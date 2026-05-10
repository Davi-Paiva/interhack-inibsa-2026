from __future__ import annotations

from datetime import datetime

import pandas as pd

from backend.signal_fusion.domain.structures import ACTIVATION_ACTORS, AlertType, FusionTables
from backend.signal_fusion.services.exporter import AlertExporter
from backend.signal_fusion.services.prioritizer import final_alert_score
from backend.signal_fusion.services.fusion_engine import SignalFusionEngine


def _tables() -> FusionTables:
    clients = pd.DataFrame(
        {
            "client_id": ["C1", "C2"],
            "province": ["Barcelona", "Madrid"],
            "customer_total_revenue": [100000.0, 20000.0],
            "customer_avg_ticket": [500.0, 200.0],
            "customer_frequency": [3.0, 0.8],
            "days_since_last_order": [5, 120],
            "is_active_customer": [True, True],
        }
    )
    products = pd.DataFrame(
        {
            "product_id": ["P1", "P2"],
            "analytic_block": ["Commodities", "Productos Tecnicos"],
            "category": ["Categoria C1", "Categoria T1"],
            "family": ["Familia C1", "Familia T1"],
            "product_total_revenue": [100000.0, 50000.0],
            "product_total_units": [1000.0, 500.0],
        }
    )
    features = pd.DataFrame(
        {
            "client_id": ["C1", "C2"],
            "product_id": ["P1", "P2"],
            "rolling_sales_30d": [10000.0, 500.0],
            "sales_growth_30d": [0.70, -0.60],
            "days_since_last_product_order": [200, 120],
            "client_product_frequency": [3.0, 0.5],
            "client_product_return_rate": [0.25, 0.05],
            "campaign_lift_product": [0.20, 0.00],
            "client_product_total_revenue": [60000.0, 8000.0],
            "client_product_total_orders": [60, 4],
        }
    )
    return FusionTables(
        clients=clients,
        products=products,
        client_product_features=features,
        potential=pd.DataFrame(
            {
                "client_id": ["C1"],
                "family": ["Familia C2"],
                "product_category": ["Categoria C2"],
                "potential_h": [10000.0],
                "current_sales": [2000.0],
                "potential_gap": [8000.0],
                "capture_ratio": [0.20],
            }
        ),
        commodity_forecast=pd.DataFrame(
            {
                "customer_id": ["C1"],
                "product_id": ["P1"],
                "predicted_30d_sales": [5000.0],
                "forecast_confidence": [0.70],
            }
        ),
        demand_leakage=pd.DataFrame(
            {
                "customer_id": ["C1"],
                "product_id": ["P1"],
                "predicted_30d_sales": [1000.0],
                "observed_30d_sales": [600.0],
                "gap_units": [400.0],
                "gap_ratio": [0.40],
                "confidence_factor": [0.80],
                "leakage_score": [0.30],
                "route_to_engine": ["commodity_ai_engine"],
                "routing_reason": ["commodity_actionable"],
            }
        ),
        capture_opportunities=pd.DataFrame(
            {
                "customer_id": ["C1"],
                "product_id": ["P1"],
                "capture_score": [50.0],
                "priority_band": ["critical"],
                "recommended_action": ["Call within 24h"],
                "gap_units": [400.0],
                "value_component": [0.90],
                "urgency_component": [0.80],
                "leakage_component": [0.30],
                "confidence_component": [0.80],
            }
        ),
        next_purchase=pd.DataFrame(
            {
                "customer_id": ["C1"],
                "product_id": ["P1"],
                "purchase_probability": [0.90],
                "days_until_expected_purchase": [2],
                "contact_window_start": ["2026-05-11"],
                "contact_window_end": ["2026-05-12"],
                "contact_recommendation": ["Contact this week"],
            }
        ),
        technical_risk=pd.DataFrame(
            {
                "client_id": ["C2"],
                "product_id": ["P2"],
                "risk_score": [0.80],
                "risk_level": ["critical"],
                "inactivity_score": [0.90],
                "inactivity_ratio": [2.5],
                "days_since_last_order": [120],
                "volume_drift_score": [0.40],
                "interval_drift_score": [0.85],
                "peer_drift_score": [0.30],
                "potential_gap": [10000.0],
                "drift_signal_count": [2],
            }
        ),
    )


