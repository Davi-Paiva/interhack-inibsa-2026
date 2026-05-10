"""Domain types for the global prioritization output."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True)
class GlobalAlertRecord:
    """Single operational alert in the globally prioritized queue."""

    global_alert_id: str
    source_engine: str
    canonical_variant: str
    source_variants: list[str]
    customer_id: str
    product_id: str
    severity_label: str | None
    priority_label: str | None
    global_priority_score: float
    global_priority_band: str
    process_on_date: date
    process_day_bucket: str
    queue_rank: int
    recommended_action: str
    feedback_adjusted_priority: str | None = None
    delegate_hint: str = ""
    last_delegate_outcome: str | None = None
    repeat_alert_count_30d: int = 0
    suppression_until: date | None = None
    alert_reason_summary: str = ""
    explanation_ids: list[str] = field(default_factory=list)
    source_row_keys: list[str] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "global_alert_id": self.global_alert_id,
            "source_engine": self.source_engine,
            "canonical_variant": self.canonical_variant,
            "source_variants": list(self.source_variants),
            "customer_id": self.customer_id,
            "product_id": self.product_id,
            "severity_label": self.severity_label,
            "priority_label": self.priority_label,
            "global_priority_score": float(self.global_priority_score),
            "global_priority_band": self.global_priority_band,
            "process_on_date": self.process_on_date.isoformat(),
            "process_day_bucket": self.process_day_bucket,
            "queue_rank": int(self.queue_rank),
            "recommended_action": self.recommended_action,
            "feedback_adjusted_priority": self.feedback_adjusted_priority,
            "delegate_hint": self.delegate_hint,
            "last_delegate_outcome": self.last_delegate_outcome,
            "repeat_alert_count_30d": int(self.repeat_alert_count_30d),
            "suppression_until": self.suppression_until.isoformat() if self.suppression_until else None,
            "alert_reason_summary": self.alert_reason_summary,
            "explanation_ids": list(self.explanation_ids),
            "source_row_keys": list(self.source_row_keys),
        }
