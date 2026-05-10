from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
COMMODITY_SRC = PROJECT_ROOT / "backend" / "commodity-ai-engine" / "src"
if str(COMMODITY_SRC) not in sys.path:
    sys.path.insert(0, str(COMMODITY_SRC))

from commodity_engine import (  # noqa: E402
    CommodityCustomerCluster,
    CaptureScoringEngine,
    DemandLeakageDetector,
    DemandForecaster,
    NextPurchasePredictor,
    build_historical_training_panel,
    run_capture_scoring,
    run_demand_leakage,
    run_next_purchase_prediction,
)


def _build_client_table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "client_id": [f"C{i:03d}" for i in range(6)],
            "postal_code": ["08001", "08002", "08003", "08004", "08005", "08006"],
            "province": ["Barcelona"] * 6,
            "customer_total_revenue": [1200, 1800, 950, 2500, 4000, 800],
            "customer_total_orders": [12, 10, 8, 20, 30, 6],
            "customer_avg_ticket": [100, 180, 118.75, 125, 133.33, 133.33],
            "customer_frequency": [1.2, 1.0, 0.8, 2.0, 3.0, 0.6],
            "customer_frequency_log1p": np.log1p([1.2, 1.0, 0.8, 2.0, 3.0, 0.6]),
            "days_since_last_order": [10, 25, 40, 5, 2, 60],
            "is_active_customer": [True, True, True, True, True, False],
            "return_rate_30d": [0.0, 0.1, 0.0, 0.05, 0.0, 0.2],
            "campaign_lift": [0.1, 0.0, -0.1, 0.2, 0.4, -0.2],
            "coefficient_variation_30d": [0.2, 0.3, 0.4, 0.1, 0.15, 0.5],
        }
    )


def _build_product_table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "product_id": ["P1", "P2"],
            "analytic_block": ["Commodities", "Commodities"],
            "category": ["Categoria C1", "Categoria C2"],
            "family": ["Familia C1", "Familia C2"],
            "product_total_revenue": [5000, 7000],
            "product_total_units": [200, 300],
            "product_frequency": [8.0, 10.0],
            "rolling_sales_30d": [1000.0, 1400.0],
            "product_growth_30d": [0.1, 0.2],
            "product_return_rate": [0.01, 0.02],
            "product_customer_count": [4, 5],
        }
    )


def _build_client_product_table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "client_id": ["C000", "C001", "C002", "C003", "C004", "C005"],
            "product_id": ["P1", "P1", "P2", "P2", "P1", "P2"],
            "rolling_sales_30d": [120, 180, 90, 250, 400, 60],
            "sales_growth_30d": [0.1, 0.2, -0.1, 0.3, 0.4, -0.2],
            "days_since_last_product_order": [8, 15, 20, 5, 2, 40],
            "client_product_frequency": [1.2, 1.0, 0.8, 2.0, 3.0, 0.5],
            "client_product_avg_ticket": [100, 180, 90, 125, 133.33, 60],
            "client_product_return_rate": [0.0, 0.1, 0.0, 0.05, 0.0, 0.2],
            "campaign_lift_product": [0.1, 0.0, -0.1, 0.2, 0.4, -0.2],
            "client_product_total_revenue": [1200, 1800, 900, 2500, 4000, 600],
            "client_product_total_orders": [12, 10, 8, 20, 30, 6],
        }
    )


def _build_cluster_assignments() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "customer_id": ["C000", "C001", "C002", "C003", "C004", "C005"],
            "cluster_id": [0, 1, 2, 3, 4, 0],
        }
    )


def _build_forecast_output_table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "customer_id": ["C000", "C001", "C002", "C003"],
            "product_id": ["P1", "P1", "P2", "P2"],
            "predicted_30d_sales": [160.0, 160.0, 160.0, 0.0],
            "forecast_confidence": [0.2, 0.2, 0.2, 0.2],
            "forecast_date": ["2025-04-30"] * 4,
        }
    )


