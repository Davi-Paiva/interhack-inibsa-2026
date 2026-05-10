from __future__ import annotations

from ..domain.scoring import clamp, safe_float
from ..domain.structures import AlertCategory, AlertType, FusionTables
from .base import AlarmContext, build_alert
from .helpers import is_missing


class ProductMixDriftAlarm:
    alert_type = AlertType.PRODUCT_MIX_DRIFT

    def generate(self, tables: FusionTables, context: AlarmContext) -> list:
        if is_missing(tables.technical_risk):
            return []
        alerts = []
        for _, row in tables.technical_risk.iterrows():
            drift = max(
                safe_float(row.get("volume_drift_score")),
                safe_float(row.get("interval_drift_score")),
                safe_float(row.get("peer_drift_score")),
            )
            if drift < 0.35:
                continue
            expected_revenue = max(safe_float(row.get("potential_gap")), 0.0)
            alerts.append(
                build_alert(
                    context=context,
                    client_id=row.get("client_id"),
                    product_id=row.get("product_id"),
                    alert_type=self.alert_type,
                    category=AlertCategory.ANOMALY,
                    reason="Product behavior drifted versus historical and peer pattern.",
                    recommended_action="Ask the account owner to validate whether the product mix changed or moved to another supplier.",
                    confidence=0.70,
                    impact_score=clamp(max(expected_revenue, drift * 8000.0) / 18000.0),
                    urgency_score=drift,
                    explainability_score=0.82,
                    expected_revenue=expected_revenue,
                    source_engines=("technical_product_engine",),
                    explanation=(
                        f"Highest drift score is {drift:.2f}.",
                        f"Volume drift is {safe_float(row.get('volume_drift_score')):.2f}.",
                        f"Interval drift is {safe_float(row.get('interval_drift_score')):.2f}.",
                    ),
                    evidence={
                        "volume_drift_score": safe_float(row.get("volume_drift_score")),
                        "interval_drift_score": safe_float(row.get("interval_drift_score")),
                        "peer_drift_score": safe_float(row.get("peer_drift_score")),
                    },
                )
            )
        return alerts
