"""
Risk scoring weights configuration.

This module defines and manages the weights assigned to
different risk factors in the scoring algorithm.
"""

import math

INACTIVITY_WEIGHT: float = 0.35
VOLUME_DRIFT_WEIGHT: float = 0.25
PEER_DRIFT_WEIGHT: float = 0.20
RETURN_RISK_WEIGHT: float = 0.10
CAMPAIGN_DROP_WEIGHT: float = 0.10


def get_default_weights() -> dict[str, float]:
    """Return the default risk scoring weights."""
    return {
        "inactivity": INACTIVITY_WEIGHT,
        "volume_drift": VOLUME_DRIFT_WEIGHT,
        "peer_drift": PEER_DRIFT_WEIGHT,
        "return_risk": RETURN_RISK_WEIGHT,
        "campaign_drop": CAMPAIGN_DROP_WEIGHT,
    }


def validate_weights(weights: dict[str, float]) -> bool:
    """Validate that weights are non-negative and sum approximately to 1.0."""
    values = tuple(weights.values())

    if any((not math.isfinite(value)) or value < 0.0 for value in values):
        return False

    return math.isclose(sum(values), 1.0, rel_tol=1e-9, abs_tol=1e-9)
