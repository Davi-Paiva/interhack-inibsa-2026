"""
Expected purchase cycle analysis.

This module determines expected purchase cycles for customers
and identifies deviations from normal patterns.
"""

import math
from typing import Optional, Any

_MIN_CYCLE: float = 7.0
_MAX_CYCLE: float = 180.0
_DEFAULT_CYCLE: float = 45.0


def _is_valid_positive(value: Any) -> bool:
    """Return True if value is a finite number greater than zero."""
    try:
        return value is not None and math.isfinite(float(value)) and float(value) > 0
    except (TypeError, ValueError):
        return False


def estimate_expected_cycle(ctx: Any, peer_cycle: Optional[float] = None) -> float:
    """Estimate the expected purchase cycle in days for a client-product pair.

    Priority:
    1. Client-product frequency (requires >= 2 orders).
    2. Customer-level frequency.
    3. Peer cycle provided by caller.
    4. Global default (45 days).

    Result is clamped to [7, 180] days.
    """
    raw: Optional[float] = None

    # 1. Client-product frequency
    cp_freq = getattr(ctx, "client_product_frequency", None)
    cp_orders = getattr(ctx, "client_product_total_orders", None)
    if _is_valid_positive(cp_freq):
        try:
            orders = int(cp_orders) if cp_orders is not None else 0
        except (TypeError, ValueError):
            orders = 0
        if orders >= 2:
            raw = 1.0 / float(cp_freq)

    # 2. Customer-level frequency
    if raw is None:
        cust_freq = getattr(ctx, "customer_frequency", None)
        if _is_valid_positive(cust_freq):
            raw = 1.0 / float(cust_freq)

    # 3. Peer cycle
    if raw is None:
        if peer_cycle is not None and _is_valid_positive(peer_cycle):
            raw = float(peer_cycle)

    # 4. Default
    if raw is None:
        raw = _DEFAULT_CYCLE

    return max(_MIN_CYCLE, min(_MAX_CYCLE, raw))

