"""
Peer-based drift detection.

This module detects drift by comparing individual customer-product behavior
against peer group patterns to identify divergence from market norms.
"""
from typing import List, Optional
from dataclasses import dataclass

from ..domain.models import ClientProductContext
from ..domain.signals import DriftSignal
from ..domain.enums import SignalType


# Configuration constants
PEER_DRIFT_MODERATE_THRESHOLD = 0.3   # 30% deviation from peer average
PEER_DRIFT_STRONG_THRESHOLD = 0.5     # 50% deviation from peer average
MIN_PEER_SAMPLE_SIZE = 5              # Minimum peers needed for valid comparison


@dataclass
class PeerMetrics:
    """Peer comparison metrics.
    
    Attributes:
        peer_avg_growth: Average growth rate among peer group
        peer_std_growth: Standard deviation of peer growth rates
        peer_count: Number of peers in the comparison group
    """
    peer_avg_growth: float
    peer_std_growth: float
    peer_count: int


def _compute_peer_deviation(
    customer_growth: float,
    peer_avg_growth: float
) -> float:
    """Compute the deviation from peer average.
    
    Args:
        customer_growth: Customer's growth rate
        peer_avg_growth: Average growth rate of peers
        
    Returns:
        Absolute deviation from peer average
    """
    return abs(customer_growth - peer_avg_growth)


def _compute_severity(
    deviation: float,
    customer_growth: float,
    peer_avg_growth: float
) -> float:
    """Compute normalized severity score from peer deviation.
    
    Higher severity when customer declines while peers are stable/growing.
    
    Args:
        deviation: Absolute deviation from peer average
        customer_growth: Customer's growth rate
        peer_avg_growth: Average growth rate of peers
        
    Returns:
        Severity score between 0.0 and 1.0
    """
    # Only flag as drift if customer is declining AND doing worse than peers
    if customer_growth >= peer_avg_growth:
        return 0.0
    
    if deviation < PEER_DRIFT_MODERATE_THRESHOLD:
        return 0.0
    
    if deviation < PEER_DRIFT_STRONG_THRESHOLD:
        # Moderate deviation: map to 0.3 - 0.7
        normalized = (deviation - PEER_DRIFT_MODERATE_THRESHOLD) / (
            PEER_DRIFT_STRONG_THRESHOLD - PEER_DRIFT_MODERATE_THRESHOLD
        )
        return 0.3 + (0.4 * normalized)
    
    # Strong deviation: map to 0.7 - 1.0
    excess = deviation - PEER_DRIFT_STRONG_THRESHOLD
    return min(0.7 + (0.3 * (excess / (excess + 0.5))), 1.0)


def detect_peer_drift(
    context: ClientProductContext,
    peer_metrics: Optional[PeerMetrics] = None
) -> List[DriftSignal]:
    """Detect peer-based drift for a customer-product relationship.
    
    Analyzes whether the customer's behavior is significantly diverging
    from peer patterns, particularly when peers are stable but the customer
    is declining.
    
    Args:
        context: Client-product analytical context with precomputed features
        peer_metrics: Peer comparison metrics (if None, no comparison possible)
        
    Returns:
        List of drift signals (empty if no drift detected)
    """
    signals: List[DriftSignal] = []
    
    # Cannot detect peer drift without peer metrics
    if peer_metrics is None:
        return signals
    
    # Need sufficient peer sample for valid comparison
    if peer_metrics.peer_count < MIN_PEER_SAMPLE_SIZE:
        return signals
    
    # Extract customer growth
    customer_growth = context.features.sales_growth_30d
    
    # Compute deviation from peer average
    deviation = _compute_peer_deviation(
        customer_growth,
        peer_metrics.peer_avg_growth
    )
    
    # Check if deviation threshold is exceeded
    if deviation >= PEER_DRIFT_MODERATE_THRESHOLD:
        severity = _compute_severity(
            deviation,
            customer_growth,
            peer_metrics.peer_avg_growth
        )
        
        # Only emit signal if severity is non-zero
        if severity > 0.0:
            signal = DriftSignal(
                signal_type=SignalType.PEER_DRIFT,
                severity=severity,
                metric_value=deviation,
                threshold=PEER_DRIFT_MODERATE_THRESHOLD
            )
            signals.append(signal)
    
    return signals

