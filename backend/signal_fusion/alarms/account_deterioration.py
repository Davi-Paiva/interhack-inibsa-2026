from __future__ import annotations

from ..domain.scoring import clamp, safe_float
from ..domain.structures import AlertCategory, AlertType, FusionTables
from .base import AlarmContext, build_alert
from .helpers import is_missing, normalize_customer_column


class AccountDeteriorationAlarm:
    alert_type = AlertType.ACCOUNT_DETERIORATION

    def generate(self, tables: FusionTables, context: AlarmContext) -> list:
        if is_missing(tables.technical_risk):
            return []
        df = tables.technical_risk.copy()
        if not is_missing(tables.client_product_features):
            features = normalize_customer_column(tables.client_product_features)
            df = df.merge(
                features[["customer_id", "product_id", "sales_growth_30d"]],
                how="left",
                left_on=["client_id", "product_id"],
                right_on=["customer_id", "product_id"],
            )
        alerts = []
        for _, row in df.iterrows():
            risk = safe_float(row.get("risk_score"))
            inactivity = safe_float(row.get("inactivity_score"))
            drift = max(
                safe_float(row.get("volume_drift_score")),
                safe_float(row.get("interval_drift_score")),
                safe_float(row.get("peer_drift_score")),
            )
            negative_growth = max(-safe_float(row.get("sales_growth_30d")), 0.0)
            score = (0.35 * risk) + (0.25 * inactivity) + (0.20 * drift) + (0.20 * clamp(negative_growth))
            if score < 0.50:
                continue
            expected_revenue = max(safe_float(row.get("potential_gap")), 0.0)
            alerts.append(
                build_alert(
                    context=context,
                    client_id=row.get("client_id"),
                    product_id=row.get("product_id"),
                    alert_type=self.alert_type,
                    category=AlertCategory.EXECUTIVE,
                    reason="Account quality is deteriorating across risk, inactivity or drift signals.",
                    recommended_action="Escalate to the account owner and register the recovery outcome after contact.",
                    confidence=0.72,
                    impact_score=clamp(max(expected_revenue, score * 10000.0) / 20000.0),
                    urgency_score=score,
                    explainability_score=0.86,
                    expected_revenue=expected_revenue,
                    source_engines=("technical_product_engine", "signal_fusion"),
                    explanation=(
                        f"Deterioration score is {score:.2f}.",
                        f"Risk score is {risk:.2f}.",
                        f"Negative growth component is {negative_growth:.2f}.",
                    ),
                    evidence={
                        "risk_score": risk,
                        "inactivity_score": inactivity,
                        "drift_score": drift,
                        "negative_growth": negative_growth,
                    },
                )
            )
        return alerts
