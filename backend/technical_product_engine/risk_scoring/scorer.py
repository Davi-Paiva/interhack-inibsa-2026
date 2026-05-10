"""
Risk scoring orchestrator.

This module coordinates the risk scoring process, combining
drift signals and inactivity metrics to generate comprehensive
risk assessments with business priority scoring.
"""

import math
from typing import List, Optional
from dataclasses import dataclass

from ..domain.signals import DriftSignal
from ..domain.enums import SignalType
from .weights import (
    INACTIVITY_WEIGHT,
    VOLUME_DRIFT_WEIGHT,
    INTERVAL_DRIFT_WEIGHT,
    PEER_DRIFT_WEIGHT,
)
from .thresholds import classify_risk_level, classify_priority_level


def _safe(value: Optional[float]) -> float:
    """Return a finite float >= 0, treating None and NaN as 0.
    
    Args:
        value: Input value to sanitize
        
    Returns:
        Sanitized float value
    """
    try:
        v = float(value) if value is not None else 0.0
        return max(0.0, v if math.isfinite(v) else 0.0)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class RiskAssessment:
    """Complete risk assessment result.
    
    Attributes:
        risk_score: Base risk score [0, 1]
        priority_score: Business-adjusted priority score
        risk_level: Classified risk level
        priority_level: Classified priority level
        inactivity_score: Inactivity component score
        volume_drift_score: Volume drift component score
        interval_drift_score: Interval drift component score
        peer_drift_score: Peer drift component score
    """
    risk_score: float
    priority_score: float
    risk_level: str
    priority_level: str
    inactivity_score: float
    volume_drift_score: float
    interval_drift_score: float
    peer_drift_score: float


class RiskScorer:
    """Computes weighted risk scores and business priority assessments."""

    def compute_from_signals(
        self,
        drift_signals: List[DriftSignal],
        inactivity_score: float,
        potential_gap: Optional[float] = None,
    ) -> RiskAssessment:
        """Compute risk assessment from drift signals and inactivity metrics.
        
        This is the primary entry point for computing risk scores from
        the outputs of drift detection and inactivity analysis modules.
        
        Args:
            drift_signals: List of detected drift signals
            inactivity_score: Inactivity score from inactivity analyzer
            potential_gap: Business opportunity (potential - current sales)
            
        Returns:
            Complete risk assessment with scores and classifications
        """
        # Extract drift scores by type
        volume_drift_score = self._extract_drift_score(drift_signals, SignalType.VOLUME_DRIFT)
        interval_drift_score = self._extract_drift_score(drift_signals, SignalType.INTERVAL_DRIFT)
        peer_drift_score = self._extract_drift_score(drift_signals, SignalType.PEER_DRIFT)
        
        # Compute base risk score
        return self.compute(
            inactivity_score=inactivity_score,
            volume_drift_score=volume_drift_score,
            interval_drift_score=interval_drift_score,
            peer_drift_score=peer_drift_score,
            potential_gap=potential_gap,
        )

    def compute(
        self,
        inactivity_score: float,
        volume_drift_score: float = 0.0,
        interval_drift_score: float = 0.0,
        peer_drift_score: float = 0.0,
        potential_gap: Optional[float] = None,
    ) -> RiskAssessment:
        """Compute risk assessment from component scores.
        
        Args:
            inactivity_score: Inactivity deterioration score [0, 1]
            volume_drift_score: Volume drift severity score [0, 1]
            interval_drift_score: Interval drift severity score [0, 1]
            peer_drift_score: Peer drift severity score [0, 1]
            potential_gap: Business opportunity gap (for priority scoring)
            
        Returns:
            Complete risk assessment
        """
        # Sanitize all inputs
        inactivity = _safe(inactivity_score)
        volume_drift = _safe(volume_drift_score)
        interval_drift = _safe(interval_drift_score)
        peer_drift = _safe(peer_drift_score)
        
        # Compute weighted base risk score
        base_score = (
            inactivity * INACTIVITY_WEIGHT
            + volume_drift * VOLUME_DRIFT_WEIGHT
            + interval_drift * INTERVAL_DRIFT_WEIGHT
            + peer_drift * PEER_DRIFT_WEIGHT
        )
        
        # Clamp to [0, 1]
        base_score = max(0.0, min(1.0, base_score))
        
        # Compute business-adjusted priority score
        gap = _safe(potential_gap)
        if gap > 0.0:
            # Use logarithmic scaling to avoid over-weighting large gaps
            # log(1 + gap) provides smooth scaling without extreme values
            opportunity_multiplier = 1.0 + math.log(1.0 + gap)
            priority_score = base_score * opportunity_multiplier
        else:
            priority_score = base_score
        
        # Classify risk and priority levels
        risk_level = classify_risk_level(base_score)
        priority_level = classify_priority_level(priority_score)
        
        return RiskAssessment(
            risk_score=base_score,
            priority_score=priority_score,
            risk_level=risk_level,
            priority_level=priority_level,
            inactivity_score=inactivity,
            volume_drift_score=volume_drift,
            interval_drift_score=interval_drift,
            peer_drift_score=peer_drift,
        )
    
    def _extract_drift_score(
        self,
        signals: List[DriftSignal],
        signal_type: SignalType
    ) -> float:
        """Extract the maximum severity score for a specific signal type.
        
        If multiple signals of the same type exist, takes the maximum severity
        as it represents the strongest detected pattern.
        
        Args:
            signals: List of drift signals
            signal_type: Type of signal to extract
            
        Returns:
            Maximum severity score for the signal type, or 0.0 if not found
        """
        matching_signals = [s for s in signals if s.signal_type == signal_type]
        
        if not matching_signals:
            return 0.0
        
        return max(s.severity for s in matching_signals)
