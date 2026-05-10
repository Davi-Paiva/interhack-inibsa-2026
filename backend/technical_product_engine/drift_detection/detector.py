"""
Main drift detection orchestrator.

This module coordinates various drift detection mechanisms
to identify changes in customer behavior and patterns.
"""
from __future__ import annotations

from typing import List, Optional

from ..domain.models import ClientProductContext
from ..domain.signals import DriftSignal
from .interval_drift import detect_interval_drift
from .volume_drift import detect_volume_drift
from .peer_drift import detect_peer_drift, PeerMetrics


class DriftDetector:
    """Central orchestrator for drift detection.
    
    Coordinates multiple specialized drift detectors to provide
    a comprehensive analysis of customer-product relationship health.
    """
    
    def detect(
        self,
        context: ClientProductContext,
        peer_metrics: Optional[PeerMetrics] = None
    ) -> List[DriftSignal]:
        """Detect all types of drift for a customer-product relationship.
        
        Invokes specialized detectors and aggregates their signals into
        a unified result set.
        
        Args:
            context: Client-product analytical context with precomputed features
            peer_metrics: Optional peer comparison metrics for peer drift detection
            
        Returns:
            Aggregated list of all detected drift signals
        """
        signals: List[DriftSignal] = []
        
        # Detect interval-based drift (inactivity)
        interval_signals = detect_interval_drift(context)
        signals.extend(interval_signals)
        
        # Detect volume-based drift (sales decline)
        volume_signals = detect_volume_drift(context)
        signals.extend(volume_signals)
        
        # Detect peer-based drift (divergence from market)
        peer_signals = detect_peer_drift(context, peer_metrics)
        signals.extend(peer_signals)
        
        return signals
    
    def detect_batch(
        self,
        contexts: List[ClientProductContext],
        peer_metrics_map: Optional[dict[tuple[str, str], PeerMetrics]] = None
    ) -> dict[tuple[str, str], List[DriftSignal]]:
        """Detect drift for multiple customer-product relationships.
        
        Efficiently processes a batch of contexts and returns results
        indexed by (client_id, product_id) tuples.
        
        Args:
            contexts: List of client-product analytical contexts
            peer_metrics_map: Optional mapping of (client_id, product_id) to peer metrics
            
        Returns:
            Dictionary mapping (client_id, product_id) to detected signals
        """
        results: dict[tuple[str, str], List[DriftSignal]] = {}
        
        for context in contexts:
            key = (context.client_id, context.product_id)
            
            # Get peer metrics if available
            peer_metrics = None
            if peer_metrics_map is not None:
                peer_metrics = peer_metrics_map.get(key)
            
            # Detect drift
            signals = self.detect(context, peer_metrics)
            results[key] = signals
        
        return results