def _build_leakage_output_table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "customer_id": ["C000", "C001", "C002", "C003"],
            "product_id": ["P1", "P1", "P2", "P2"],
            "cluster_id": [0, 1, 2, 1],
            "predicted_30d_sales": [140.0, 150.0, 125.0, 120.0],
            "observed_30d_sales": [60.0, 70.0, 55.0, 0.0],
            "gap_units": [80.0, 80.0, 70.0, 120.0],
            "gap_ratio": [0.57, 0.53, 0.56, 1.0],
            "volatility_penalty": [0.9, 0.8, 0.95, 1.0],
            "campaign_softener": [1.0, 0.9, 1.0, 1.0],
            "return_penalty": [1.0, 1.0, 0.96, 1.0],
            "confidence_factor": [0.6, 0.55, 0.58, 0.57],
            "leakage_score": [0.30, 0.24, 0.28, 0.45],
            "risk_level": ["high", "medium", "medium", "high"],
            "is_actionable": [True, True, True, False],
            "route_to_engine": [
                "commodity_ai_engine",
                "commodity_ai_engine",
                "commodity_ai_engine",
                "technical_product_engine",
            ],
            "routing_reason": [
                "commodity_actionable",
                "commodity_actionable",
                "commodity_actionable",
                "zero_baseline",
            ],
        }
    )


def _build_capture_output_table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "customer_id": ["C000", "C001", "C002"],
            "product_id": ["P1", "P1", "P2"],
            "cluster_id": [0, 1, 2],
            "capture_score": [42.0, 33.0, 25.0],
            "priority_rank": [1, 2, 3],
            "priority_band": ["critical", "high", "medium"],
            "recommended_action": [
                "Call within 24h",
                "Follow up this week",
                "Monitor timing",
            ],
            "leakage_score": [0.30, 0.24, 0.28],
            "gap_units": [80.0, 80.0, 70.0],
            "customer_total_revenue": [1200.0, 1800.0, 950.0],
            "customer_avg_ticket": [100.0, 180.0, 118.75],
            "customer_frequency": [1.2, 1.0, 0.8],
            "days_since_last_order": [10, 25, 40],
            "sales_growth_30d": [0.1, -0.2, -0.1],
        }
    )


def _build_sales_history_table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "invoice_id": ["I1", "I2", "I3", "I4", "I5", "I6", "I7", "I8"],
            "date": [
                "2025-01-01",
                "2025-01-20",
                "2025-02-10",
                "2025-03-01",
                "2025-01-05",
                "2025-02-04",
                "2025-03-08",
                "2025-04-12",
            ],
            "client_id": ["C000", "C000", "C000", "C000", "C002", "C002", "C002", "C002"],
            "product_id": ["P1", "P1", "P1", "P1", "P2", "P2", "P2", "P2"],
            "units": [1] * 8,
            "sales_value": [10.0] * 8,
            "is_return": [False] * 8,
            "is_campaign_period": [False] * 8,
        }
    )


def _build_leakage_panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "snapshot_date": pd.to_datetime(["2025-03-31", "2025-03-31", "2025-03-31"]),
            "customer_id": ["C000", "C001", "C002"],
            "product_id": ["P1", "P1", "P2"],
            "rolling_sales_30d": [60.0, 60.0, 30.0],
            "campaign_lift_product": [0.0, 0.2, 0.0],
            "client_product_return_rate": [0.0, 0.0, 0.1],
            "coefficient_variation_30d": [0.2, 0.5, 0.1],
            "is_active_customer": [True, False, True],
            "days_since_last_order": [30, 220, 45],
            "cluster_id": [0, 1, 2],
        }
    )


def _build_backtest_predictions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "snapshot_date": pd.to_datetime(["2025-03-31", "2025-03-31", "2025-03-31"]),
            "customer_id": ["C000", "C001", "C002"],
            "product_id": ["P1", "P1", "P2"],
            "cluster_id": [0, 1, 2],
            "actual_30d_sales": [50.0, 70.0, 20.0],
            "predicted_30d_sales": [120.0, 120.0, 90.0],
            "baseline_30d_sales": [60.0, 60.0, 30.0],
            "forecast_confidence": [0.2, 0.2, 0.2],
        }
    )


