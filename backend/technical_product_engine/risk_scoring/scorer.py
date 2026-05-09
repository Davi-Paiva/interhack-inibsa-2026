"""
Risk scoring orchestrator.

This module coordinates the risk scoring process, combining
various risk factors to generate final risk scores.
"""

import math
from typing import Optional

from .weights import (
    INACTIVITY_WEIGHT,
    VOLUME_DRIFT_WEIGHT,
    PEER_DRIFT_WEIGHT,
    RETURN_RISK_WEIGHT,
    CAMPAIGN_DROP_WEIGHT,
)
from .thresholds import classify_risk_level


def _safe(value: Optional[float]) -> float:
    """Return a finite float >= 0, treating None and NaN as 0."""
    try:
        v = float(value) if value is not None else 0.0
        return v if math.isfinite(v) else 0.0
    except (TypeError, ValueError):
        return 0.0


class RiskScorer:
    """Computes a weighted risk score and classifies it."""

    def compute(
        self,
        inactivity_score: float,
        volume_drift_score: float = 0.0,
        peer_drift_score: float = 0.0,
        return_risk_score: float = 0.0,
        campaign_drop_score: float = 0.0,
        potential_gap: Optional[float] = None,
    ) -> dict:
        base_score: float = (
            _safe(inactivity_score) * INACTIVITY_WEIGHT
            + _safe(volume_drift_score) * VOLUME_DRIFT_WEIGHT
            + _safe(peer_drift_score) * PEER_DRIFT_WEIGHT
            + _safe(return_risk_score) * RETURN_RISK_WEIGHT
            + _safe(campaign_drop_score) * CAMPAIGN_DROP_WEIGHT
        )

        base_score = max(0.0, min(1.0, base_score))

        gap = _safe(potential_gap)
        priority_score: float = (
            base_score * math.log(1.0 + gap) if gap > 0.0 else base_score
        )

        return {
            "risk_score": base_score,
            "priority_score": priority_score,
            "risk_level": classify_risk_level(base_score),
        }
