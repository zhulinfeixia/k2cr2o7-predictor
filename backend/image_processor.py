"""
图像预处理模块
实现光照标准化、颜色空间转换和特征构造
"""

import cv2
import numpy as np
import io
from typing import Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """图像预处理器 - 专门处理比色皿图像"""
        
    def preprocess(self, image: np.ndarray) -> Dict:
        """
        前端已裁剪 ROI 后的标准预处理流程
        
        Args:
            image: 输入图像 (BGR格式，OpenCV默认)
            
        Returns:
            Dict 包含：
                - roi: 光照标准化后的输入区域
                - features: 构造的特征字典
                - metadata: 处理元数据
        """
        if image is None or image.size == 0:
            raise ValueError("输入图像为空")
        
        # 前端已经完成 ROI 裁剪，后端统一进行光照标准化。
        normalized = self._normalize_lighting(image)
        
        # 从标准化后的图像提取颜色特征。
        features = self._extract_color_features(normalized)
        
        return {
            'roi': normalized,
            'features': features,
            'metadata': {
                'original_shape': image.shape,
                'roi_shape': normalized.shape,
                'extraction_method': 'frontend_roi_lighting_normalized'
            }
        }
    
    def _normalize_lighting(self, image: np.ndarray) -> np.ndarray:
        """
        光照标准化
        
        使用 LAB 颜色空间的 L 通道进行光照归一化
        """
        # 转换到 LAB 颜色空间
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # 对 L 通道进行 CLAHE (对比度受限自适应直方图均衡化)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_normalized = clahe.apply(l)
        
        # 合并回 LAB
        lab_normalized = cv2.merge([l_normalized, a, b])
        
        # 转换回 BGR
        normalized = cv2.cvtColor(lab_normalized, cv2.COLOR_LAB2BGR)
        
        return normalized
    
    def _extract_color_features(self, image: np.ndarray) -> Dict[str, float]:
        """
        提取颜色特征
        
        提取 RGB、HSV、Lab 颜色空间的统计特征
        """
        features = {}
        
        # 1. RGB 特征 (均值)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        r_mean = np.mean(rgb[:, :, 0])
        g_mean = np.mean(rgb[:, :, 1])
        b_mean = np.mean(rgb[:, :, 2])
        
        features['R'] = r_mean
        features['G'] = g_mean
        features['B'] = b_mean
        
        # 2. HSV 特征
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h_mean = np.mean(hsv[:, :, 0])
        s_mean = np.mean(hsv[:, :, 1])
        v_mean = np.mean(hsv[:, :, 2])
        
        features['H'] = h_mean
        features['S'] = s_mean
        features['V'] = v_mean
        
        # 3. Lab 特征
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_mean = np.mean(lab[:, :, 0])
        a_mean = np.mean(lab[:, :, 1])
        b_lab_mean = np.mean(lab[:, :, 2])
        
        features['L'] = l_mean
        features['a'] = a_mean
        features['b'] = b_lab_mean
        
        # 4. 比值特征
        # 避免除以零
        eps = 1e-6
        features['R_over_G'] = r_mean / (g_mean + eps)
        features['R_over_B'] = r_mean / (b_mean + eps)
        features['G_over_B'] = g_mean / (b_mean + eps)
        
        # RGB 归一化比例
        rgb_sum = r_mean + g_mean + b_mean + eps
        features['R_ratio'] = r_mean / rgb_sum
        features['G_ratio'] = g_mean / rgb_sum
        features['B_ratio'] = b_mean / rgb_sum
        
        return features
    
    def get_feature_vector(self, features: Dict[str, float], ph: float) -> np.ndarray:
        """
        将特征字典转换为模型输入向量
        
        特征顺序必须与训练时一致：
        ['pH', 'R', 'G', 'B', 'H', 'S', 'V', 'L', 'a', 'b', 
         'R_over_G', 'R_over_B', 'G_over_B', 'R_ratio', 'G_ratio', 'B_ratio']
        """
        feature_order = [
            'pH', 'R', 'G', 'B', 'H', 'S', 'V', 'L', 'a', 'b',
            'R_over_G', 'R_over_B', 'G_over_B', 'R_ratio', 'G_ratio', 'B_ratio'
        ]
        
        # 添加 pH 到特征字典
        features_with_ph = features.copy()
        features_with_ph['pH'] = ph
        
        # DEBUG: 打印特征值
        logger.info(f"DEBUG - Extracted features: {features}")
        logger.info(f"DEBUG - pH value: {ph}")
        
        # 按顺序构建向量
        vector = np.array([features_with_ph[f] for f in feature_order])
        
        logger.info(f"DEBUG - Feature vector: {vector}")
        
        return vector.reshape(1, -1)


def preprocess_image(image_bytes: bytes, ph: float) -> Dict:
    """
    便捷的预处理函数
    
    Args:
        image_bytes: 图像字节数据
        ph: pH 值
        
    Returns:
        Dict 包含特征向量和元数据
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # 解码图像
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 如果OpenCV解码失败（如某些TIF格式），尝试用PIL
    if image is None:
        try:
            from PIL import Image
            pil_image = Image.open(io.BytesIO(image_bytes))
            # 转换为RGB（如果是RGBA或P模式）
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            # 转换为OpenCV格式（BGR）
            image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            logger.info(f"使用PIL解码图像成功，尺寸: {image.shape}")
        except Exception as e:
            raise ValueError(f"无法解码图像，请确保上传的是有效的图像文件: {e}")
    
    if image is None:
        raise ValueError("无法解码图像，请确保上传的是有效的图像文件")

    # 标准流程：前端传入裁剪后的 ROI，后端统一光照标准化后提取特征。
    preprocessor = ImagePreprocessor()
    result = preprocessor.preprocess(image)
    
    # 构建特征向量
    feature_vector = preprocessor.get_feature_vector(result['features'], ph)
    
    return {
        'feature_vector': feature_vector,
        'features_dict': result['features'],
        'roi_image': result['roi'],
        'metadata': result['metadata']
    }
