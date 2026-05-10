from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd


class ProductBlock(str, Enum):
    COMMODITY = "commodity"
    TECHNICAL = "technical"
    UNKNOWN = "unknown"


class AlertCategory(str, Enum):
    OPPORTUNITY = "opportunity"
    RISK = "risk"
    ANOMALY = "anomaly"
    PRIORITIZATION = "prioritization"
    EXECUTIVE = "executive"


class AlertType(str, Enum):
    HIGH_PURCHASE_PROBABILITY = "high_purchase_probability"
    DEMAND_SPIKE_OPPORTUNITY = "demand_spike_opportunity"
    CROSS_SELL_OPPORTUNITY = "cross_sell_opportunity"
    CHURN_RISK = "churn_risk"
    DEMAND_LEAKAGE = "demand_leakage"
    PURCHASE_ANOMALY = "purchase_anomaly"
    PRODUCT_MIX_DRIFT = "product_mix_drift"
    COMMERCIAL_OPPORTUNITY_SCORE = "commercial_opportunity_score"
    ACCOUNT_DETERIORATION = "account_deterioration"
    EMERGING_STRATEGIC_ACCOUNT = "emerging_strategic_account"


class PriorityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UrgencyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActivationChannel(str, Enum):
    FIELD_SALES = "field_sales"
    TELESALES = "telesales"
    MARKETING_AUTOMATION = "marketing_automation"


@dataclass(frozen=True)
class AlertActor:
    actor_id: str
    display_name: str
    channel: ActivationChannel
    default_sla_hours: int
    handles: tuple[AlertCategory, ...]
    description: str


ACTIVATION_ACTORS: dict[str, AlertActor] = {
    "delegado": AlertActor(
        actor_id="delegado",
        display_name="Delegado comercial",
        channel=ActivationChannel.FIELD_SALES,
        default_sla_hours=48,
        handles=(
            AlertCategory.RISK,
            AlertCategory.PRIORITIZATION,
            AlertCategory.EXECUTIVE,
        ),
        description="Owner for high-value accounts, technical products and field intervention.",
    ),
    "televenta": AlertActor(
        actor_id="televenta",
        display_name="Televenta",
        channel=ActivationChannel.TELESALES,
        default_sla_hours=72,
        handles=(
            AlertCategory.OPPORTUNITY,
            AlertCategory.RISK,
            AlertCategory.ANOMALY,
        ),
        description="Remote sales queue for commodity capture and medium-priority actions.",
    ),
    "marketing_automation": AlertActor(
        actor_id="marketing_automation",
        display_name="Marketing automation",
        channel=ActivationChannel.MARKETING_AUTOMATION,
        default_sla_hours=168,
        handles=(AlertCategory.OPPORTUNITY,),
        description="Automated nurture or CRM-ready activation, for example HubSpot.",
    ),
}


@dataclass(frozen=True)
class Alert:
    alert_id: str
    client_id: str
    product_id: str
    product_family: str
    product_category: str
    product_block: ProductBlock
    alert_type: AlertType
    category: AlertCategory
    priority_score: float
    priority_level: PriorityLevel
    urgency: UrgencyLevel
    confidence: float
    impact_score: float
    urgency_score: float
    explainability_score: float
    expected_revenue: float
    recommended_action: str
    reason: str
    actor_id: str
    action_deadline_hours: int
    source_engines: tuple[str, ...]
    explanation: tuple[str, ...] = field(default_factory=tuple)
    evidence: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    due_at: datetime | None = None
    suppressed: bool = False
    suppression_reason: str = ""

    @property
    def dedupe_key(self) -> tuple[str, str, AlertType]:
        return (self.client_id, self.product_id, self.alert_type)


@dataclass
class FusionTables:
    clients: "pd.DataFrame | None" = None
    products: "pd.DataFrame | None" = None
    potential: "pd.DataFrame | None" = None
    client_product_features: "pd.DataFrame | None" = None
    commodity_forecast: "pd.DataFrame | None" = None
    demand_leakage: "pd.DataFrame | None" = None
    capture_opportunities: "pd.DataFrame | None" = None
    next_purchase: "pd.DataFrame | None" = None
    technical_risk: "pd.DataFrame | None" = None
