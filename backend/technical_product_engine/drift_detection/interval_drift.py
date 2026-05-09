"""
Interval-based drift detection.

This module detects inactivity deterioration by identifying when the time
since the last purchase significantly exceeds the expected purchasing cycle
for a customer-product relationship.
"""
from typing import List, Optional

from ..domain.models import ClientProductContext
from ..domain.signals import DriftSignal
from ..domain.enums import SignalType


# Configuration constants
INTERVAL_DRIFT_MEDIUM_THRESHOLD = 1.5
INTERVAL_DRIFT_HIGH_THRESHOLD = 2.0
MIN_FREQUENCY_THRESHOLD = 0.01  # Minimum frequency to compute expected interval
DEFAULT_EXPECTED_INTERVAL_DAYS = 365  # Default cycle when frequency is too low


def _compute_expected_interval(frequency: float) -> float:
    """Compute expected purchase interval from frequency.
    
    Args:
        frequency: Purchase frequency (purchases per day)
        
    Returns:
        Expected interval in days between purchases
    """
    if frequency < MIN_FREQUENCY_THRESHOLD:
        return DEFAULT_EXPECTED_INTERVAL_DAYS
    
    return 1.0 / frequency


def _compute_inactivity_ratio(
    days_since_last_order: int,
    expected_interval: float
) -> float:
    """Compute the inactivity ratio.
    
    Args:
        days_since_last_order: Days since the last product purchase
        expected_interval: Expected interval between purchases
        
    Returns:
        Ratio of actual inactivity to expected interval
    """
    if expected_interval <= 0:
        return 0.0
    
    return days_since_last_order / expected_interval


def _compute_severity(inactivity_ratio: float) -> float:
    """Compute normalized severity score from inactivity ratio.
    
    Uses a sigmoid-like transformation to map ratio to [0, 1] range.
    
    Args:
        inactivity_ratio: Ratio of actual to expected interval
        
    Returns:
        Severity score between 0.0 and 1.0
    """
    if inactivity_ratio <= 1.0:
        return 0.0
    
    # Linear scaling between thresholds
    if inactivity_ratio <= INTERVAL_DRIFT_MEDIUM_THRESHOLD:
        # Low severity: ratio between 1.0 and medium threshold
        return 0.3 * ((inactivity_ratio - 1.0) / (INTERVAL_DRIFT_MEDIUM_THRESHOLD - 1.0))
    
    if inactivity_ratio <= INTERVAL_DRIFT_HIGH_THRESHOLD:
        # Medium severity: ratio between medium and high threshold
        base = 0.3
        range_severity = 0.4  # Goes from 0.3 to 0.7
        normalized = (inactivity_ratio - INTERVAL_DRIFT_MEDIUM_THRESHOLD) / (
            INTERVAL_DRIFT_HIGH_THRESHOLD - INTERVAL_DRIFT_MEDIUM_THRESHOLD
        )
        return base + (range_severity * normalized)
    
    # High severity: ratio exceeds high threshold
    # Asymptotic approach to 1.0
    excess = inactivity_ratio - INTERVAL_DRIFT_HIGH_THRESHOLD
    return min(0.7 + (0.3 * (1.0 - (1.0 / (1.0 + excess)))), 1.0)


def detect_interval_drift(context: ClientProductContext) -> List[DriftSignal]:
    """Detect interval-based drift for a customer-product relationship.
    
    Analyzes whether the time since the last purchase significantly exceeds
    the expected purchasing cycle, indicating potential abandonment or
    deterioration in the commercial relationship.
    
    Args:
        context: Client-product analytical context with precomputed features
        
    Returns:
        List of drift signals (empty if no drift detected)
    """
    signals: List[DriftSignal] = []
    
    # Extract relevant metrics
    days_since_last_order = context.features.days_since_last_product_order
    frequency = context.features.client_product_frequency
    
    # Handle edge cases
    if days_since_last_order < 0:
        # Invalid data
        return signals
    
    if days_since_last_order == 0:
        # Recent purchase, no inactivity
        return signals
    
    # Compute expected interval
    expected_interval = _compute_expected_interval(frequency)
    
    # Compute inactivity ratio
    inactivity_ratio = _compute_inactivity_ratio(
        days_since_last_order,
        expected_interval
    )
    
    # Check if drift threshold is exceeded
    if inactivity_ratio > INTERVAL_DRIFT_MEDIUM_THRESHOLD:
        severity = _compute_severity(inactivity_ratio)
        
        signal = DriftSignal(
            signal_type=SignalType.INTERVAL_DRIFT,
            severity=severity,
            metric_value=inactivity_ratio,
            threshold=INTERVAL_DRIFT_MEDIUM_THRESHOLD
        )
        signals.append(signal)
    
    return signals