def test_cluster_loader_supports_csv_inputs(tmp_path: Path) -> None:
    client_table = _build_client_table()
    client_table.to_csv(tmp_path / "clients.csv", index=False)

    clusterer = CommodityCustomerCluster()
    loaded = clusterer.load_inputs(tmp_path)

    assert list(loaded.columns) == list(client_table.columns)
    assert len(loaded) == len(client_table)


def test_cluster_loader_supports_legacy_parquet_fallback(tmp_path: Path) -> None:
    client_table = _build_client_table()
    client_table.to_parquet(tmp_path / "clients.parquet", index=False)

    clusterer = CommodityCustomerCluster()
    loaded = clusterer.load_inputs(tmp_path)

    assert len(loaded) == len(client_table)
    assert "customer_frequency_log1p" in loaded.columns


def test_forecast_loader_supports_csv_inputs(tmp_path: Path) -> None:
    _build_client_table().to_csv(tmp_path / "clients.csv", index=False)
    _build_product_table().to_csv(tmp_path / "products.csv", index=False)
    _build_client_product_table().to_csv(tmp_path / "client_product_features.csv", index=False)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    _build_cluster_assignments().to_parquet(output_dir / "cluster_assignments.parquet", index=False)

    forecaster = DemandForecaster()
    merged = forecaster.load_inputs(tmp_path, output_dir)

    assert len(merged) == 6
    assert "customer_frequency_log1p" in merged.columns
    assert "is_active_customer" in merged.columns
    assert "cluster_id" in merged.columns


def test_leakage_loader_supports_forecast_and_feature_inputs(tmp_path: Path) -> None:
    _build_client_table().to_csv(tmp_path / "clients.csv", index=False)
    _build_client_product_table().to_csv(tmp_path / "client_product_features.csv", index=False)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    _build_forecast_output_table().to_parquet(output_dir / "consumption_forecast.parquet", index=False)
    _build_cluster_assignments().iloc[:4].to_parquet(output_dir / "cluster_assignments.parquet", index=False)

    detector = DemandLeakageDetector()
    merged = detector.load_inputs(tmp_path, output_dir)

    assert len(merged) == 4
    assert "rolling_sales_30d" in merged.columns
    assert "coefficient_variation_30d" in merged.columns
    assert "cluster_id" in merged.columns


def test_capture_loader_supports_leakage_and_feature_inputs(tmp_path: Path) -> None:
    _build_client_table().to_csv(tmp_path / "clients.csv", index=False)
    _build_product_table().to_csv(tmp_path / "products.csv", index=False)
    _build_client_product_table().to_csv(tmp_path / "client_product_features.csv", index=False)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    _build_leakage_output_table().to_parquet(output_dir / "demand_leakage_signals.parquet", index=False)
    _build_cluster_assignments().iloc[:4].to_parquet(output_dir / "cluster_assignments.parquet", index=False)

    scorer = CaptureScoringEngine()
    merged = scorer.load_inputs(tmp_path, output_dir)

    assert len(merged) == 4
    assert "customer_total_revenue" in merged.columns
    assert "sales_growth_30d" in merged.columns
    assert "family" in merged.columns or "product_family" in merged.columns


def test_next_purchase_loader_supports_capture_and_feature_inputs(tmp_path: Path) -> None:
    _build_client_table().to_csv(tmp_path / "clients.csv", index=False)
    _build_client_product_table().to_csv(tmp_path / "client_product_features.csv", index=False)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    _build_capture_output_table().to_parquet(output_dir / "capture_opportunities.parquet", index=False)
    _build_cluster_assignments().iloc[:3].to_parquet(output_dir / "cluster_assignments.parquet", index=False)

    predictor = NextPurchasePredictor()
    merged = predictor.load_inputs(tmp_path, output_dir)

    assert len(merged) == 3
    assert "days_since_last_product_order" in merged.columns
    assert "client_product_frequency" in merged.columns
    assert "coefficient_variation_30d" in merged.columns


