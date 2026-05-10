from __future__ import annotations

from ..domain.scoring import clamp, safe_float
from ..domain.structures import AlertCategory, AlertType, FusionTables
from .base import AlarmContext, build_alert
from .helpers import is_missing, numeric


class DemandSpikeOpportunityAlarm:
    alert_type = AlertType.DEMAND_SPIKE_OPPORTUNITY

    def generate(self, tables: FusionTables, context: AlarmContext) -> list:
        if is_missing(tables.client_product_features):
            return []
        df = tables.client_product_features.copy()
        df["spike_score"] = numeric(df, "sales_growth_30d")
        df["rolling_sales_30d"] = numeric(df, "rolling_sales_30d")
        candidates = df.loc[df["spike_score"].gt(0.15)].copy()
        alerts = []
        for _, row in candidates.iterrows():
            spike = safe_float(row.get("spike_score"))
            rolling = safe_float(row.get("rolling_sales_30d"))
            expected_revenue = max(rolling * spike, 0.0)
            alerts.append(
                build_alert(
                    context=context,
                    client_id=row.get("client_id"),
                    product_id=row.get("product_id"),
                    alert_type=self.alert_type,
                    category=AlertCategory.OPPORTUNITY,
                    reason="Consumption accelerated above the normal growth threshold.",
                    recommended_action="Review stock allocation and propose a proactive replenishment or upsell action.",
                    confidence=0.70,
                    impact_score=clamp(expected_revenue / 20000.0),
                    urgency_score=clamp(spike / 0.60),
                    explainability_score=0.80,
                    expected_revenue=expected_revenue,
                    source_engines=("feature_engineering",),
                    explanation=(
                        f"30-day growth is {spike:.0%}.",
                        f"Current 30-day sales are {rolling:.2f}.",
                    ),
                    evidence={
                        "sales_growth_30d": spike,
                        "rolling_sales_30d": rolling,
                    },
                )
            )
        return alerts
