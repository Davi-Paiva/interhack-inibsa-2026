from __future__ import annotations

from ..domain.scoring import clamp, safe_float
from ..domain.structures import AlertCategory, AlertType, FusionTables
from .base import AlarmContext, build_alert
from .helpers import is_missing, numeric


class PurchaseAnomalyAlarm:
    alert_type = AlertType.PURCHASE_ANOMALY

    def generate(self, tables: FusionTables, context: AlarmContext) -> list:
        if is_missing(tables.client_product_features):
            return []
        df = tables.client_product_features.copy()
        growth = numeric(df, "sales_growth_30d").abs().clip(upper=1.0)
        stale = (numeric(df, "days_since_last_product_order") / 180.0).clip(upper=1.0)
        returns = (numeric(df, "client_product_return_rate") / 0.30).clip(upper=1.0)
        campaign = numeric(df, "campaign_lift_product").abs().clip(upper=1.0)
        df["anomaly_score"] = (
            0.35 * growth + 0.25 * stale + 0.25 * returns + 0.15 * campaign
        ).clip(0.0, 1.0)
        candidates = df.loc[df["anomaly_score"].ge(0.65)].copy()
        alerts = []
        for _, row in candidates.iterrows():
            score = safe_float(row.get("anomaly_score"))
            revenue = safe_float(row.get("client_product_total_revenue"))
            alerts.append(
                build_alert(
                    context=context,
                    client_id=row.get("client_id"),
                    product_id=row.get("product_id"),
                    alert_type=self.alert_type,
                    category=AlertCategory.ANOMALY,
                    reason="Current behavior is outside the expected purchase pattern.",
                    recommended_action="Review the order pattern before treating the signal as normal demand.",
                    confidence=0.62,
                    impact_score=clamp(revenue / 25000.0),
                    urgency_score=score,
                    explainability_score=0.78,
                    expected_revenue=revenue,
                    source_engines=("feature_engineering",),
                    explanation=(
                        f"Anomaly score is {score:.2f}.",
                        f"Absolute 30-day growth is {abs(safe_float(row.get('sales_growth_30d'))):.0%}.",
                        f"Return rate is {safe_float(row.get('client_product_return_rate')):.0%}.",
                    ),
                    evidence={
                        "anomaly_score": score,
                        "sales_growth_30d": safe_float(row.get("sales_growth_30d")),
                        "days_since_last_product_order": safe_float(
                            row.get("days_since_last_product_order")
                        ),
                        "campaign_lift_product": safe_float(row.get("campaign_lift_product")),
                    },
                )
            )
        return alerts
