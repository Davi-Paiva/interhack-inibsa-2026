"""
Inactivity calculation module.

This module calculates and analyzes customer inactivity periods,
identifying unusual gaps in purchase behavior.
"""

import math

_MAX_RATIO: float = 5.0
_SCORE_SCALE: float = 2.5


def compute_inactivity(
    days_since_last_order: int,
    expected_cycle_days: float,
) -> tuple[float, float]:
    """Compute inactivity ratio and score for a client-product pair.

    Parameters
    ----------
    days_since_last_order:
        Number of days elapsed since the last order. Negative values are
        clamped to 0.
    expected_cycle_days:
        Expected purchase cycle in days. Must be > 0.

    Returns
    -------
    (inactivity_ratio, inactivity_score)
        inactivity_ratio  -- days_since_last_order / expected_cycle_days,
                             clamped to [0, 5.0].
        inactivity_score  -- linear score in [0, 1] derived from the ratio.
    """
    # Sanitise days
    try:
        days = float(days_since_last_order) if days_since_last_order is not None else 0.0
        if not math.isfinite(days):
            days = 0.0
    except (TypeError, ValueError):
        days = 0.0
    days = max(0.0, days)

    # Sanitise expected cycle
    try:
        cycle = float(expected_cycle_days) if expected_cycle_days is not None else 0.0
        if not math.isfinite(cycle):
            cycle = 0.0
    except (TypeError, ValueError):
        cycle = 0.0

    if cycle <= 0.0:
        return (_MAX_RATIO, 1.0)

    inactivity_ratio: float = min(days / cycle, _MAX_RATIO)
    inactivity_score: float = min(inactivity_ratio / _SCORE_SCALE, 1.0)

    return (inactivity_ratio, inactivity_score)
