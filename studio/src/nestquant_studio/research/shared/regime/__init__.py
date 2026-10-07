"""NestQuant regime detection module."""

from nestquant_studio.research.shared.regime.base import RegimeDetector, RegimePrediction
from nestquant_studio.research.shared.regime.labels import RegimeLabel, REGIME_PARAMS
from nestquant_studio.research.shared.regime.adx_regime import ADXRegimeDetector
from nestquant_studio.research.shared.regime.hybrid import HybridRegimeDetector

__all__ = [
    "RegimeDetector",
    "RegimePrediction",
    "RegimeLabel",
    "REGIME_PARAMS",
    "ADXRegimeDetector",
    "HybridRegimeDetector",
]
