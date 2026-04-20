"""
图像预处理模块
实现 ROI 提取、光照标准化、颜色空间转换和特征构造
"""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """图像预处理器 - 专门处理比色皿图像"""
    
    def __init__(self, target_size: Tuple[int, int] = (224, 224)):
        self.target_size = target_size
        
    def preprocess(self, image: np.ndarray) -> Dict:
        """
        完整的图像预处理流程
        
        Args:
            image: 输入图像 (BGR格式，OpenCV默认)
            
        Returns:
            Dict 包含：
                - roi: 提取的ROI区域
                - features: 构造的特征字典
                - metadata: 处理元数据
        """
        # 1. 基础预处理
        image = self._basic_preprocess(image)
        
        # 2. ROI 提取
        roi = self._extract_roi(image)
        if roi is None:
            # 如果自动提取失败，使用中心区域
            roi = self._fallback_roi(image)
            logger.warning("自动ROI提取失败，使用中心区域作为备选")
        
        # 3. 光照标准化
        roi_normalized = self._normalize_lighting(roi)
        
        # 4. 颜色空间转换和特征提取
        features = self._extract_color_features(roi_normalized)
        
        return {
            'roi': roi_normalized,
            'features': features,
            'metadata': {
                'original_shape': image.shape,
                'roi_shape': roi.shape if roi is not None else None,
                'extraction_method': 'auto' if roi is not None else 'fallback'
            }
        }
    
    def _basic_preprocess(self, image: np.ndarray) -> np.ndarray:
        """基础预处理：调整大小、去噪"""
        # 确保图像不为空
        if image is None or image.size == 0:
            raise ValueError("输入图像为空")
        
        # 如果图像太大，先缩小以提高处理速度
        max_dim = 1024
        h, w = image.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            image = cv2.resize(image, (new_w, new_h))
        
        # 轻微高斯模糊去噪
        image = cv2.GaussianBlur(image, (5, 5), 0)
        
        return image
    
    def _extract_roi(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        自动提取比色皿 ROI 区域
        
        策略：
        1. 转换为灰度
        2. 边缘检测
        3. 查找轮廓
        4. 选择最可能是比色皿的矩形区域
        """
        try:
            # 灰度转换
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 自适应阈值
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY_INV, 11, 2
            )
            
            # 形态学操作清理
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
            
            # 查找轮廓
            contours, _ = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            
            if not contours:
                return None
            
            # 筛选可能的比色皿区域
            candidates = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 1000:  # 过滤太小的区域
                    continue
                
                x, y, w, h = cv2.boundingRect(cnt)
                aspect_ratio = float(w) / h if h > 0 else 0
                
                # 比色皿通常是竖直的长方形
                # 宽高比在 0.2-0.5 之间（窄高型）
                if 0.15 < aspect_ratio < 0.6:
                    candidates.append({
                        'contour': cnt,
                        'rect': (x, y, w, h),
                        'area': area,
                        'aspect_ratio': aspect_ratio,
                        'center': (x + w//2, y + h//2)
                    })
            
            if not candidates:
                return None
            
            # 选择最中心的候选区域（假设比色皿在图像中心）
            h, w = image.shape[:2]
            image_center = (w // 2, h // 2)
            
            best_candidate = min(
                candidates,
                key=lambda c: abs(c['center'][0] - image_center[0]) + 
                             abs(c['center'][1] - image_center[1])
            )
            
            x, y, w, h = best_candidate['rect']
            
            # 添加边距
            margin = int(min(w, h) * 0.1)
            x1 = max(0, x + margin)
            y1 = max(0, y + margin)
            x2 = min(image.shape[1], x + w - margin)
            y2 = min(image.shape[0], y + h - margin)
            
            roi = image[y1:y2, x1:x2]
            
            # 调整大小
            if roi.size > 0:
                roi = cv2.resize(roi, self.target_size)
                return roi
            
            return None
            
        except Exception as e:
            logger.error(f"ROI提取失败: {e}")
            return None
    
    def _fallback_roi(self, image: np.ndarray) -> np.ndarray:
        """备选方案：提取图像中心区域"""
        h, w = image.shape[:2]
        
        # 提取中心 40% 区域
        cx, cy = w // 2, h // 2
        rw, rh = int(w * 0.4), int(h * 0.6)
        
        x1 = max(0, cx - rw // 2)
        y1 = max(0, cy - rh // 2)
        x2 = min(w, cx + rw // 2)
        y2 = min(h, cy + rh // 2)
        
        roi = image[y1:y2, x1:x2]
        roi = cv2.resize(roi, self.target_size)
        
        return roi
    
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
        
        # 按顺序构建向量
        vector = np.array([features_with_ph[f] for f in feature_order])
        
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
    # 解码图像
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if image is None:
        raise ValueError("无法解码图像，请确保上传的是有效的图像文件")
    
    # 预处理
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
