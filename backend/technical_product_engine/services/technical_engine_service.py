"""
Technical product engine service.

This service orchestrates the complete technical product risk analysis pipeline,
coordinating drift detection, inactivity analysis, and risk scoring to produce
comprehensive abandonment risk assessments for client-product relationships.
"""

import logging
from typing import List, Optional
from dataclasses import dataclass, asdict

from ..domain.models import ClientProductContext
from ..domain.signals import DriftSignal, build_inactivity_signal
from ..drift_detection.detector import DriftDetector
from ..inactivity_analysis.analyzer import InactivityAnalyzer
from ..risk_scoring.scorer import RiskScorer, RiskAssessment

logger = logging.getLogger(__name__)


@dataclass
class TechnicalRiskAssessment:
    """Complete technical risk assessment for a client-product relationship.
    
    Attributes:
        client_id: Client identifier
        product_id: Product identifier
        risk_score: Base risk score [0, 1]
        priority_score: Business-adjusted priority score
        risk_level: Classified risk level (low/medium/high/critical)
        priority_level: Classified priority level
        inactivity_score: Inactivity component score
        inactivity_ratio: Days since last order / expected cycle
        expected_cycle_days: Expected purchase cycle in days
        days_since_last_order: Days since last product purchase
        is_inactive: Whether relationship is flagged as inactive
        volume_drift_score: Volume drift component score
        interval_drift_score: Interval drift component score
        peer_drift_score: Peer drift component score
        potential_gap: Business opportunity (potential - current sales)
        drift_signal_count: Number of drift signals detected
    """
    client_id: str
    product_id: str
    risk_score: float
    priority_score: float
    risk_level: str
    priority_level: str
    inactivity_score: float
    inactivity_ratio: float
    expected_cycle_days: float
    days_since_last_order: int
    is_inactive: bool
    volume_drift_score: float
    interval_drift_score: float
    peer_drift_score: float
    potential_gap: float
    drift_signal_count: int


