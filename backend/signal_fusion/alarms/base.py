from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from ..domain.catalog import Catalog
from ..domain.scoring import clamp, safe_str, score_to_priority, score_to_urgency
from ..domain.structures import (
    Alert,
    AlertCategory,
    AlertType,
    FusionTables,
    ProductBlock,
)
from ..services.prioritizer import final_alert_score
from ..services.routing import RoutingService


@dataclass(frozen=True)
class AlarmContext:
    catalog: Catalog
    router: RoutingService
    created_at: datetime


class AlarmGenerator(Protocol):
    alert_type: AlertType

    def generate(self, tables: FusionTables, context: AlarmContext) -> list[Alert]:
        ...


def build_alert(
    *,
    context: AlarmContext,
    client_id: object,
    product_id: object,
    alert_type: AlertType,
    category: AlertCategory,
    reason: str,
    recommended_action: str,
    confidence: float,
    impact_score: float,
    urgency_score: float,
    explainability_score: float,
    expected_revenue: float,
    source_engines: tuple[str, ...],
    explanation: tuple[str, ...],
    evidence: dict,
    fallback_family: object = "",
    product_block: ProductBlock | None = None,
) -> Alert:
    product = context.catalog.product(product_id, fallback_family)
    client_key = safe_str(client_id, "unknown_client")
    product_key = safe_str(product_id, product.product_id)
    block = product_block or product.block
    priority_score = final_alert_score(
        impact_score=impact_score,
        urgency_score=urgency_score,
        confidence=confidence,
        explainability_score=explainability_score,
    )
    priority_level = score_to_priority(priority_score)
    urgency = score_to_urgency(urgency_score)
    actor_id = context.router.select_actor(
        alert_type=alert_type,
        category=category,
        product_block=block,
        priority_level=priority_level,
        expected_revenue=expected_revenue,
        confidence=confidence,
    )
    deadline_hours = context.router.deadline_hours(actor_id, urgency)
    return Alert(
        alert_id=_alert_id(alert_type, client_key, product_key, context.created_at),
        client_id=client_key,
        product_id=product_key,
        product_family=product.family,
        product_category=product.category,
        product_block=block,
        alert_type=alert_type,
        category=category,
        priority_score=priority_score,
        priority_level=priority_level,
        urgency=urgency,
        confidence=clamp(confidence),
        impact_score=clamp(impact_score),
        urgency_score=clamp(urgency_score),
        explainability_score=clamp(explainability_score),
        expected_revenue=max(float(expected_revenue), 0.0),
        recommended_action=recommended_action,
        reason=reason,
        actor_id=actor_id,
        action_deadline_hours=deadline_hours,
        due_at=context.router.due_at(context.created_at, deadline_hours),
        source_engines=source_engines,
        explanation=explanation,
        evidence=evidence,
        created_at=context.created_at,
    )


def _alert_id(
    alert_type: AlertType,
    client_id: str,
    product_id: str,
    created_at: datetime,
) -> str:
    raw = f"{created_at.date()}|{alert_type.value}|{client_id}|{product_id}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"AL-{digest}"
