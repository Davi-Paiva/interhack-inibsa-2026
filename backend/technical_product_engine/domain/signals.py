"""
Signal definitions for the technical product engine.

This module defines various signals and indicators that are used
to detect patterns and behaviors in customer data.
"""
from dataclasses import dataclass

from .enums import SignalType


@dataclass
class DriftSignal:
    """Represents a detected drift signal in customer-product behavior.
    
    Attributes:
        signal_type: The category of drift detected
        severity: Normalized severity score (0.0 to 1.0)
        metric_value: The actual measured value that triggered the signal
        threshold: The threshold value that was exceeded
    """
    
    signal_type: SignalType
    severity: float
    metric_value: float
    threshold: float
    
    def __post_init__(self):
        """Validate signal attributes."""
        if not 0.0 <= self.severity <= 1.0:
            raise ValueError(f"Severity must be between 0.0 and 1.0, got {self.severity}")
        if self.metric_value < 0:
            raise ValueError(f"Metric value cannot be negative, got {self.metric_value}")
        if self.threshold < 0:
            raise ValueError(f"Threshold cannot be negative, got {self.threshold}")

from dataclasses import dataclass
from typing import Any, Optional

from ..inactivity_analysis.analyzer import InactivityAnalyzer


@dataclass(frozen=True)
class InactivitySignal:
	"""Signal produced by inactivity analysis."""

	expected_cycle_days: float
	days_since_last_order: int
	inactivity_ratio: float
	inactivity_score: float
	is_inactive: bool


def build_inactivity_signal(
	ctx: Any,
	peer_cycle: Optional[float] = None,
) -> InactivitySignal:
	"""Build an inactivity signal from a client-product context."""

	assessment = InactivityAnalyzer().analyze(ctx, peer_cycle=peer_cycle)

	return InactivitySignal(
		expected_cycle_days=assessment.expected_cycle_days,
		days_since_last_order=assessment.days_since_last_order,
		inactivity_ratio=assessment.inactivity_ratio,
		inactivity_score=assessment.inactivity_score,
		is_inactive=assessment.is_inactive,
	)


__all__ = ["InactivitySignal", "build_inactivity_signal"]
