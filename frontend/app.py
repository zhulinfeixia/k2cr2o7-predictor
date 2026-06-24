"""
Streamlit frontend for chromium(VI) species prediction.
"""

import io
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import streamlit as st
from PIL import Image
from streamlit_cropper import st_cropper


st.set_page_config(
    page_title="K2Cr2O7 Species Predictor",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
CONTENT_DIR = Path(__file__).parent / "content"
INTRODUCTION_FILE = CONTENT_DIR / "knowledge_summary.md"


def init_state() -> None:
    defaults = {
        "history": [],
        "cropped_image": None,
        "original_image": None,
        "roi_selected": False,
        "last_prediction": None,
        "query_messages": [],
        "analysis_messages": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def check_api() -> bool:
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        return response.status_code == 200
    except requests.RequestException:
        return False


def image_mimetype(filename: str) -> str:
    lowered = filename.lower()
    if lowered.endswith((".tif", ".tiff")):
        return "image/tiff"
    if lowered.endswith(".png"):
        return "image/png"
    return "image/jpeg"


def predict(image_bytes: bytes, ph: float, filename: str) -> Dict[str, Any]:
    try:
        files = {"image": (filename, image_bytes, image_mimetype(filename))}
        data = {"ph": ph}
        response = requests.post(
            f"{API_BASE_URL}/predict",
            files=files,
            data=data,
            timeout=60,
        )
        if response.status_code == 200:
            return response.json()
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text or f"HTTP {response.status_code}"
        return {"error": f"API Error ({response.status_code}): {detail}"}
    except requests.RequestException as exc:
        return {"error": str(exc)}


def ask_llm(
    prompt: str,
    messages: List[Dict[str, str]],
    mode: str,
    prediction_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = {
        "prompt": prompt,
        "messages": messages,
        "mode": mode,
        "prediction_context": prediction_context or {},
    }
    try:
        response = requests.post(f"{API_BASE_URL}/chat", json=payload, timeout=60)
        if response.status_code == 200:
            return response.json()
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text or f"HTTP {response.status_code}"
        return {"reply": f"Chat API error ({response.status_code}): {detail}", "configured": False}
    except requests.RequestException as exc:
        return {"reply": f"Chat API unavailable: {exc}", "configured": False}


def render_chat_panel(
    title: str,
    state_key: str,
    mode: str,
    placeholder: str,
    prediction_context: Optional[Dict[str, Any]] = None,
) -> None:
    st.subheader(title)

    messages = st.session_state[state_key]
    if not messages:
        st.caption("大模型接口已预留，填入后端环境变量后即可使用。")

    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    with st.form(f"{state_key}_form", clear_on_submit=True):
        prompt = st.text_area("Message", placeholder=placeholder, label_visibility="collapsed", height=110)
        submitted = st.form_submit_button("Send")

    if submitted and prompt.strip():
        user_message = {"role": "user", "content": prompt.strip()}
        messages.append(user_message)
        with st.spinner("Waiting for model response..."):
            result = ask_llm(prompt.strip(), messages[:-1], mode, prediction_context)
        messages.append({"role": "assistant", "content": result.get("reply", "")})
        st.rerun()


def render_introduction() -> None:
    st.title("Introduction")
    if INTRODUCTION_FILE.exists():
        st.markdown(INTRODUCTION_FILE.read_text(encoding="utf-8"))
    else:
        st.warning("Introduction content is missing.")


def render_query(api_ok: bool) -> None:
    st.title("Query")
    st.caption(f"Backend: {API_BASE_URL} · {'online' if api_ok else 'offline'}")
    render_chat_panel(
        "General chemistry query",
        "query_messages",
        "query",
        "Ask about dichromate equilibrium, experimental design, or model interpretation...",
    )


def save_crop_for_prediction(cropped: Image.Image, original_name: str) -> bytes:
    image_buffer = io.BytesIO()
    if cropped.mode == "RGBA":
        cropped = cropped.convert("RGB")
    if original_name.lower().endswith((".tif", ".tiff")):
        cropped.save(image_buffer, format="TIFF")
    else:
        cropped.save(image_buffer, format="PNG")
    image_buffer.seek(0)
    return image_buffer.getvalue()


def render_prediction_results(result: Dict[str, Any], ph: float) -> None:
    species = result.get("species_concentrations") or {}
    total_cr = float(species.get("estimated_total_cr_mM", result.get("concentration", 0.0)))
    hcro4 = float(species.get("HCrO4_mM", 0.0))
    cr2o7 = float(species.get("Cr2O7_mM", 0.0))
    cro4 = float(species.get("CrO4_mM", 0.0))
    residual = float(species.get("dimer_residual_mM", 0.0))

    st.session_state.history.append(
        {
            "time": datetime.now().strftime("%H:%M:%S"),
            "ph": ph,
            "total_cr": total_cr,
            "hcro4": hcro4,
            "cr2o7": cr2o7,
            "cro4": cro4,
        }
    )
    st.session_state.last_prediction = {
        "pH": ph,
        "HCrO4_mM": hcro4,
        "Cr2O7_mM": cr2o7,
        "CrO4_mM": cro4,
        "estimated_total_cr_mM": total_cr,
        "dimer_residual_mM": residual,
        "confidence": result.get("confidence"),
        "warnings": result.get("warnings", []),
        "features_used": result.get("features_used", {}),
    }

    st.success("Prediction completed.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("HCrO4-", f"{hcro4:.4f} mM")
    c2.metric("Cr2O7^2-", f"{cr2o7:.4f} mM")
    c3.metric("CrO4^2-", f"{cro4:.4f} mM")
    c4.metric("Estimated total Cr(VI)", f"{total_cr:.4f} mM")

    d1, d2, d3 = st.columns(3)
    d1.metric("Confidence", f"{float(result.get('confidence', 0.0)):.1%}")
    d2.metric("Dimer residual", f"{residual:.4f} mM")
    d3.metric("pH", f"{ph:.1f}")

    for warning in result.get("warnings", []):
        st.warning(warning)


def render_model_prediction(api_ok: bool) -> None:
    st.title("Model Prediction")
    st.caption("Workflow: upload ROI image and pH, standardize illumination, extract color features, predict HCrO4- and Cr2O7^2-, then compute CrO4^2-.")

    left, right = st.columns([1, 1])

    with left:
        st.subheader("Sample image")
        uploaded = st.file_uploader("Select photo", type=["jpg", "jpeg", "png", "tif", "tiff"])
        if uploaded:
            image = Image.open(uploaded)
            st.session_state.original_image = image
            st.session_state.cropped_image = st_cropper(
                image,
                realtime_update=True,
                box_color="#D92D20",
                aspect_ratio=None,
                return_type="image",
            )
            st.session_state.roi_selected = True

        ph = st.slider("pH", 3.0, 8.0, 6.0, 0.1)
        st.caption("The deployed model is trained for pH 3-8. pH 7-8 may amplify CrO4^2- uncertainty.")

        can_predict = bool(uploaded and api_ok and st.session_state.cropped_image)
        if st.button("Predict", disabled=not can_predict, type="primary"):
            with st.spinner("Analyzing ROI image..."):
                image_bytes = save_crop_for_prediction(st.session_state.cropped_image, uploaded.name)
                result = predict(image_bytes, ph, uploaded.name)
            if "error" in result:
                st.error(result["error"])
            else:
                render_prediction_results(result, ph)

    with right:
        st.subheader("ROI preview")
        if st.session_state.cropped_image:
            st.image(st.session_state.cropped_image, caption="Selected ROI", use_container_width=True)
        elif uploaded:
            st.info("Draw a box around the cuvette region.")
        else:
            st.info("Upload a photo, then select the cuvette region.")

        st.markdown("---")
        st.subheader("Equilibrium basis")
        st.latex(r"Cr_2O_7^{2-} + H_2O \rightleftharpoons 2HCrO_4^-")
        st.latex(r"HCrO_4^- \rightleftharpoons H^+ + CrO_4^{2-}")
        st.latex(r"[CrO_4^{2-}] = K_{a2}[HCrO_4^-]/[H^+]")
        st.latex(r"C_{Cr(VI)} = [HCrO_4^-] + [CrO_4^{2-}] + 2[Cr_2O_7^{2-}]")

    st.markdown("---")
    render_chat_panel(
        "Result analysis assistant",
        "analysis_messages",
        "prediction_analysis",
        "Ask the model to summarize this result, discuss reliability, or suggest experimental checks...",
        st.session_state.last_prediction,
    )


def render_sidebar(api_ok: bool) -> str:
    with st.sidebar:
        st.title("K2Cr2O7")
        st.caption("Chromium(VI) species predictor")
        if api_ok:
            st.success("Backend online")
        else:
            st.error("Backend offline")

        module = st.radio(
            "Module",
            ["Introduction", "Query", "Model Prediction"],
            index=2,
        )

        if st.session_state.history:
            st.markdown("---")
            st.subheader("Recent predictions")
            for item in st.session_state.history[-5:]:
                st.write(
                    f"{item['time']} · pH {item['ph']:.1f} · "
                    f"CrO4^2- {item['cro4']:.3f} mM"
                )
    return module


def main() -> None:
    init_state()
    api_ok = check_api()
    module = render_sidebar(api_ok)

    if module == "Introduction":
        render_introduction()
    elif module == "Query":
        render_query(api_ok)
    else:
        render_model_prediction(api_ok)

    st.markdown("---")
    st.caption("K2Cr2O7 Prediction System · ML species prediction with equilibrium calculation")


if __name__ == "__main__":
    main()
