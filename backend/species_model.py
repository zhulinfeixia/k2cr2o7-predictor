"""
Ion-species prediction model.

The deployed model predicts HCrO4- and Cr2O7^2- directly from color
features plus pH. CrO4^2- is then computed from the acid dissociation
equilibrium at 25 C:

    [CrO4^2-] = Ka2 * [HCrO4-] / [H+]
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

import joblib
import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)


class SpeciesPredictor:
    """Predict chromium(VI) ion species from backend image features."""

    FEATURE_ORDER = [
        "pH", "R", "G", "B", "H", "S", "V", "L", "a", "b",
        "R_over_G", "R_over_B", "G_over_B", "R_ratio", "G_ratio", "B_ratio",
    ]

    def __init__(self, model_path: Optional[str] = None):
        if model_path is None:
            model_path = Path(__file__).parent / "models" / "species_model.joblib"
        self.model_path = Path(model_path)
        self.model = None
        self.feature_cols: List[str] = []
        self.target_cols: List[str] = []
        self.valid_ph_range = (3.0, 8.0)
        self.ka1 = 2.94e-2
        self.ka2 = 1.26e-6
        self.k_dimer = 1.58e1
        self.target_transform = None
        self.model_name = None
        self.metrics: Dict[str, Any] = {}
        self._load_model()

    def _load_model(self) -> None:
        if not self.model_path.exists():
            raise FileNotFoundError(f"离子模型文件不存在: {self.model_path}")

        package = joblib.load(self.model_path)
        if not isinstance(package, dict) or "model" not in package:
            raise ValueError("离子模型文件格式不正确")

        self.model = package["model"]
        self.feature_cols = package.get("feature_cols", [])
        self.target_cols = package.get("target_cols", ["HCrO4_mM", "Cr2O7_mM"])
        self.valid_ph_range = tuple(package.get("valid_ph_range", self.valid_ph_range))
        self.ka1 = float(package.get("ka1", self.ka1))
        self.ka2 = float(package.get("ka2", self.ka2))
        self.k_dimer = float(package.get("k_dimer", self.k_dimer))
        self.target_transform = package.get("target_transform")
        self.model_name = package.get("model_name", type(self.model).__name__)
        self.metrics = package.get("cv_leave_pH_group", {})
        logger.info("离子模型加载成功: %s", self.model_name)

    def _predict_targets(self, model_feature_vector: np.ndarray) -> np.ndarray:
        raw = self.model.predict(model_feature_vector)
        if self.target_transform == "log1p":
            raw = np.expm1(raw)
        return np.clip(raw, 0.0, None)

    def predict(self, feature_vector: np.ndarray) -> Dict[str, Any]:
        if self.model is None:
            raise RuntimeError("离子模型未加载")
        if feature_vector.shape[1] != len(self.FEATURE_ORDER):
            raise ValueError(
                f"特征维度不匹配: 输入 {feature_vector.shape[1]}, "
                f"预期 {len(self.FEATURE_ORDER)}"
            )

        feature_dict = dict(zip(self.FEATURE_ORDER, feature_vector[0]))
        ph = float(feature_dict["pH"])
        model_feature_vector = pd.DataFrame(
            [[feature_dict[col] for col in self.feature_cols]],
            columns=self.feature_cols,
            dtype=float,
        )

        pred = self._predict_targets(model_feature_vector)[0]
        values = dict(zip(self.target_cols, pred))
        hcro4_mM = float(values.get("HCrO4_mM", 0.0))
        cr2o7_mM = float(values.get("Cr2O7_mM", 0.0))

        h = 10.0 ** (-ph)
        cro4_mM = float(self.ka2 * hcro4_mM / h)
        h2cro4_mM = float(hcro4_mM * h / self.ka1)
        total_cr_mM = float(h2cro4_mM + hcro4_mM + cro4_mM + 2.0 * cr2o7_mM)
        dimer_residual_mM = float(
            cr2o7_mM - self.k_dimer * np.square(hcro4_mM / 1000.0) * 1000.0
        )

        warnings = self._generate_warnings(ph, cro4_mM)
        confidence = self._calculate_confidence(ph)
        species = {
            "HCrO4_mM": hcro4_mM,
            "Cr2O7_mM": cr2o7_mM,
            "CrO4_mM": cro4_mM,
            "estimated_total_cr_mM": total_cr_mM,
            "dimer_residual_mM": dimer_residual_mM,
        }

        return {
            "species_concentrations": species,
            "confidence": confidence,
            "warnings": warnings,
            "model_info": {
                "model_name": self.model_name,
                "target_cols": self.target_cols,
                "computed_species": ["CrO4_mM", "estimated_total_cr_mM"],
                "valid_ph_range": self.valid_ph_range,
                "ka1": self.ka1,
                "ka2": self.ka2,
                "k_dimer": self.k_dimer,
            },
        }

    def _calculate_confidence(self, ph: float) -> float:
        ph_min, ph_max = self.valid_ph_range
        if ph < ph_min or ph > ph_max:
            return 0.35
        if ph >= 7.0:
            return 0.65
        return 0.85

    def _generate_warnings(self, ph: float, cro4_mM: float) -> List[str]:
        warnings: List[str] = []
        ph_min, ph_max = self.valid_ph_range
        if ph < ph_min or ph > ph_max:
            warnings.append(
                f"pH={ph:.1f} 超出离子模型训练范围 ({ph_min:g}-{ph_max:g})，"
                "离子预测结果可能不可靠"
            )
        if ph >= 7.0:
            warnings.append(
                "CrO4^2- 由 HCrO4- 和 pH 计算得到；pH 较高时该计算会放大 "
                "HCrO4- 的微小预测误差"
            )
        if cro4_mM > 20:
            warnings.append("计算得到的 CrO4^2- 浓度超出常见训练浓度范围，请复核样品条件")
        return warnings

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_type": self.model_name,
            "feature_count": len(self.feature_cols),
            "features": self.feature_cols,
            "target_cols": self.target_cols,
            "valid_ph_range": self.valid_ph_range,
            "constants": {
                "Ka1": self.ka1,
                "Ka2": self.ka2,
                "K_dimer": self.k_dimer,
            },
            "cv_leave_pH_group": self.metrics,
        }


_species_predictor_instance = None


def get_species_predictor() -> SpeciesPredictor:
    global _species_predictor_instance
    if _species_predictor_instance is None:
        _species_predictor_instance = SpeciesPredictor()
    return _species_predictor_instance
