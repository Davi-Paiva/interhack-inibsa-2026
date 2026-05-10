"""
Risk scoring thresholds.

This module defines thresholds for classifying risk levels
and triggering alerts based on risk scores.

Thresholds are calibrated to balance sensitivity and specificity
in detecting meaningful abandonment risk patterns.
"""

import math
from typing import Optional

# Risk level classification thresholds
LOW_RISK_THRESHOLD: float = 0.30
MEDIUM_RISK_THRESHOLD: float = 0.60
HIGH_RISK_THRESHOLD: float = 0.80

# Priority score thresholds (business opportunity adjusted)
LOW_PRIORITY_THRESHOLD: float = 0.50
MEDIUM_PRIORITY_THRESHOLD: float = 0.90
HIGH_PRIORITY_THRESHOLD: float = 1.40


def classify_risk_level(score: Optional[float]) -> str:
    """Classify a risk score into a risk level string.
    
    Risk levels indicate the severity of abandonment risk:
    - low: Normal behavior, no immediate concern
    - medium: Early warning signs, monitor closely
    - high: Clear deterioration signals, intervention recommended
    - critical: Severe risk, immediate action required

    Args:
        score: Risk score in range [0, 1]. None and NaN treated as 0.

    Returns:
        Risk level: "low" | "medium" | "high" | "critical"
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


def classify_priority_level(score: Optional[float]) -> str:
    """Classify a priority score into a priority level string.
    
    Priority levels combine risk severity with business opportunity:
    - low: Low risk or low business value
    - medium: Moderate risk/value combination
    - high: Significant risk-adjusted opportunity
    - critical: Maximum priority for intervention

    Args:
        score: Priority score. None and NaN treated as 0.

    Returns:
        Priority level: "low" | "medium" | "high" | "critical"
    """
    try:
        value = float(score) if score is not None else 0.0
        if not math.isfinite(value):
            value = 0.0
    except (TypeError, ValueError):
        value = 0.0

    value = max(0.0, value)  # No upper bound clamp for priority

    if value < LOW_PRIORITY_THRESHOLD:
        return "low"
    if value < MEDIUM_PRIORITY_THRESHOLD:
        return "medium"
    if value < HIGH_PRIORITY_THRESHOLD:
        return "high"
    return "critical"