def test_leakage_schema_validation_fails_when_required_columns_are_missing() -> None:
    detector = DemandLeakageDetector()
    invalid = pd.DataFrame(
        {
            "customer_id": ["C000"],
            "product_id": ["P1"],
            "predicted_30d_sales": [100.0],
            "rolling_sales_30d": [80.0],
        }
    )

    with pytest.raises(ValueError, match="required columns"):
        detector.validate_schema(invalid)


def test_capture_schema_validation_fails_when_required_columns_are_missing() -> None:
    scorer = CaptureScoringEngine()
    invalid = pd.DataFrame(
        {
            "customer_id": ["C000"],
            "product_id": ["P1"],
            "leakage_score": [0.2],
            "gap_units": [50.0],
        }
    )

    with pytest.raises(ValueError, match="required columns"):
        scorer.validate_schema(invalid)


def test_next_purchase_schema_validation_fails_when_required_columns_are_missing() -> None:
    predictor = NextPurchasePredictor()
    invalid = pd.DataFrame(
        {
            "customer_id": ["C000"],
            "product_id": ["P1"],
            "capture_score": [42.0],
        }
    )

    with pytest.raises(ValueError, match="required columns"):
        predictor.validate_schema(invalid)


def test_cluster_schema_allows_real_client_extras() -> None:
    clusterer = CommodityCustomerCluster(n_clusters=3, random_state=42)
    client_table = _build_client_table()

    matrix = clusterer.prepare_matrix(client_table)
    clusterer.fit(matrix, raw_df=client_table)
    labels = clusterer.predict(matrix)
    profiles = clusterer.build_cluster_profiles(client_table, labels)
    metrics = clusterer.compute_metrics(matrix, labels)

    assert matrix.shape == (6, 10)
    assert len(np.unique(labels)) == 3
    assert "cluster_name" in profiles.columns
    assert set(metrics["cluster_labels"].values()) == {
        "null_or_marginal",
        "loyal",
        "promiscuous",
    }


def test_snapshot_target_uses_future_window_only() -> None:
    sales = pd.DataFrame(
        {
            "invoice_number": ["I1", "I2", "I3", "I4", "I5", "I6", "I7", "I8"],
            "sale_date": pd.to_datetime(
                [
                    "2025-01-10",
                    "2025-01-20",
                    "2025-02-10",
                    "2025-03-10",
                    "2025-01-15",
                    "2025-02-20",
                    "2025-03-25",
                    "2025-04-10",
                ]
            ),
            "client_id": ["C1", "C1", "C1", "C1", "C2", "C2", "C2", "C2"],
            "product_id": ["P1", "P1", "P1", "P1", "P2", "P2", "P2", "P2"],
            "amount": [100.0, 50.0, 200.0, 300.0, 80.0, 40.0, 60.0, 90.0],
            "units": [1, 1, 2, 3, 1, 1, 1, 1],
            "postal_code": ["08001", "08001", "08001", "08001", "08002", "08002", "08002", "08002"],
            "province": ["Barcelona"] * 8,
            "analytic_block": ["Commodities"] * 8,
            "category": ["Categoria C1", "Categoria C1", "Categoria C1", "Categoria C1", "Categoria C2", "Categoria C2", "Categoria C2", "Categoria C2"],
            "family": ["Familia C1", "Familia C1", "Familia C1", "Familia C1", "Familia C2", "Familia C2", "Familia C2", "Familia C2"],
            "is_campaign_period": [False, False, True, False, False, True, False, False],
            "is_return": [False] * 8,
        }
    )

    panel = build_historical_training_panel(sales, n_clusters=2, random_state=42)
    jan_snapshot = panel.loc[
        panel["snapshot_date"].eq(pd.Timestamp("2025-01-31"))
        & panel["customer_id"].eq("C1")
        & panel["product_id"].eq("P1")
    ]

    assert not jan_snapshot.empty
    assert float(jan_snapshot["target_30d_sales"].iloc[0]) == 200.0
    assert 140.0 <= float(jan_snapshot["baseline_30d_sales"].iloc[0]) <= 150.0


