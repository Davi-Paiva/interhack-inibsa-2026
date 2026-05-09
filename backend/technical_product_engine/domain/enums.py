"""
Enumerations for the technical product engine.

This module contains enum definitions for various categorical
values used throughout the system.
"""
from enum import Enum


class SignalType(Enum):
    """Types of drift signals that can be detected in customer-product behavior."""
    
    INTERVAL_DRIFT = "interval_drift"
    VOLUME_DRIFT = "volume_drift"
    PEER_DRIFT = "peer_drift"