class TechnicalProductEngine:
    """Main engine for technical product risk analysis.
    
    This service coordinates the complete analytical pipeline:
    1. Build analytical context
    2. Detect drift patterns
    3. Analyze inactivity
    4. Compute risk scores
    5. Generate structured assessments
    """
    
    def __init__(self):
        """Initialize the technical product engine with required components."""
        self.drift_detector = DriftDetector()
        self.inactivity_analyzer = InactivityAnalyzer()
        self.risk_scorer = RiskScorer()
        
        logger.info("Technical Product Engine initialized")
    
    def analyze_relationship(
        self,
        context: ClientProductContext,
        peer_cycle: Optional[float] = None,
        peer_metrics: Optional[Any] = None
    ) -> TechnicalRiskAssessment:
        """Analyze a single client-product relationship.
        
        This is the core analytical method that orchestrates all detection
        and scoring components to produce a comprehensive risk assessment.
        
        Args:
            context: Client-product analytical context
            peer_cycle: Optional peer-level expected cycle for comparison
            peer_metrics: Optional peer metrics for drift detection
            
        Returns:
            Complete technical risk assessment
        """
        # Step 1: Detect drift patterns
        drift_signals = self.drift_detector.detect(context, peer_metrics=peer_metrics)
        
        # Step 2: Analyze inactivity
        inactivity_signal = build_inactivity_signal(context, peer_cycle=peer_cycle)
        
        # Step 3: Extract potential gap for business priority
        potential_gap = 0.0
        if context.potential is not None:
            potential_gap = max(0.0, context.potential.potential_gap)
        
        # Step 4: Compute risk assessment
        risk_assessment = self.risk_scorer.compute_from_signals(
            drift_signals=drift_signals,
            inactivity_score=inactivity_signal.inactivity_score,
            potential_gap=potential_gap,
        )
        
        # Step 5: Build structured output
        return TechnicalRiskAssessment(
            client_id=context.client_id,
            product_id=context.product_id,
            risk_score=risk_assessment.risk_score,
            priority_score=risk_assessment.priority_score,
            risk_level=risk_assessment.risk_level,
            priority_level=risk_assessment.priority_level,
            inactivity_score=inactivity_signal.inactivity_score,
            inactivity_ratio=inactivity_signal.inactivity_ratio,
            expected_cycle_days=inactivity_signal.expected_cycle_days,
            days_since_last_order=inactivity_signal.days_since_last_order,
            is_inactive=inactivity_signal.is_inactive,
            volume_drift_score=risk_assessment.volume_drift_score,
            interval_drift_score=risk_assessment.interval_drift_score,
            peer_drift_score=risk_assessment.peer_drift_score,
            potential_gap=potential_gap,
            drift_signal_count=len(drift_signals),
        )
    
    def analyze_batch(
        self,
        contexts: List[ClientProductContext],
        peer_cycles: Optional[dict[tuple[str, str], float]] = None,
        peer_metrics_map: Optional[dict[str, Any]] = None
    ) -> List[TechnicalRiskAssessment]:
        """Analyze multiple client-product relationships in batch.
        
        Efficiently processes multiple contexts and returns structured
        assessments for all relationships.
        
        Args:
            contexts: List of client-product analytical contexts
            peer_cycles: Optional mapping of (client_id, product_id) to peer cycles
            peer_metrics_map: Optional mapping of product_id to peer metrics
            
        Returns:
            List of technical risk assessments
        """
        logger.info(f"Starting batch analysis of {len(contexts)} relationships")
        
        assessments = []
        for i, context in enumerate(contexts):
            if (i + 1) % 100 == 0:
                logger.info(f"Processed {i + 1}/{len(contexts)} relationships")
            
            # Get peer cycle if available
            peer_cycle = None
            if peer_cycles is not None:
                key = (context.client_id, context.product_id)
                peer_cycle = peer_cycles.get(key)
            
            # Get peer metrics for this product
            peer_metrics = None
            if peer_metrics_map is not None:
                peer_metrics = peer_metrics_map.get(context.product_id)
            
            # Analyze relationship
            try:
                assessment = self.analyze_relationship(
                    context, 
                    peer_cycle=peer_cycle,
                    peer_metrics=peer_metrics
                )
                assessments.append(assessment)
            except Exception as e:
                logger.error(
                    f"Error analyzing {context.client_id}-{context.product_id}: {e}",
                    exc_info=True
                )
                continue
        
        logger.info(f"Batch analysis complete: {len(assessments)} assessments generated")
        return assessments
    
    def get_high_risk_relationships(
        self,
        assessments: List[TechnicalRiskAssessment],
        min_risk_level: str = "medium"
    ) -> List[TechnicalRiskAssessment]:
        """Filter assessments to high-risk relationships.
        
        Args:
            assessments: List of technical risk assessments
            min_risk_level: Minimum risk level to include
            
        Returns:
            Filtered list of high-risk assessments
        """
        risk_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_level = risk_order.get(min_risk_level, 1)
        
        return [
            a for a in assessments
            if risk_order.get(a.risk_level, 0) >= min_level
        ]
    
    def get_summary_statistics(
        self,
        assessments: List[TechnicalRiskAssessment]
    ) -> dict:
        """Compute summary statistics for a set of assessments.
        
        Args:
            assessments: List of technical risk assessments
            
        Returns:
            Dictionary with summary statistics
        """
        if not assessments:
            return {
                "total_relationships": 0,
                "avg_risk_score": 0.0,
                "avg_priority_score": 0.0,
                "risk_level_counts": {},
                "inactive_count": 0,
                "avg_drift_signals": 0.0,
            }
        
        # Count risk levels
        risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for a in assessments:
            risk_counts[a.risk_level] = risk_counts.get(a.risk_level, 0) + 1
        
        # Count inactive relationships
        inactive_count = sum(1 for a in assessments if a.is_inactive)
        
        # Compute averages
        avg_risk = sum(a.risk_score for a in assessments) / len(assessments)
        avg_priority = sum(a.priority_score for a in assessments) / len(assessments)
        avg_signals = sum(a.drift_signal_count for a in assessments) / len(assessments)
        
        return {
            "total_relationships": len(assessments),
            "avg_risk_score": avg_risk,
            "avg_priority_score": avg_priority,
            "risk_level_counts": risk_counts,
            "inactive_count": inactive_count,
            "inactive_percentage": (inactive_count / len(assessments)) * 100,
            "avg_drift_signals": avg_signals,
        }