def test_forecast_predictions_are_non_negative_and_confidence_is_bounded() -> None:
    rows = []
    for month_index, snapshot_date in enumerate(
        pd.date_range("2024-01-31", periods=18, freq="M"),
        start=1,
    ):
        for customer_index in range(4):
            customer_id = f"C{customer_index}"
            product_id = "P1" if customer_index % 2 == 0 else "P2"
            rolling_sales = 100 + month_index * 5 + customer_index * 10
            rows.append(
                {
                    "customer_id": customer_id,
                    "product_id": product_id,
                    "rolling_sales_30d": rolling_sales,
                    "sales_growth_30d": 0.05 * (customer_index + 1),
                    "days_since_last_product_order": 5 + customer_index,
                    "client_product_frequency": 1.0 + customer_index * 0.2,
                    "client_product_avg_ticket": 90 + customer_index * 10,
                    "client_product_return_rate": 0.01 * customer_index,
                    "campaign_lift_product": 0.1,
                    "client_product_total_revenue": rolling_sales * 6,
                    "client_product_total_orders": 5 + customer_index,
                    "analytic_block": "Commodities",
                    "category": "Categoria C1",
                    "product_family": "Familia C1" if product_id == "P1" else "Familia C2",
                    "product_total_revenue": 10000 + month_index * 100,
                    "product_total_units": 500,
                    "product_frequency": 10 + month_index,
                    "product_growth_30d": 0.1,
                    "product_return_rate": 0.02,
                    "product_customer_count": 50,
                    "postal_code": "08001",
                    "province": "Barcelona",
                    "customer_total_revenue": 5000 + month_index * 50,
                    "customer_total_orders": 20 + customer_index,
                    "customer_avg_ticket": 150.0,
                    "customer_frequency": 1.5,
                    "customer_frequency_log1p": np.log1p(1.5),
                    "days_since_last_order": 8 + customer_index,
                    "is_active_customer": True,
                    "return_rate_30d": 0.01,
                    "campaign_lift": 0.2,
                    "coefficient_variation_30d": 0.3,
                    "cluster_id": customer_index % 2,
                    "snapshot_date": snapshot_date,
                    "snapshot_month": snapshot_date.month,
                    "snapshot_quarter": snapshot_date.quarter,
                    "target_30d_sales": rolling_sales * 1.1,
                    "baseline_30d_sales": rolling_sales,
                }
            )
    training_df = pd.DataFrame(rows)

    forecaster = DemandForecaster()
    X, y = forecaster.build_training_frame(training_df)
    forecaster.train(X, y)
    inference_raw = forecaster.build_prediction_frame(training_df.tail(8))
    predictions = forecaster.predict(inference_raw)
    confidence = forecaster.estimate_confidence(inference_raw, predictions)

    assert np.all(predictions >= 0)
    assert np.all(confidence >= 0)
    assert np.all(confidence <= 1)


def test_leakage_scoring_is_bounded_and_penalizes_campaign_volatility_and_returns() -> None:
    detector = DemandLeakageDetector()
    base = pd.DataFrame(
        {
            "customer_id": ["C000", "C001", "C002", "C003"],
            "product_id": ["P1", "P1", "P1", "P1"],
            "predicted_30d_sales": [100.0, 100.0, 100.0, 0.0],
            "rolling_sales_30d": [40.0, 40.0, 40.0, 10.0],
            "campaign_lift_product": [0.0, 0.8, 0.0, 0.0],
            "client_product_return_rate": [0.0, 0.0, 0.4, 0.0],
            "coefficient_variation_30d": [0.1, 0.1, 0.8, 0.3],
            "forecast_confidence": [0.2, 0.2, 0.2, 0.2],
            "is_active_customer": [True, True, True, True],
            "days_since_last_order": [10, 10, 10, 10],
        }
    )

    scored = detector.compute_scores(base)

    assert np.all(scored["gap_ratio"].between(0, 1))
    assert np.all(scored["leakage_score"].between(0, 1))
    assert float(scored.loc[0, "leakage_score"]) > float(scored.loc[1, "leakage_score"])
    assert float(scored.loc[0, "leakage_score"]) > float(scored.loc[2, "leakage_score"])
    assert float(scored.loc[3, "gap_ratio"]) == 0.0
    assert float(scored.loc[3, "leakage_score"]) == 0.0


