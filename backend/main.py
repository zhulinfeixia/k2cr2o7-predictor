"""
FastAPI backend for chromium(VI) species prediction.
"""

import base64
import logging
import os
from typing import Any, Dict, List, Literal, Optional

import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from image_processor import preprocess_image
from species_model import get_species_predictor


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LLM_API_KEY = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")


try:
    logger.info("Preloading deployed species model...")
    _species_predictor = get_species_predictor()
    logger.info("Species model loaded.")
except Exception as exc:
    logger.error("Species model preload failed: %s", exc, exc_info=True)
    _species_predictor = None


app = FastAPI(
    title="K2Cr2O7 Species Prediction API",
    description="ML species prediction with chromium(VI) equilibrium calculation.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictRequest(BaseModel):
    ph: float = Field(..., ge=0, le=14, description="pH value")
    image_base64: str = Field(..., description="Base64 encoded image")


class PredictResponse(BaseModel):
    concentration: float = Field(..., description="Estimated total Cr(VI), mM")
    confidence: float = Field(..., ge=0, le=1)
    features_used: Dict[str, Any]
    species_concentrations: Dict[str, float]
    species_model_info: Dict[str, Any]
    warnings: List[str] = []
    success: bool
    message: str = ""


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    chat_configured: bool


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    messages: List[ChatMessage] = []
    mode: str = Field(default="query")
    prediction_context: Dict[str, Any] = {}


class ChatResponse(BaseModel):
    reply: str
    configured: bool
    model: Optional[str] = None


def validate_features(features_dict: Dict[str, Any], ph: float) -> List[str]:
    errors: List[str] = []
    required = set(get_species_predictor().FEATURE_ORDER[1:])
    missing = required - set(features_dict.keys())
    if missing:
        errors.append(f"Missing image features: {sorted(missing)}")
    if not isinstance(ph, (int, float)):
        errors.append("pH must be numeric.")
    elif ph < 0 or ph > 14:
        errors.append("pH must be between 0 and 14.")
    for key, value in features_dict.items():
        if not isinstance(value, (int, float)):
            errors.append(f"Feature {key} must be numeric.")
            break
    return errors


def build_features_used(preprocess_result: Dict[str, Any], ph: float) -> Dict[str, Any]:
    features = preprocess_result["features_dict"]
    return {
        "ph": ph,
        "rgb": [round(features["R"], 2), round(features["G"], 2), round(features["B"], 2)],
        "hsv": [round(features["H"], 2), round(features["S"], 2), round(features["V"], 2)],
        "lab": [round(features["L"], 2), round(features["a"], 2), round(features["b"], 2)],
        "ratios": {
            "R_over_G": round(features["R_over_G"], 4),
            "R_over_B": round(features["R_over_B"], 4),
            "G_over_B": round(features["G_over_B"], 4),
            "R_ratio": round(features["R_ratio"], 4),
            "G_ratio": round(features["G_ratio"], 4),
            "B_ratio": round(features["B_ratio"], 4),
        },
    }


def run_prediction(image_bytes: bytes, ph: float) -> PredictResponse:
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Image file is empty.")

    try:
        preprocess_result = preprocess_image(image_bytes, ph)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Image processing failed: {exc}") from exc

    validation_errors = validate_features(preprocess_result["features_dict"], ph)
    if validation_errors:
        raise HTTPException(status_code=400, detail="; ".join(validation_errors))

    species_predictor = get_species_predictor()
    species_result = species_predictor.predict(preprocess_result["feature_vector"])
    species = species_result["species_concentrations"]

    return PredictResponse(
        concentration=round(species["estimated_total_cr_mM"], 4),
        confidence=round(species_result["confidence"], 4),
        features_used=build_features_used(preprocess_result, ph),
        species_concentrations={key: round(float(value), 6) for key, value in species.items()},
        species_model_info=species_result["model_info"],
        warnings=species_result["warnings"],
        success=True,
        message="Species prediction completed.",
    )


def system_prompt_for(mode: str, prediction_context: Dict[str, Any]) -> str:
    base = (
        "You are a careful chemistry assistant for a potassium dichromate web app. "
        "Answer in the user's language. Keep explanations grounded in chromium(VI) "
        "equilibria, color features, pH, and model uncertainty. Do not invent hidden "
        "training data or claim laboratory certainty."
    )
    if mode == "prediction_analysis":
        return (
            base
            + "\nThe user is asking about a model prediction result. Use the supplied "
            "prediction context, explain reliability and possible experimental checks."
            f"\nPrediction context: {prediction_context}"
        )
    return base


@app.get("/")
async def root() -> Dict[str, Any]:
    return {
        "name": "K2Cr2O7 Species Prediction API",
        "version": "2.0.0",
        "endpoints": {
            "predict": "/predict",
            "predict_base64": "/predict/base64",
            "chat": "/chat",
            "health": "/health",
            "model_info": "/model/info",
        },
    }


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    try:
        species_predictor = get_species_predictor()
        model_loaded = species_predictor.model is not None
        return HealthResponse(
            status="healthy" if model_loaded else "unhealthy",
            model_loaded=model_loaded,
            chat_configured=bool(LLM_API_KEY),
        )
    except Exception as exc:
        logger.error("Health check failed: %s", exc, exc_info=True)
        return HealthResponse(status=f"unhealthy: {exc}", model_loaded=False, chat_configured=bool(LLM_API_KEY))


@app.get("/model/info")
async def model_info() -> Dict[str, Any]:
    try:
        return get_species_predictor().get_model_info()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load model info: {exc}") from exc


@app.get("/species/model/info")
async def species_model_info() -> Dict[str, Any]:
    return await model_info()


@app.post("/predict", response_model=PredictResponse)
async def predict(
    ph: float = Form(..., ge=0, le=14, description="pH value"),
    image: UploadFile = File(..., description="ROI image file"),
) -> PredictResponse:
    try:
        image_bytes = await image.read()
        return run_prediction(image_bytes, ph)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Prediction failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}") from exc


@app.post("/predict/base64", response_model=PredictResponse)
async def predict_base64(request: PredictRequest) -> PredictResponse:
    try:
        image_bytes = base64.b64decode(request.image_base64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 image data.") from exc
    return run_prediction(image_bytes, request.ph)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if not LLM_API_KEY:
        return ChatResponse(
            reply=(
                "大模型接口代码已经接好，但后端还没有配置 API key。"
                "请在部署环境中设置 LLM_API_KEY，并按需要设置 LLM_BASE_URL 和 LLM_MODEL。"
            ),
            configured=False,
            model=None,
        )

    upstream_messages = [
        {"role": "system", "content": system_prompt_for(request.mode, request.prediction_context)}
    ]
    upstream_messages.extend({"role": m.role, "content": m.content} for m in request.messages[-12:])
    upstream_messages.append({"role": "user", "content": request.prompt})

    try:
        response = requests.post(
            LLM_BASE_URL,
            headers={
                "Authorization": f"Bearer {LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "messages": upstream_messages,
                "temperature": 0.3,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        return ChatResponse(reply=reply, configured=True, model=LLM_MODEL)
    except Exception as exc:
        logger.error("Chat request failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Chat provider request failed: {exc}") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
