"""Domain types for the explainability engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ContributingFactor:
    """Normalized explanatory factor attached to an explained signal."""

    name: str
    kind: str
    direction: str
    raw_value: Any
    display_value: str
    threshold: Any = None
    weight: float | None = None
    importance_rank: int = 0
    explanation_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "direction": self.direction,
            "raw_value": self.raw_value,
            "display_value": self.display_value,
            "threshold": self.threshold,
            "weight": self.weight,
            "importance_rank": self.importance_rank,
            "explanation_text": self.explanation_text,
        }


@dataclass(frozen=True)
class ExplanationRecord:
    """Persisted explanation for a single existing alert variant."""

    explanation_id: str
    source_engine: str
    alert_variant: str
    entity_id: str
    customer_id: str
    product_id: str
    severity_label: str | None
    priority_label: str | None
    headline: str
    summary_text: str
    why_triggered_text: str
    confidence_text: str
    temporal_summary_text: str
    contributing_factors: list[ContributingFactor] = field(default_factory=list)
    supporting_metrics: dict[str, Any] = field(default_factory=dict)
    decision_trace: list[str] = field(default_factory=list)
    source_artifact: str = ""
    source_row_key: str = ""

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "explanation_id": self.explanation_id,
            "source_engine": self.source_engine,
            "alert_variant": self.alert_variant,
            "entity_id": self.entity_id,
            "customer_id": self.customer_id,
            "product_id": self.product_id,
            "severity_label": self.severity_label,
            "priority_label": self.priority_label,
            "headline": self.headline,
            "summary_text": self.summary_text,
            "why_triggered_text": self.why_triggered_text,
            "confidence_text": self.confidence_text,
            "temporal_summary_text": self.temporal_summary_text,
            "contributing_factors": [factor.to_dict() for factor in self.contributing_factors],
            "supporting_metrics": self.supporting_metrics,
            "decision_trace": self.decision_trace,
            "source_artifact": self.source_artifact,
            "source_row_key": self.source_row_key,
        }
