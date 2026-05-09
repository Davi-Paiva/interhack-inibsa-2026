"""
Volume-based drift detection.

This module detects deterioration in purchase volume by identifying
significant negative growth trends in recent sales activity for a
customer-product relationship.
"""
from typing import List

from ..domain.models import ClientProductContext
from ..domain.signals import DriftSignal
from ..domain.enums import SignalType


# Configuration constants
VOLUME_DRIFT_WARNING_THRESHOLD = -0.2  # -20% growth
VOLUME_DRIFT_STRONG_THRESHOLD = -0.4   # -40% growth
NEGLIGIBLE_GROWTH_THRESHOLD = 0.05     # Ignore fluctuations within ±5%


def _is_negligible_growth(growth: float) -> bool:
    """Check if growth is within negligible fluctuation range.
    
    Args:
        growth: Growth rate (e.g., -0.15 for -15%)
        
    Returns:
        True if growth is within negligible range
    """
    return abs(growth) <= NEGLIGIBLE_GROWTH_THRESHOLD


def _compute_severity(growth: float) -> float:
    """Compute normalized severity score from growth rate.
    
    Maps negative growth to a severity score between 0.0 and 1.0.
    
    Args:
        growth: Sales growth rate (negative values indicate decline)
        
    Returns:
        Severity score between 0.0 and 1.0
    """
    if growth >= VOLUME_DRIFT_WARNING_THRESHOLD:
        return 0.0
    
    if growth >= VOLUME_DRIFT_STRONG_THRESHOLD:
        # Warning to strong range: map to 0.3 - 0.7
        normalized = (growth - VOLUME_DRIFT_WARNING_THRESHOLD) / (
            VOLUME_DRIFT_STRONG_THRESHOLD - VOLUME_DRIFT_WARNING_THRESHOLD
        )
        return 0.3 + (0.4 * normalized)
    
    # Strong decline: map to 0.7 - 1.0
    # More severe as growth becomes more negative
    excess = abs(growth) - abs(VOLUME_DRIFT_STRONG_THRESHOLD)
    
    # Asymptotic scaling: approaches 1.0 as growth becomes extremely negative
    # Use exponential decay to map remaining range
    return min(0.7 + (0.3 * (excess / (excess + 0.3))), 1.0)


def detect_volume_drift(context: ClientProductContext) -> List[DriftSignal]:
    """Detect volume-based drift for a customer-product relationship.
    
    Analyzes whether recent sales growth shows significant negative trends
    that indicate deterioration in the commercial relationship.
    
    Args:
        context: Client-product analytical context with precomputed features
        
    Returns:
        List of drift signals (empty if no drift detected)
    """
    signals: List[DriftSignal] = []
    
    # Extract relevant metric
    sales_growth = context.features.sales_growth_30d
    
    # Ignore negligible fluctuations
    if _is_negligible_growth(sales_growth):
        return signals
    
    # Check for positive growth (no drift)
    if sales_growth >= 0:
        return signals
    
    # Check if warning threshold is exceeded
    if sales_growth < VOLUME_DRIFT_WARNING_THRESHOLD:
        severity = _compute_severity(sales_growth)
        
        signal = DriftSignal(
            signal_type=SignalType.VOLUME_DRIFT,
            severity=severity,
            metric_value=abs(sales_growth),  # Use absolute value for metric
            threshold=abs(VOLUME_DRIFT_WARNING_THRESHOLD)
        )
        signals.append(signal)
    
    return signals
