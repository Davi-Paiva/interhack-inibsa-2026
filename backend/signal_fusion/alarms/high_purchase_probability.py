from __future__ import annotations

import pandas as pd

from ..domain.scoring import clamp, safe_float
from ..domain.structures import AlertCategory, AlertType, FusionTables
from .base import AlarmContext, build_alert
from .helpers import is_missing


class HighPurchaseProbabilityAlarm:
    alert_type = AlertType.HIGH_PURCHASE_PROBABILITY

    def generate(self, tables: FusionTables, context: AlarmContext) -> list:
        if is_missing(tables.next_purchase):
            return []
        df = tables.next_purchase.copy()
        if not is_missing(tables.commodity_forecast):
            df = df.merge(
                tables.commodity_forecast[
                    ["customer_id", "product_id", "predicted_30d_sales", "forecast_confidence"]
                ],
                how="left",
                on=["customer_id", "product_id"],
                validate="one_to_one",
            )
        df["purchase_probability"] = pd.to_numeric(
            df["purchase_probability"], errors="coerce"
        ).fillna(0.0)
        candidates = df.loc[df["purchase_probability"].ge(0.70)].copy()
        alerts = []
        for _, row in candidates.iterrows():
            probability = safe_float(row.get("purchase_probability"))
            days_until = safe_float(row.get("days_until_expected_purchase"), 30.0)
            expected_revenue = safe_float(row.get("predicted_30d_sales"))
            urgency_score = max(probability, clamp(1.0 - (days_until / 30.0)))
            confidence = max(probability, safe_float(row.get("forecast_confidence"), 0.5))
            alerts.append(
                build_alert(
                    context=context,
                    client_id=row.get("customer_id"),
                    product_id=row.get("product_id"),
                    alert_type=self.alert_type,
                    category=AlertCategory.OPPORTUNITY,
                    reason="High probability of purchase in the next contact window.",
                    recommended_action="Contact before the suggested purchase window and confirm replenishment needs.",
                    confidence=confidence,
                    impact_score=clamp(expected_revenue / 15000.0),
                    urgency_score=urgency_score,
                    explainability_score=0.85,
                    expected_revenue=expected_revenue,
                    source_engines=("commodity_ai_engine",),
                    explanation=(
                        f"Purchase probability is {probability:.2f}.",
                        f"Expected purchase is in {int(days_until)} days.",
                        str(row.get("contact_recommendation", "")),
                    ),
                    evidence={
                        "purchase_probability": probability,
                        "days_until_expected_purchase": days_until,
                        "contact_window_start": str(row.get("contact_window_start", "")),
                        "contact_window_end": str(row.get("contact_window_end", "")),
                    },
                )
            )
        return alerts
