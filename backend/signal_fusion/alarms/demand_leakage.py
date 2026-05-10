from __future__ import annotations

from ..domain.scoring import clamp, safe_float
from ..domain.structures import AlertCategory, AlertType, FusionTables
from .base import AlarmContext, build_alert
from .helpers import is_missing


class DemandLeakageAlarm:
    alert_type = AlertType.DEMAND_LEAKAGE

    def generate(self, tables: FusionTables, context: AlarmContext) -> list:
        if is_missing(tables.demand_leakage):
            return []
        df = tables.demand_leakage.copy()
        alerts = []
        for _, row in df.iterrows():
            gap_ratio = safe_float(row.get("gap_ratio"))
            leakage_score = safe_float(row.get("leakage_score"))
            if gap_ratio < 0.15 and leakage_score < 0.15:
                continue
            gap_units = max(safe_float(row.get("gap_units")), 0.0)
            route = str(row.get("route_to_engine", ""))
            action = (
                "Launch competitor recovery campaign and confirm the next purchase window."
                if route == "commodity_ai_engine"
                else "Validate account status before commercial recovery action."
            )
            alerts.append(
                build_alert(
                    context=context,
                    client_id=row.get("customer_id"),
                    product_id=row.get("product_id"),
                    alert_type=self.alert_type,
                    category=AlertCategory.RISK,
                    reason="Observed demand is below expected demand for this client-product pair.",
                    recommended_action=action,
                    confidence=clamp(safe_float(row.get("confidence_factor"), 0.5)),
                    impact_score=clamp(gap_units / 15000.0),
                    urgency_score=max(gap_ratio, leakage_score),
                    explainability_score=0.90,
                    expected_revenue=gap_units,
                    source_engines=("commodity_ai_engine",),
                    explanation=(
                        f"Expected demand exceeds observed demand by {gap_units:.2f}.",
                        f"Gap ratio is {gap_ratio:.0%}.",
                        f"Routing reason: {row.get('routing_reason', '')}.",
                    ),
                    evidence={
                        "predicted_30d_sales": safe_float(row.get("predicted_30d_sales")),
                        "observed_30d_sales": safe_float(row.get("observed_30d_sales")),
                        "gap_ratio": gap_ratio,
                        "leakage_score": leakage_score,
                        "route_to_engine": route,
                    },
                )
            )
        return alerts
