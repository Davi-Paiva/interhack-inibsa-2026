"""
Risk scoring weights configuration.

This module defines and manages the weights assigned to
different risk factors in the scoring algorithm.

The weights represent the relative importance of each risk factor
in the final risk score composition. They sum to 1.0 to ensure
normalized scoring in the [0, 1] range.
"""

import math
from typing import Dict

# Core risk factor weights (sum to 1.0)
INACTIVITY_WEIGHT: float = 0.40  # Inactivity is the strongest signal
VOLUME_DRIFT_WEIGHT: float = 0.25  # Sales decline is critical
INTERVAL_DRIFT_WEIGHT: float = 0.20  # Purchase pattern disruption
PEER_DRIFT_WEIGHT: float = 0.15  # Peer comparison provides context


def get_default_weights() -> Dict[str, float]:
    """Return the default risk scoring weights.
    
    Returns:
        Dictionary mapping risk factor names to their weights
    """
    return {
        "inactivity": INACTIVITY_WEIGHT,
        "volume_drift": VOLUME_DRIFT_WEIGHT,
        "interval_drift": INTERVAL_DRIFT_WEIGHT,
        "peer_drift": PEER_DRIFT_WEIGHT,
    }


def validate_weights(weights: Dict[str, float]) -> bool:
    """Validate that weights are non-negative and sum approximately to 1.0.
    
    Args:
        weights: Dictionary of weight values to validate
        
    Returns:
        True if weights are valid, False otherwise
    """
    values = tuple(weights.values())

    # Check all values are finite and non-negative
    if any((not math.isfinite(value)) or value < 0.0 for value in values):
        return False

    # Check sum is approximately 1.0
    return math.isclose(sum(values), 1.0, rel_tol=1e-9, abs_tol=1e-9)
