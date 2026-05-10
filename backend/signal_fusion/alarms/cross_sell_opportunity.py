from __future__ import annotations

from ..domain.scoring import clamp, safe_float, safe_str
from ..domain.structures import AlertCategory, AlertType, FusionTables, ProductBlock
from .base import AlarmContext, build_alert
from .helpers import is_missing


class CrossSellOpportunityAlarm:
    alert_type = AlertType.CROSS_SELL_OPPORTUNITY

    def generate(self, tables: FusionTables, context: AlarmContext) -> list:
        if is_missing(tables.potential):
            return []
        df = tables.potential.copy()
        alerts = []
        for _, row in df.iterrows():
            potential_gap = safe_float(row.get("potential_gap"))
            if potential_gap <= 0:
                continue
            potential_h = max(safe_float(row.get("potential_h")), 1.0)
            capture_ratio = safe_float(row.get("capture_ratio"), 1.0)
            white_space = clamp(1.0 - capture_ratio)
            capacity = clamp(potential_gap / potential_h)
            score = (0.55 * capacity) + (0.45 * white_space)
            if score < 0.35:
                continue
            family = safe_str(row.get("family"), row.get("product_category"))
            product_ref = safe_str(row.get("product_category"), family)
            alerts.append(
                build_alert(
                    context=context,
                    client_id=row.get("client_id"),
                    product_id=product_ref,
                    fallback_family=family,
                    product_block=ProductBlock.COMMODITY,
                    alert_type=self.alert_type,
                    category=AlertCategory.OPPORTUNITY,
                    reason="Detected available wallet share in a related product family.",
                    recommended_action="Prepare a complementary offer linked to the client's observed consumption profile.",
                    confidence=0.60,
                    impact_score=clamp(potential_gap / 15000.0),
                    urgency_score=score,
                    explainability_score=0.75,
                    expected_revenue=potential_gap,
                    source_engines=("feature_engineering", "commodity_ai_engine"),
                    explanation=(
                        f"Potential gap is {potential_gap:.2f}.",
                        f"Capture ratio is {capture_ratio:.2f}.",
                    ),
                    evidence={
                        "potential_h": potential_h,
                        "potential_gap": potential_gap,
                        "capture_ratio": capture_ratio,
                        "cross_sell_score": score,
                    },
                )
            )
        return alerts