def test_activation_actors_match_briefing_channels() -> None:
    assert set(ACTIVATION_ACTORS) == {"delegado", "televenta", "marketing_automation"}


def test_signal_fusion_generates_one_file_per_alarm_contract() -> None:
    alerts = SignalFusionEngine().generate_alerts(
        _tables(),
        created_at=datetime(2026, 5, 10, 9, 0, 0),
    )
    alert_types = {alert.alert_type for alert in alerts}

    assert {
        AlertType.HIGH_PURCHASE_PROBABILITY,
        AlertType.DEMAND_SPIKE_OPPORTUNITY,
        AlertType.CROSS_SELL_OPPORTUNITY,
        AlertType.CHURN_RISK,
        AlertType.DEMAND_LEAKAGE,
        AlertType.PURCHASE_ANOMALY,
        AlertType.PRODUCT_MIX_DRIFT,
        AlertType.COMMERCIAL_OPPORTUNITY_SCORE,
        AlertType.ACCOUNT_DETERIORATION,
        AlertType.EMERGING_STRATEGIC_ACCOUNT,
    }.issubset(alert_types)
    assert all(alert.actor_id in ACTIVATION_ACTORS for alert in alerts)
    assert all(alert.reason and alert.recommended_action for alert in alerts)


def test_exporter_writes_json_and_csv(tmp_path) -> None:
    alerts = SignalFusionEngine().generate_alerts(
        _tables(),
        created_at=datetime(2026, 5, 10, 9, 0, 0),
        top_n=3,
    )
    exporter = AlertExporter()

    json_path = exporter.write_json(alerts, tmp_path / "alerts.json")
    csv_path = exporter.write_csv(alerts, tmp_path / "alerts.csv")

    assert json_path.exists()
    assert csv_path.exists()
    assert "alert_id" in csv_path.read_text(encoding="utf-8")


def test_random_selection_is_seeded_and_not_ranked_only() -> None:
    engine = SignalFusionEngine()
    alerts_a = engine.generate_alerts(
        _tables(),
        created_at=datetime(2026, 5, 10, 9, 0, 0),
        selection="random",
        seed=7,
        top_n=5,
    )
    alerts_b = engine.generate_alerts(
        _tables(),
        created_at=datetime(2026, 5, 10, 9, 0, 0),
        selection="random",
        seed=7,
        top_n=5,
    )
    ranked = engine.generate_alerts(
        _tables(),
        created_at=datetime(2026, 5, 10, 9, 0, 0),
        selection="ranked",
        top_n=5,
    )

    assert [alert.alert_id for alert in alerts_a] == [alert.alert_id for alert in alerts_b]
    assert [alert.alert_id for alert in alerts_a] != [alert.alert_id for alert in ranked]


def test_balanced_selection_keeps_variety_between_types() -> None:
    alerts = SignalFusionEngine().generate_alerts(
        _tables(),
        created_at=datetime(2026, 5, 10, 9, 0, 0),
        selection="balanced",
        top_n=6,
        seed=11,
    )

    assert len({alert.alert_type for alert in alerts}) >= 3


def test_priority_score_ignores_explainability_placeholder() -> None:
    low = final_alert_score(
        impact_score=0.8,
        urgency_score=0.7,
        confidence=0.6,
        explainability_score=0.1,
    )
    high = final_alert_score(
        impact_score=0.8,
        urgency_score=0.7,
        confidence=0.6,
        explainability_score=0.95,
    )

    assert low == high