def test_leakage_actionability_routes_inactive_stale_and_zero_baseline_rows() -> None:
    detector = DemandLeakageDetector()
    frame = pd.DataFrame(
        {
            "customer_id": ["C000", "C001", "C002", "C003"],
            "product_id": ["P1", "P1", "P2", "P2"],
            "predicted_30d_sales": [120.0, 120.0, 120.0, 120.0],
            "rolling_sales_30d": [60.0, 60.0, 60.0, 0.0],
            "campaign_lift_product": [0.0, 0.0, 0.0, 0.0],
            "client_product_return_rate": [0.0, 0.0, 0.0, 0.0],
            "coefficient_variation_30d": [0.1, 0.1, 0.1, 0.1],
            "forecast_confidence": [0.2, 0.2, 0.2, 0.2],
            "is_active_customer": [True, False, True, True],
            "days_since_last_order": [20, 20, 300, 20],
        }
    )

    routed = detector.filter_actionable(detector.compute_scores(frame))

    assert bool(routed.loc[0, "is_actionable"]) is True
    assert str(routed.loc[0, "route_to_engine"]) == "commodity_ai_engine"
    assert str(routed.loc[1, "route_to_engine"]) == "technical_product_engine"
    assert "inactive_customer" in str(routed.loc[1, "routing_reason"])
    assert str(routed.loc[2, "route_to_engine"]) == "technical_product_engine"
    assert "stale_customer" in str(routed.loc[2, "routing_reason"])
    assert str(routed.loc[3, "route_to_engine"]) == "technical_product_engine"
    assert "zero_baseline" in str(routed.loc[3, "routing_reason"])


def test_capture_scoring_outputs_ranked_scores_bands_and_recommendations() -> None:
    scorer = CaptureScoringEngine()
    frame = _build_leakage_output_table().merge(
        _build_client_table().rename(columns={"client_id": "customer_id"}),
        on="customer_id",
        how="left",
    ).merge(
        _build_client_product_table().rename(columns={"client_id": "customer_id"}),
        on=["customer_id", "product_id"],
        how="left",
    ).merge(
        _build_product_table(),
        on="product_id",
        how="left",
    )

    scored = scorer.score(frame)

    assert len(scored) == 3
    assert np.all(scored["capture_score"].between(0, 100))
    assert scored["priority_rank"].is_unique
    assert scored["priority_rank"].is_monotonic_increasing
    assert not scored["recommended_action"].astype(str).str.len().eq(0).any()
    assert set(scored["priority_band"]).issubset({"critical", "high", "medium", "low"})


def test_capture_run_writes_metrics_artifact(tmp_path: Path) -> None:
    project_root = tmp_path
    features_dir = project_root / "backend" / "processed_data" / "historical"
    output_dir = project_root / "backend" / "commodity-ai-engine" / "output" / "historical"
    metrics_dir = output_dir / "metrics"
    features_dir.mkdir(parents=True)
    metrics_dir.mkdir(parents=True)

    _build_client_table().iloc[:4].to_csv(features_dir / "clients.csv", index=False)
    _build_product_table().to_csv(features_dir / "products.csv", index=False)
    _build_client_product_table().iloc[:4].to_csv(features_dir / "client_product_features.csv", index=False)
    _build_leakage_output_table().to_parquet(output_dir / "demand_leakage_signals.parquet", index=False)
    _build_cluster_assignments().iloc[:4].to_parquet(output_dir / "cluster_assignments.parquet", index=False)
    _build_backtest_predictions().to_parquet(metrics_dir / "forecast_backtest_predictions.parquet", index=False)

    artifacts = run_capture_scoring("historical", project_root=project_root)

    assert artifacts["capture_output"].exists()
    assert artifacts["capture_metrics"].exists()

    metrics = json.loads(artifacts["capture_metrics"].read_text(encoding="utf-8"))
    assert "scored_rows" in metrics
    assert "historical_validation_proxy" in metrics


