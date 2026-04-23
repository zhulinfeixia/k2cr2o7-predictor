"""
FastAPI 后端主入口
提供 /predict 接口和模型信息接口
"""

import base64
import io
from typing import Optional

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from image_processor import preprocess_image, ImagePreprocessor
from model import get_predictor, ConcentrationPredictor

# 启动时预加载模型，捕获错误
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    logger.info("启动时预加载模型...")
    _predictor = get_predictor()
    logger.info("模型预加载成功!")
except Exception as e:
    logger.error(f"模型预加载失败: {e}")
    import traceback
    logger.error(f"错误详情: {traceback.format_exc()}")
    _predictor = None

# 创建 FastAPI 应用
app = FastAPI(
    title="重铬酸钾浓度预测 API",
    description="基于机器学习的重铬酸钾溶液浓度预测服务",
    version="1.0.0"
)

# 配置 CORS（允许前端跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ 数据模型 ============

class PredictRequest(BaseModel):
    """预测请求体"""
    ph: float = Field(..., ge=0, le=14, description="pH 值 (0-14)")
    image_base64: str = Field(..., description="Base64 编码的图像数据")


class PredictResponse(BaseModel):
    """预测响应体"""
    concentration: float = Field(..., description="预测浓度 (mM)")
    confidence: float = Field(..., ge=0, le=1, description="置信度 (0-1)")
    features_used: dict = Field(..., description="使用的特征值")
    warnings: list = Field(default=[], description="警告信息")
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="附加信息")


class ModelInfoResponse(BaseModel):
    """模型信息响应体"""
    model_type: Optional[str]
    feature_count: int
    features: list
    valid_ph_range: tuple
    valid_concentration_range: tuple
    n_estimators: Optional[int] = None
    feature_importances: Optional[dict] = None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    model_loaded: bool


# ============ 路由 ============

@app.get("/", tags=["根路径"])
async def root():
    """根路径 - 返回 API 信息"""
    return {
        "name": "重铬酸钾浓度预测 API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "endpoints": {
            "predict": "/predict",
            "health": "/health",
            "model_info": "/model/info"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["健康检查"])
async def health_check():
    """健康检查接口"""
    try:
        predictor = get_predictor()
        model_loaded = predictor.main_model is not None
        return HealthResponse(
            status="healthy",
            model_loaded=model_loaded
        )
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return HealthResponse(
            status=f"unhealthy: {str(e)}",
            model_loaded=False
        )


@app.get("/model/info", response_model=ModelInfoResponse, tags=["模型信息"])
async def model_info():
    """获取模型信息"""
    try:
        predictor = get_predictor()
        info = predictor.get_model_info()
        return ModelInfoResponse(**info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型信息失败: {str(e)}")


@app.post("/predict", response_model=PredictResponse, tags=["预测"])
async def predict(
    ph: float = Form(..., ge=0, le=14, description="pH 值 (0-14)"),
    image: UploadFile = File(..., description="比色皿图像文件"),
    skip_preprocessing: bool = Form(False, description="是否跳过ROI提取和光照标准化（如果图片已处理好）")
):
    """
    预测重铬酸钾浓度
    
    - **ph**: 溶液的 pH 值
    - **image**: 比色皿照片（支持 JPG, PNG 格式）
    
    返回预测的浓度值和置信度
    """
    try:
        # 1. 读取图像数据
        image_bytes = await image.read()
        
        if len(image_bytes) == 0:
            raise HTTPException(status_code=400, detail="图像文件为空")
        
        # 2. 图像预处理
        try:
            preprocess_result = preprocess_image(image_bytes, ph, skip_preprocessing)
            
            # DEBUG: 打印提取的特征值
            logger.info(f"DEBUG - 预处理方式: {'跳过' if skip_preprocessing else '完整'}")
            logger.info(f"DEBUG - 提取的特征: {preprocess_result['features_dict']}")
            logger.info(f"DEBUG - pH值: {ph}")
            logger.info(f"DEBUG - 特征向量: {preprocess_result['feature_vector'][0]}")
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"图像处理失败: {str(e)}")
        
        # 3. 获取预测器并执行预测
        predictor = get_predictor()
        feature_vector = preprocess_result['feature_vector']
        
        # 验证输入
        validation_errors = predictor.validate_input(
            preprocess_result['features_dict'], ph
        )
        if validation_errors:
            raise HTTPException(
                status_code=400, 
                detail=f"输入验证失败: {'; '.join(validation_errors)}"
            )
        
        # 执行预测
        prediction_result = predictor.predict(feature_vector)
        
        # 4. 构建响应
        features_used = {
            "ph": ph,
            "rgb": [
                round(preprocess_result['features_dict']['R'], 2),
                round(preprocess_result['features_dict']['G'], 2),
                round(preprocess_result['features_dict']['B'], 2)
            ],
            "hsv": [
                round(preprocess_result['features_dict']['H'], 2),
                round(preprocess_result['features_dict']['S'], 2),
                round(preprocess_result['features_dict']['V'], 2)
            ],
            "lab": [
                round(preprocess_result['features_dict']['L'], 2),
                round(preprocess_result['features_dict']['a'], 2),
                round(preprocess_result['features_dict']['b'], 2)
            ]
        }
        
        return PredictResponse(
            concentration=round(prediction_result['concentration'], 4),
            confidence=round(prediction_result['confidence'], 4),
            features_used=features_used,
            warnings=prediction_result['warnings'],
            success=True,
            message="预测成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预测失败: {str(e)}")


@app.post("/predict/base64", response_model=PredictResponse, tags=["预测"])
async def predict_base64(request: PredictRequest):
    """
    使用 Base64 编码图像预测浓度
    
    适合无法直接上传文件的客户端使用
    """
    try:
        # 解码 Base64 图像
        try:
            image_bytes = base64.b64decode(request.image_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="无效的 Base64 图像数据")
        
        if len(image_bytes) == 0:
            raise HTTPException(status_code=400, detail="图像数据为空")
        
        # 图像预处理
        preprocess_result = preprocess_image(image_bytes, request.ph)
        
        # 执行预测
        predictor = get_predictor()
        feature_vector = preprocess_result['feature_vector']
        
        prediction_result = predictor.predict(feature_vector)
        
        features_used = {
            "ph": request.ph,
            "rgb": [
                round(preprocess_result['features_dict']['R'], 2),
                round(preprocess_result['features_dict']['G'], 2),
                round(preprocess_result['features_dict']['B'], 2)
            ],
            "hsv": [
                round(preprocess_result['features_dict']['H'], 2),
                round(preprocess_result['features_dict']['S'], 2),
                round(preprocess_result['features_dict']['V'], 2)
            ],
            "lab": [
                round(preprocess_result['features_dict']['L'], 2),
                round(preprocess_result['features_dict']['a'], 2),
                round(preprocess_result['features_dict']['b'], 2)
            ]
        }
        
        return PredictResponse(
            concentration=round(prediction_result['concentration'], 4),
            confidence=round(prediction_result['confidence'], 4),
            features_used=features_used,
            warnings=prediction_result['warnings'],
            success=True,
            message="预测成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预测失败: {str(e)}")


# ============ 启动入口 ============

if __name__ == "__main__":
    import uvicorn
    
    print("启动重铬酸钾浓度预测 API 服务...")
    print("访问 http://localhost:8000/docs 查看 API 文档")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
