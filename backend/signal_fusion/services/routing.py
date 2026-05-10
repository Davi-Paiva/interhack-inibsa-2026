from __future__ import annotations

from datetime import datetime, timedelta

from ..domain.structures import (
    ACTIVATION_ACTORS,
    AlertCategory,
    AlertType,
    ProductBlock,
    PriorityLevel,
    UrgencyLevel,
)


class RoutingService:
    def select_actor(
        self,
        *,
        alert_type: AlertType,
        category: AlertCategory,
        product_block: ProductBlock,
        priority_level: PriorityLevel,
        expected_revenue: float,
        confidence: float,
    ) -> str:
        if confidence < 0.35 and category == AlertCategory.OPPORTUNITY:
            return "marketing_automation"
        if product_block == ProductBlock.TECHNICAL:
            return "delegado"
        if category in {AlertCategory.RISK, AlertCategory.EXECUTIVE}:
            return "delegado" if priority_level != PriorityLevel.MEDIUM else "televenta"
        if alert_type == AlertType.DEMAND_LEAKAGE and priority_level in {
            PriorityLevel.HIGH,
            PriorityLevel.CRITICAL,
        }:
            return "delegado" if expected_revenue >= 5000 else "televenta"
        if priority_level == PriorityLevel.CRITICAL or expected_revenue >= 15000:
            return "delegado"
        if priority_level == PriorityLevel.LOW:
            return "marketing_automation"
        return "televenta"

    def deadline_hours(self, actor_id: str, urgency: UrgencyLevel) -> int:
        base = ACTIVATION_ACTORS[actor_id].default_sla_hours
        urgency_hours = {
            UrgencyLevel.CRITICAL: 24,
            UrgencyLevel.HIGH: 48,
            UrgencyLevel.MEDIUM: 72,
            UrgencyLevel.LOW: base,
        }[urgency]
        return min(base, urgency_hours)

    def due_at(self, created_at: datetime, hours: int) -> datetime:
        return created_at + timedelta(hours=hours)
