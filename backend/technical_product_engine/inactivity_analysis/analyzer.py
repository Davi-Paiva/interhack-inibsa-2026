"""
Inactivity analyzer module.

Orchestrates expected cycle estimation and inactivity computation
to produce a consolidated assessment for a client-product pair.
"""

from dataclasses import dataclass
from typing import Optional, Any

from .expected_cycle import estimate_expected_cycle
from .inactivity_calculator import compute_inactivity


@dataclass(frozen=True)
class InactivityAssessment:
    expected_cycle_days: float
    days_since_last_order: int
    inactivity_ratio: float
    inactivity_score: float
    is_inactive: bool


_INACTIVITY_THRESHOLD: float = 1.5


class InactivityAnalyzer:
    """Produces an InactivityAssessment for a given context."""

    def analyze(
        self,
        ctx: Any,
        peer_cycle: Optional[float] = None,
    ) -> InactivityAssessment:
        expected_cycle: float = estimate_expected_cycle(ctx, peer_cycle=peer_cycle)

        # Get product-specific days since last order from features
        # Try features.days_since_last_product_order first (correct field)
        # Fall back to top-level days_since_last_order for compatibility
        days_since_last_order: int = int(
            getattr(getattr(ctx, "features", None), "days_since_last_product_order", None)
            or getattr(ctx, "days_since_last_order", 0)
            or 0
        )

        inactivity_ratio, inactivity_score = compute_inactivity(
            days_since_last_order=days_since_last_order,
            expected_cycle_days=expected_cycle,
        )

        is_inactive: bool = inactivity_ratio > _INACTIVITY_THRESHOLD

        return InactivityAssessment(
            expected_cycle_days=expected_cycle,
            days_since_last_order=days_since_last_order,
            inactivity_ratio=inactivity_ratio,
            inactivity_score=inactivity_score,
            is_inactive=is_inactive,
        )
