from __future__ import annotations

import pandas as pd

from ..domain.scoring import clamp, safe_float
from ..domain.structures import AlertCategory, AlertType, FusionTables
from .base import AlarmContext, build_alert
from .helpers import is_missing, normalize_customer_column, numeric


class EmergingStrategicAccountAlarm:
    alert_type = AlertType.EMERGING_STRATEGIC_ACCOUNT

    def generate(self, tables: FusionTables, context: AlarmContext) -> list:
        if is_missing(tables.client_product_features):
            return []
        df = normalize_customer_column(tables.client_product_features).copy()
        if not is_missing(tables.clients):
            clients = normalize_customer_column(tables.clients)
            df = df.merge(
                clients[["customer_id", "customer_total_revenue", "customer_frequency"]],
                how="left",
                on="customer_id",
                validate="many_to_one",
            )
        growth = numeric(df, "sales_growth_30d").clip(lower=0.0, upper=1.0)
        revenue = _minmax(numeric(df, "customer_total_revenue"))
        frequency = _minmax(numeric(df, "customer_frequency"))
        df["strategic_growth_score"] = (0.45 * growth) + (0.35 * revenue) + (0.20 * frequency)
        candidates = df.loc[df["strategic_growth_score"].ge(0.55)].copy()
        alerts = []
        for _, row in candidates.iterrows():
            score = safe_float(row.get("strategic_growth_score"))
            revenue_value = safe_float(row.get("client_product_total_revenue"))
            alerts.append(
                build_alert(
                    context=context,
                    client_id=row.get("customer_id"),
                    product_id=row.get("product_id"),
                    alert_type=self.alert_type,
                    category=AlertCategory.EXECUTIVE,
                    reason="Client shows fast growth and enough value to be managed strategically.",
                    recommended_action="Review as a potential key account and define the next expansion step.",
                    confidence=0.68,
                    impact_score=max(clamp(revenue_value / 30000.0), score),
                    urgency_score=score,
                    explainability_score=0.80,
                    expected_revenue=revenue_value,
                    source_engines=("feature_engineering", "signal_fusion"),
                    explanation=(
                        f"Strategic growth score is {score:.2f}.",
                        f"30-day growth is {safe_float(row.get('sales_growth_30d')):.0%}.",
                        f"Client revenue is {safe_float(row.get('customer_total_revenue')):.2f}.",
                    ),
                    evidence={
                        "strategic_growth_score": score,
                        "sales_growth_30d": safe_float(row.get("sales_growth_30d")),
                        "customer_total_revenue": safe_float(row.get("customer_total_revenue")),
                    },
                )
            )
        return alerts


def _minmax(series: pd.Series) -> pd.Series:
    if series.empty or series.nunique() <= 1:
        return pd.Series(0.0, index=series.index)
    return (series - series.min()) / (series.max() - series.min())
