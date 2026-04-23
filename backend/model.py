"""
模型封装模块 - 多pH集成模型版本
加载训练好的模型并进行推理
支持主模型 + 各pH专属子模型
"""

import joblib
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConcentrationPredictor:
    """重铬酸钾浓度预测器 - 多pH集成模型"""
    
    # 特征顺序（必须与训练时一致）
    FEATURE_ORDER = [
        'pH', 'R', 'G', 'B', 'H', 'S', 'V', 'L', 'a', 'b',
        'R_over_G', 'R_over_B', 'G_over_B', 'R_ratio', 'G_ratio', 'B_ratio'
    ]
    
    FEATURE_ORDER_NO_PH = [
        'R', 'G', 'B', 'H', 'S', 'V', 'L', 'a', 'b',
        'R_over_G', 'R_over_B', 'G_over_B', 'R_ratio', 'G_ratio', 'B_ratio'
    ]
    
    # 模型适用范围
    VALID_PH_RANGE = (2.0, 12.0)
    VALID_CONCENTRATION_RANGE = (0.0, 10.0)  # mM
    
    def __init__(self, model_path: Optional[str] = None):
        """
        初始化预测器
        
        Args:
            model_path: 模型文件路径，默认使用 models/RF_model.joblib
        """
        if model_path is None:
            current_dir = Path(__file__).parent
            # 优先加载多pH模型，如果不存在则加载默认模型
            multiph_path = current_dir / "models" / "RF_model_multiph.joblib"
            default_path = current_dir / "models" / "RF_model.joblib"
            if multiph_path.exists():
                model_path = multiph_path
            else:
                model_path = default_path
        
        self.model_path = Path(model_path)
        self.main_model = None
        self.ph_models = {}
        self.ph_stats = {}
        self.version = "1.0"
        self._load_model()
    
    def _load_model(self):
        """加载模型文件"""
        try:
            logger.info(f"正在加载模型: {self.model_path}")
            
            # 检查文件是否存在
            if not self.model_path.exists():
                raise FileNotFoundError(f"模型文件不存在: {self.model_path}")
            
            # 检查文件大小
            file_size = self.model_path.stat().st_size / (1024 * 1024)  # MB
            logger.info(f"模型文件大小: {file_size:.2f} MB")
            
            # 加载模型包
            model_package = joblib.load(self.model_path)
            logger.info(f"模型文件加载完成，类型: {type(model_package)}")
            
            # 检查是否是多pH模型包
            if isinstance(model_package, dict):
                logger.info(f"模型包包含的键: {list(model_package.keys())}")
                
                if 'main_model' in model_package:
                    self.main_model = model_package['main_model']
                    self.ph_models = model_package.get('ph_models', {})
                    self.ph_stats = model_package.get('ph_stats', {})
                    self.version = model_package.get('version', '2.0')
                    logger.info(f"多pH集成模型加载成功 (版本: {self.version})")
                    logger.info(f"主模型: {type(self.main_model).__name__}")
                    logger.info(f"子模型数量: {len(self.ph_models)}")
                    if self.ph_models:
                        logger.info(f"支持的pH值: {sorted(self.ph_models.keys())}")
                else:
                    # 可能是其他格式的字典，尝试作为单一模型
                    logger.warning(f"模型包不包含'main_model'键，尝试其他加载方式")
                    self.main_model = model_package
                    logger.info(f"模型加载成功: {type(self.main_model).__name__}")
            else:
                # 旧版单一模型
                self.main_model = model_package
                logger.info(f"单一模型加载成功: {type(self.main_model).__name__}")
                
        except FileNotFoundError:
            raise FileNotFoundError(f"模型文件不存在: {self.model_path}")
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            raise RuntimeError(f"模型加载失败: {e}")
    
    def _get_ph_model_key(self, ph: float) -> Optional[int]:
        """
        根据pH值确定使用哪个子模型
        
        pH范围映射:
        - 2-3  → pH=2 模型
        - 3-5  → pH=4 模型
        - 5-7  → pH=6 模型
        - 7-9  → pH=8 模型
        - 9-11 → pH=10 模型
        - 11-12→ pH=12 模型
        """
        if 2 <= ph < 3:
            return 2
        elif 3 <= ph < 5:
            return 4
        elif 5 <= ph < 7:
            return 6
        elif 7 <= ph < 9:
            return 8
        elif 9 <= ph < 11:
            return 10
        elif 11 <= ph <= 12:
            return 12
        else:
            return None  # 超出范围
    
    def predict(self, feature_vector: np.ndarray, use_ph_model: bool = True) -> Dict[str, Any]:
        """
        执行预测
        
        策略:
        1. 首先尝试使用对应pH范围的子模型
        2. 如果没有匹配的子模型，使用主模型作为备选
        
        Args:
            feature_vector: 形状为 (1, 16) 的特征向量
            use_ph_model: 是否使用pH专属子模型（如果可用）
            
        Returns:
            Dict 包含预测结果和元数据
        """
        if self.main_model is None:
            raise RuntimeError("模型未加载")
        
        # 验证输入维度
        if feature_vector.shape[1] != len(self.FEATURE_ORDER):
            raise ValueError(
                f"特征维度不匹配: 输入 {feature_vector.shape[1]}, "
                f"预期 {len(self.FEATURE_ORDER)}"
            )
        
        # 获取pH值
        ph = float(feature_vector[0][0])
        
        # 确定使用哪个模型
        ph_model_key = self._get_ph_model_key(ph)
        
        # 暂时强制使用主模型，避免子模型过拟合问题
        use_ph_model = False  # 强制使用主模型
        
        if use_ph_model and ph_model_key is not None and ph_model_key in self.ph_models:
            # 使用子模型预测
            feature_vector_no_ph = feature_vector[:, 1:]  # 去掉第一列pH
            prediction = self.ph_models[ph_model_key].predict(feature_vector_no_ph)[0]
            method = f'ph_{ph_model_key}_model'
            logger.info(f"使用 pH={ph_model_key} 子模型预测: {prediction:.4f} M (输入pH={ph:.1f})")
        else:
            # 使用主模型预测
            prediction = self.main_model.predict(feature_vector)[0]
            method = 'main_model'
            ph_model_key = None
            logger.info(f"使用主模型预测: {prediction:.4f} M (输入pH={ph:.1f})")
        
        # 计算置信度
        confidence = self._calculate_confidence(prediction, ph, ph_model_key)
        
        # 生成警告
        warnings = self._generate_warnings(feature_vector[0], prediction, ph_model_key)
        
        result = {
            'concentration': float(prediction),
            'ph_model_used': ph_model_key,
            'ph_input': ph,
            'method': method,
            'confidence': float(confidence),
            'warnings': warnings,
            'is_valid': len(warnings) == 0
        }
        
        logger.info(f"最终预测结果: {prediction:.4f} M (方法: {method})")
        
        return result
    
    def _calculate_confidence(self, prediction: float, ph: float, ph_model_key: Optional[int]) -> float:
        """
        计算置信度
        
        基于：
        1. 是否使用了对应pH范围的子模型
        2. 预测值是否在训练范围内
        """
        confidence = 0.6  # 基础置信度
        
        # 如果使用了子模型，增加置信度
        if ph_model_key is not None:
            confidence += 0.25
            
            # 如果预测值在该pH的训练范围内，再增加置信度
            if self.ph_stats and ph_model_key in self.ph_stats:
                stats = self.ph_stats[ph_model_key]
                if stats['min_concentration'] <= prediction <= stats['max_concentration']:
                    confidence += 0.15
        else:
            # 使用主模型，置信度较低
            confidence += 0.1
        
        return float(np.clip(confidence, 0.1, 1.0))
    
    def _generate_warnings(self, features: np.ndarray, prediction: float, ph_model_key: Optional[int]) -> List[str]:
        """生成使用警告"""
        warnings = []
        
        ph = features[0]
        r, g, b = features[1], features[2], features[3]
        
        # pH 范围检查
        if ph < 2 or ph > 12:
            warnings.append(
                f"pH 值 {ph:.1f} 超出模型支持范围 (2-12)，"
                f"预测结果可能不可靠"
            )
        
        # 检查是否使用了子模型（仅当存在子模型时显示此警告）
        if ph_model_key is None and len(self.ph_models) > 0:
            if 2 <= ph <= 12:
                warnings.append(
                    f"pH={ph:.1f} 在支持范围内但未能匹配到子模型，"
                    f"使用主模型预测，结果可能不够精确"
                )
            else:
                warnings.append(
                    f"pH={ph:.1f} 超出子模型支持范围，"
                    f"使用主模型预测"
                )
        
        # 浓度范围检查
        if prediction < 0:
            warnings.append(
                f"预测浓度为负值 ({prediction:.4f} M)，"
                f"可能是输入图像或 pH 值有误"
            )
        elif prediction > 0.02:  # 20 mM
            warnings.append(
                f"预测浓度 {prediction:.4f} M 超出典型范围，"
                f"请检查输入数据"
            )
        
        # 颜色值合理性检查
        if r < 10 and g < 10 and b < 10:
            warnings.append("图像颜色过暗，可能影响预测精度")
        
        if r > 250 and g > 250 and b > 250:
            warnings.append("图像颜色过亮，可能存在过曝")
        
        rgb_variance = np.var([r, g, b])
        if rgb_variance < 100:
            warnings.append("图像颜色过于均匀，可能未检测到有效溶液")
        
        return warnings
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        info = {
            'model_type': type(self.main_model).__name__ if self.main_model else None,
            'version': self.version,
            'feature_count': len(self.FEATURE_ORDER),
            'features': self.FEATURE_ORDER,
            'valid_ph_range': self.VALID_PH_RANGE,
            'valid_concentration_range': self.VALID_CONCENTRATION_RANGE,
            'ph_models_available': sorted(self.ph_models.keys()) if self.ph_models else [],
            'ph_stats': self.ph_stats
        }
        
        # 添加主模型特定参数
        if self.main_model:
            if hasattr(self.main_model, 'n_estimators'):
                info['n_estimators'] = self.main_model.n_estimators
            if hasattr(self.main_model, 'feature_importances_'):
                importances = dict(zip(
                    self.FEATURE_ORDER, 
                    self.main_model.feature_importances_.tolist()
                ))
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
