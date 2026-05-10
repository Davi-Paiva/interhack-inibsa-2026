"""Domain types for delegate feedback and lightweight policy outputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class DelegateFeedbackRecord:
    """Structured feedback captured after a delegate resolves an alert."""

    feedback_id: str
    global_alert_id: str
    source_engine: str
    canonical_variant: str
    customer_id: str
    product_id: str
    delegate_id: str
    resolution_status: str
    alert_validity: str
    action_taken: str
    business_outcome: str
    root_cause: str
    free_note: str
    resolved_at: datetime
    created_at: datetime
    global_priority_score: float
    global_priority_band: str
    recommended_action: str
    alert_reason_summary: str = ""

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "global_alert_id": self.global_alert_id,
            "source_engine": self.source_engine,
            "canonical_variant": self.canonical_variant,
            "customer_id": self.customer_id,
            "product_id": self.product_id,
            "delegate_id": self.delegate_id,
            "resolution_status": self.resolution_status,
            "alert_validity": self.alert_validity,
            "action_taken": self.action_taken,
            "business_outcome": self.business_outcome,
            "root_cause": self.root_cause,
            "free_note": self.free_note,
            "resolved_at": self.resolved_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "global_priority_score": float(self.global_priority_score),
            "global_priority_band": self.global_priority_band,
            "recommended_action": self.recommended_action,
            "alert_reason_summary": self.alert_reason_summary,
        }
