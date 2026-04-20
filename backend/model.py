"""
模型封装模块
加载训练好的模型并进行推理
"""

import joblib
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConcentrationPredictor:
    """重铬酸钾浓度预测器"""
    
    # 特征顺序（必须与训练时一致）
    FEATURE_ORDER = [
        'pH', 'R', 'G', 'B', 'H', 'S', 'V', 'L', 'a', 'b',
        'R_over_G', 'R_over_B', 'G_over_B', 'R_ratio', 'G_ratio', 'B_ratio'
    ]
    
    # 模型适用范围（根据训练数据分布）
    VALID_PH_RANGE = (2.0, 12.0)
    VALID_CONCENTRATION_RANGE = (0.0, 10.0)  # mM，根据实际情况调整
    
    def __init__(self, model_path: Optional[str] = None):
        """
        初始化预测器
        
        Args:
            model_path: 模型文件路径，默认使用 models/RF_model.joblib
        """
        if model_path is None:
            # 默认路径：当前文件所在目录的 models 子目录
            current_dir = Path(__file__).parent
            model_path = current_dir / "models" / "RF_model.joblib"
        
        self.model_path = Path(model_path)
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """加载模型文件"""
        try:
            logger.info(f"正在加载模型: {self.model_path}")
            self.model = joblib.load(self.model_path)
            logger.info(f"模型加载成功: {type(self.model).__name__}")
            
            # 验证模型类型
            model_type = type(self.model).__name__
            if 'RandomForest' not in model_type:
                logger.warning(f"模型类型为 {model_type}，预期为 RandomForestRegressor")
                
        except FileNotFoundError:
            raise FileNotFoundError(f"模型文件不存在: {self.model_path}")
        except Exception as e:
            raise RuntimeError(f"模型加载失败: {e}")
    
    def predict(self, feature_vector: np.ndarray) -> Dict[str, Any]:
        """
        执行预测
        
        Args:
            feature_vector: 形状为 (1, 16) 的特征向量
            
        Returns:
            Dict 包含预测结果和元数据
        """
        if self.model is None:
            raise RuntimeError("模型未加载")
        
        # 验证输入维度
        if feature_vector.shape[1] != len(self.FEATURE_ORDER):
            raise ValueError(
                f"特征维度不匹配: 输入 {feature_vector.shape[1]}, "
                f"预期 {len(self.FEATURE_ORDER)}"
            )
        
        # DEBUG: 打印特征值
        logger.info(f"DEBUG - Feature vector: {feature_vector[0]}")
        logger.info(f"DEBUG - Feature names: {self.FEATURE_ORDER}")
        logger.info(f"DEBUG - Feature ranges: min={feature_vector[0].min():.2f}, max={feature_vector[0].max():.2f}")
        
        # 执行预测
        prediction = self.model.predict(feature_vector)[0]
        logger.info(f"DEBUG - Raw prediction: {prediction}")
        
        # 计算置信度（使用树的方差作为不确定性估计）
        if hasattr(self.model, 'estimators_'):
            # 获取所有树的预测
            tree_predictions = np.array([
                tree.predict(feature_vector)[0] 
                for tree in self.model.estimators_
            ])
            std = np.std(tree_predictions)
            confidence = self._calculate_confidence(std)
        else:
            confidence = 0.5  # 默认中等置信度
        
        # 生成警告
        warnings = self._generate_warnings(feature_vector[0], prediction)
        
        return {
            'concentration': float(prediction),
            'confidence': float(confidence),
            'std': float(std) if 'std' in locals() else None,
            'warnings': warnings,
            'is_valid': len(warnings) == 0
        }
    
    def _calculate_confidence(self, std: float) -> float:
        """
        根据预测标准差计算置信度
        
        标准差越小，置信度越高
        """
        # 将标准差映射到 0-1 的置信度
        # 假设 std=0 时 confidence=1, std=1 时 confidence=0.5
        confidence = np.exp(-std)
        return float(np.clip(confidence, 0.1, 1.0))
    
    def _generate_warnings(self, features: np.ndarray, prediction: float) -> List[str]:
        """生成使用警告"""
        warnings = []
        
        # 解包特征
        ph = features[0]
        r, g, b = features[1], features[2], features[3]
        
        # pH 范围检查
        if ph < self.VALID_PH_RANGE[0] or ph > self.VALID_PH_RANGE[1]:
            warnings.append(
                f"pH 值 {ph:.1f} 超出训练范围 "
                f"({self.VALID_PH_RANGE[0]}-{self.VALID_PH_RANGE[1]})，"
                f"预测结果可能不可靠"
            )
        
        # 浓度范围检查
        if prediction < 0:
            warnings.append(
                f"预测浓度为负值 ({prediction:.3f} mM)，"
                f"可能是输入图像或 pH 值有误"
            )
        elif prediction > self.VALID_CONCENTRATION_RANGE[1]:
            warnings.append(
                f"预测浓度 {prediction:.2f} mM 超出典型范围，"
                f"请检查输入数据"
            )
        
        # 颜色值合理性检查
        if r < 10 and g < 10 and b < 10:
            warnings.append("图像颜色过暗，可能影响预测精度")
        
        if r > 250 and g > 250 and b > 250:
            warnings.append("图像颜色过亮，可能存在过曝")
        
        # RGB 平衡检查（重铬酸钾溶液通常有颜色）
        rgb_variance = np.var([r, g, b])
        if rgb_variance < 100:
            warnings.append("图像颜色过于均匀，可能未检测到有效溶液")
        
        return warnings
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        info = {
            'model_type': type(self.model).__name__ if self.model else None,
            'feature_count': len(self.FEATURE_ORDER),
            'features': self.FEATURE_ORDER,
            'valid_ph_range': self.VALID_PH_RANGE,
            'valid_concentration_range': self.VALID_CONCENTRATION_RANGE,
        }
        
        # 添加模型特定参数
        if self.model:
            if hasattr(self.model, 'n_estimators'):
                info['n_estimators'] = self.model.n_estimators
            if hasattr(self.model, 'max_depth'):
                info['max_depth'] = self.model.max_depth
            if hasattr(self.model, 'feature_importances_'):
                # 特征重要性
                importances = dict(zip(
                    self.FEATURE_ORDER, 
                    self.model.feature_importances_.tolist()
                ))
                # 按重要性排序
                info['feature_importances'] = dict(
                    sorted(importances.items(), key=lambda x: x[1], reverse=True)
                )
        
        return info
    
    def validate_input(self, features_dict: Dict[str, float], ph: float) -> List[str]:
        """
        验证输入数据
        
        Args:
            features_dict: 图像特征字典
            ph: pH 值
            
        Returns:
            错误信息列表，为空表示验证通过
        """
        errors = []
        
        # 检查必需特征
        missing_features = set(self.FEATURE_ORDER[1:]) - set(features_dict.keys())
        if missing_features:
            errors.append(f"缺少特征: {missing_features}")
        
        # 检查 pH 值
        if not isinstance(ph, (int, float)):
            errors.append("pH 值必须是数字")
        elif ph < 0 or ph > 14:
            errors.append("pH 值必须在 0-14 范围内")
        
        # 检查特征值
        for key, value in features_dict.items():
            if not isinstance(value, (int, float)):
                errors.append(f"特征 {key} 必须是数字")
                break
            if np.isnan(value) or np.isinf(value):
                errors.append(f"特征 {key} 包含无效值")
                break
        
        return errors


# 全局预测器实例（单例模式）
_predictor_instance = None


def get_predictor() -> ConcentrationPredictor:
    """获取全局预测器实例"""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = ConcentrationPredictor()
    return _predictor_instance


def predict_concentration(feature_vector: np.ndarray) -> Dict[str, Any]:
    """
    便捷的预测函数
    
    Args:
        feature_vector: 特征向量
        
    Returns:
        预测结果字典
    """
    predictor = get_predictor()
    return predictor.predict(feature_vector)
