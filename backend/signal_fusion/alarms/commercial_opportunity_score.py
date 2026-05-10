from __future__ import annotations

from ..domain.scoring import clamp, safe_float
from ..domain.structures import AlertCategory, AlertType, FusionTables
from .base import AlarmContext, build_alert
from .helpers import is_missing


class CommercialOpportunityScoreAlarm:
    alert_type = AlertType.COMMERCIAL_OPPORTUNITY_SCORE

    def generate(self, tables: FusionTables, context: AlarmContext) -> list:
        if is_missing(tables.capture_opportunities):
            return []
        df = tables.capture_opportunities.copy()
        if not is_missing(tables.next_purchase):
            df = df.merge(
                tables.next_purchase[
                    ["customer_id", "product_id", "purchase_probability", "days_until_expected_purchase"]
                ],
                how="left",
                on=["customer_id", "product_id"],
                validate="one_to_one",
            )
        alerts = []
        for _, row in df.iterrows():
            capture_score = safe_float(row.get("capture_score"))
            band = str(row.get("priority_band", "low"))
            if capture_score < 24 and band == "low":
                continue
            purchase_probability = safe_float(row.get("purchase_probability"), capture_score / 100.0)
            revenue_potential = clamp(safe_float(row.get("value_component")))
            urgency = clamp(safe_float(row.get("urgency_component")))
            leakage = clamp(safe_float(row.get("leakage_component")))
            expansion = clamp(safe_float(row.get("gap_units")) / 15000.0)
            priority_0_1 = (
                0.30 * purchase_probability
                + 0.25 * revenue_potential
                + 0.20 * urgency
                + 0.15 * leakage
                + 0.10 * expansion
            )
            expected_revenue = max(safe_float(row.get("gap_units")), 0.0)
            alerts.append(
                build_alert(
                    context=context,
                    client_id=row.get("customer_id"),
                    product_id=row.get("product_id"),
                    alert_type=self.alert_type,
                    category=AlertCategory.PRIORITIZATION,
                    reason="This account is high enough in the commercial queue to be actioned.",
                    recommended_action=str(row.get("recommended_action", "Prioritize this account in the next sales queue.")),
                    confidence=clamp(safe_float(row.get("confidence_component"), 0.6)),
                    impact_score=max(revenue_potential, expansion),
                    urgency_score=max(urgency, priority_0_1),
                    explainability_score=0.88,
                    expected_revenue=expected_revenue,
                    source_engines=("commodity_ai_engine", "signal_fusion"),
                    explanation=(
                        f"Commercial opportunity score is {capture_score:.1f}.",
                        f"Priority band is {band}.",
                        f"Leakage component is {leakage:.2f}.",
                    ),
                    evidence={
                        "capture_score": capture_score,
                        "priority_band": band,
                        "purchase_probability": purchase_probability,
                        "priority_formula_score": priority_0_1,
                    },
                )
            )
        return alerts
