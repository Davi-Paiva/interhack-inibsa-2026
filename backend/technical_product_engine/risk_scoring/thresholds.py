"""
Risk scoring thresholds.

This module defines thresholds for classifying risk levels
and triggering alerts based on risk scores.
"""

import math
from typing import Optional

LOW_RISK_THRESHOLD: float = 0.30
MEDIUM_RISK_THRESHOLD: float = 0.60
HIGH_RISK_THRESHOLD: float = 0.80


def classify_risk_level(score: Optional[float]) -> str:
    """Classify a risk score into a risk level string.

    Parameters
    ----------
    score:
        A numeric risk score. Clamped to [0, 1] before classification.
        None and NaN are treated as 0.

    Returns
    -------
    "low" | "medium" | "high" | "critical"
    """
    try:
        value = float(score) if score is not None else 0.0
        if not math.isfinite(value):
            value = 0.0
    except (TypeError, ValueError):
        value = 0.0

    value = max(0.0, min(1.0, value))

    if value < LOW_RISK_THRESHOLD:
        return "low"
    if value < MEDIUM_RISK_THRESHOLD:
        return "medium"
    if value < HIGH_RISK_THRESHOLD:
        return "high"
    return "critical"