def test_next_purchase_predictions_are_valid_and_contact_windows_are_coherent() -> None:
    predictor = NextPurchasePredictor()
    frame = _build_capture_output_table().merge(
        _build_client_product_table().rename(columns={"client_id": "customer_id"}),
        on=["customer_id", "product_id"],
        how="left",
    ).merge(
        _build_client_table().rename(columns={"client_id": "customer_id"})[
            ["customer_id", "coefficient_variation_30d", "days_since_last_order"]
        ],
        on="customer_id",
        how="left",
    )
    if "sales_growth_30d_x" in frame.columns and "sales_growth_30d" not in frame.columns:
        frame = frame.rename(columns={"sales_growth_30d_x": "sales_growth_30d"})

    predictions = predictor.build_predictions(frame, pd.Timestamp("2025-04-30"))

    assert predictions["expected_next_purchase_date"].notna().all()
    assert predictions["purchase_probability"].between(0, 1).all()
    assert (
        pd.to_datetime(predictions["contact_window_start"])
        <= pd.to_datetime(predictions["contact_window_end"])
    ).all()
    assert (
        pd.to_datetime(predictions["contact_window_end"])
        < pd.to_datetime(predictions["expected_next_purchase_date"])
    ).all()


def test_next_purchase_run_writes_metrics_artifact(tmp_path: Path) -> None:
    project_root = tmp_path
    features_dir = project_root / "backend" / "processed_data" / "historical"
    output_dir = project_root / "backend" / "commodity-ai-engine" / "output" / "historical"
    features_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)

    _build_client_table().iloc[:3].to_csv(features_dir / "clients.csv", index=False)
    _build_client_product_table().iloc[:3].to_csv(features_dir / "client_product_features.csv", index=False)
    _build_capture_output_table().to_parquet(output_dir / "capture_opportunities.parquet", index=False)
    _build_cluster_assignments().iloc[:3].to_parquet(output_dir / "cluster_assignments.parquet", index=False)
    _build_sales_history_table().to_csv(features_dir / "sales_enriched.csv", index=False)

    artifacts = run_next_purchase_prediction("historical", project_root=project_root)

    assert artifacts["next_purchase_output"].exists()
    assert artifacts["next_purchase_metrics"].exists()

    metrics = json.loads(artifacts["next_purchase_metrics"].read_text(encoding="utf-8"))
    assert "prediction_rows" in metrics
    assert "historical_validation_proxy" in metrics


def test_historical_leakage_run_writes_metrics_artifact(tmp_path: Path) -> None:
    project_root = tmp_path
    features_dir = project_root / "backend" / "processed_data" / "historical"
    output_dir = project_root / "backend" / "commodity-ai-engine" / "output" / "historical"
    features_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)

    _build_client_table().iloc[:4].to_csv(features_dir / "clients.csv", index=False)
    _build_client_product_table().iloc[:4].to_csv(features_dir / "client_product_features.csv", index=False)
    _build_forecast_output_table().to_parquet(output_dir / "consumption_forecast.parquet", index=False)
    _build_cluster_assignments().iloc[:4].to_parquet(output_dir / "cluster_assignments.parquet", index=False)

    artifacts = run_demand_leakage(
        "historical",
        project_root=project_root,
        historical_panel=_build_leakage_panel(),
        backtest_predictions=_build_backtest_predictions(),
    )

    assert artifacts["leakage_output"].exists()
    assert artifacts["leakage_metrics"].exists()

    metrics = json.loads(artifacts["leakage_metrics"].read_text(encoding="utf-8"))
    assert "actionable_count" in metrics
    assert "historical_validation" in metrics
