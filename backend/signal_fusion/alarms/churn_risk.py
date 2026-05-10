from __future__ import annotations

from ..domain.scoring import clamp, safe_float
from ..domain.structures import AlertCategory, AlertType, FusionTables
from .base import AlarmContext, build_alert
from .helpers import is_missing


class ChurnRiskAlarm:
    alert_type = AlertType.CHURN_RISK

    def generate(self, tables: FusionTables, context: AlarmContext) -> list:
        if is_missing(tables.technical_risk):
            return []
        df = tables.technical_risk.copy()
        alerts = []
        for _, row in df.iterrows():
            risk = safe_float(row.get("risk_score"))
            if risk < 0.50:
                continue
            inactivity = safe_float(row.get("inactivity_score"))
            expected_revenue = max(safe_float(row.get("potential_gap")), 0.0)
            confidence = clamp(0.55 + 0.10 * safe_float(row.get("drift_signal_count")))
            alerts.append(
                build_alert(
                    context=context,
                    client_id=row.get("client_id"),
                    product_id=row.get("product_id"),
                    alert_type=self.alert_type,
                    category=AlertCategory.RISK,
                    reason="Technical-product relationship shows abandonment risk.",
                    recommended_action="Schedule a retention call and validate whether the product has moved to a competitor.",
                    confidence=confidence,
                    impact_score=clamp(max(expected_revenue, risk * 10000.0) / 20000.0),
                    urgency_score=max(risk, inactivity),
                    explainability_score=0.85,
                    expected_revenue=expected_revenue,
                    source_engines=("technical_product_engine",),
                    explanation=(
                        f"Churn risk score is {risk * 100:.1f}.",
                        f"Inactivity ratio is {safe_float(row.get('inactivity_ratio')):.2f}.",
                        f"Detected {int(safe_float(row.get('drift_signal_count')))} drift signals.",
                    ),
                    evidence={
                        "risk_score": risk,
                        "risk_level": str(row.get("risk_level", "")),
                        "inactivity_score": inactivity,
                        "days_since_last_order": safe_float(row.get("days_since_last_order")),
                    },
                )
            )
        return alerts
