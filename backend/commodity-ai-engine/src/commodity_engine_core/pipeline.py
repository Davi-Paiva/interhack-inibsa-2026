from __future__ import annotations

import sys
from .common import *
from .capture import CaptureScoringEngine
from .clustering import CommodityCustomerCluster
from .forecasting import DemandForecaster
from .leakage import DemandLeakageDetector
from .next_purchase import NextPurchasePredictor

_FEATURE_OUTPUT_FILES = {
    "clients": "clients.csv",
    "products": "products.csv",
    "client_product_features": "client_product_features.csv",
}


def _generate_commodity_explainability(mode: str, project_root: Path) -> None:
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from backend.explainability_engine.service import generate_commodity_explanations

    generate_commodity_explanations(mode, project_root=project_root)


def _ensure_feature_tables(mode: str, project_root: Optional[Path] = None) -> dict[str, Path]:
    """Materialize feature tables if they are missing for the requested mode."""
    project_root = (
        Path(project_root).resolve()
        if project_root is not None
        else PROJECT_ROOT
    )
    features_dir = project_root / "backend" / "processed_data" / mode
    features_dir.mkdir(parents=True, exist_ok=True)

    expected_paths = {
        name: features_dir / file_name
        for name, file_name in _FEATURE_OUTPUT_FILES.items()
    }
    if all(path.exists() for path in expected_paths.values()):
        return expected_paths

    sales_source_path = features_dir / "sales_enriched.csv"
    if not sales_source_path.exists():
        return expected_paths

    sales = _load_prepared_sales(mode, project_root)
    if sales.empty:
        return expected_paths
    embedding_bundle = build_embedding_bundle(sales)
    frames = {
        "clients": build_client_features(sales, embedding_bundle=embedding_bundle),
        "products": build_product_features(sales, embedding_bundle=embedding_bundle),
        "client_product_features": build_client_product_features(sales, embedding_bundle=embedding_bundle),
    }
    for name, frame in frames.items():
        expected_paths[name].parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(expected_paths[name], index=False)
        logger.info("Materialized %s feature table at %s", name, expected_paths[name])
    return expected_paths


def _historical_output_dir(project_root: Path) -> Path:
    return project_root / "backend" / "commodity-ai-engine" / "output" / "historical"


def _clustering_model_path(project_root: Path) -> Path:
    return _models_dir(_historical_output_dir(project_root)) / CommodityCustomerCluster._model_file_name


def _forecast_model_path(project_root: Path) -> Path:
    return _models_dir(_historical_output_dir(project_root)) / DemandForecaster._model_file_name


def _load_prepared_sales(mode: str, project_root: Optional[Path] = None) -> pd.DataFrame:
    project_root = (
        Path(project_root).resolve()
        if project_root is not None
        else PROJECT_ROOT
    )
    config = FeatureConfig(processed_data_dir=project_root / "backend" / "processed_data")
    source_frame = load_feature_source_frame(mode, config)
    return prepare_feature_source_frame(source_frame)


def _build_snapshot_dates(sales: pd.DataFrame) -> List[pd.Timestamp]:
    if sales.empty:
        return []
    max_sale_date = sales["sale_date"].max().normalize()
    first_month_end = sales["sale_date"].min().to_period("M").to_timestamp(how="end").normalize()
    all_month_ends = pd.date_range(first_month_end, max_sale_date, freq="ME")
    snapshot_dates = [
        ts.normalize()
        for ts in all_month_ends
        if ts.normalize() + pd.Timedelta(days=30) <= max_sale_date
    ]
    return snapshot_dates


def _build_forward_target(
    sales: pd.DataFrame,
    snapshot_date: pd.Timestamp,
) -> pd.DataFrame:
    horizon_end = snapshot_date + pd.Timedelta(days=30)
    window = sales.loc[sales["sale_date"].gt(snapshot_date) & sales["sale_date"].le(horizon_end)]
    if window.empty:
        return pd.DataFrame(columns=["client_id", "product_id", "target_30d_sales"])
    return (
        window.groupby(["client_id", "product_id"], dropna=False)["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "target_30d_sales"})
    )


def _attach_snapshot_metadata(df: pd.DataFrame, snapshot_date: pd.Timestamp) -> pd.DataFrame:
    enriched = df.copy()
    enriched["snapshot_date"] = pd.Timestamp(snapshot_date)
    enriched["snapshot_month"] = int(snapshot_date.month)
    enriched["snapshot_quarter"] = int(snapshot_date.quarter)
    return enriched


def build_historical_training_panel(
    sales: pd.DataFrame,
    *,
    n_clusters: int = 5,
    random_state: int = 42,
    use_embedding_features: bool = False,
) -> pd.DataFrame:
    """Build the monthly walk-forward training panel without future leakage."""
    if sales.empty:
        raise ValueError("Cannot build training panel from empty sales data")
    snapshot_dates = _build_snapshot_dates(sales)
    if not snapshot_dates:
        raise ValueError("No monthly snapshots with a complete 30-day horizon were found")

    forecaster = DemandForecaster()
    frames: List[pd.DataFrame] = []
    for snapshot_date in snapshot_dates:
        snapshot_sales = sales.loc[sales["sale_date"].le(snapshot_date)].copy()
        embedding_bundle = build_embedding_bundle(snapshot_sales)
        client_df = _attach_snapshot_metadata(
            build_client_features(snapshot_sales, embedding_bundle=embedding_bundle),
            snapshot_date,
        )
        product_df = _attach_snapshot_metadata(
            build_product_features(snapshot_sales, embedding_bundle=embedding_bundle),
            snapshot_date,
        )
        client_product_df = _attach_snapshot_metadata(
            build_client_product_features(snapshot_sales, embedding_bundle=embedding_bundle),
            snapshot_date,
        )

        clusterer = CommodityCustomerCluster(
            n_clusters=n_clusters,
            random_state=random_state,
            use_embedding_features=use_embedding_features,
        )
        cluster_matrix = clusterer.prepare_matrix(client_df)
        clusterer.fit(cluster_matrix, raw_df=client_df)
        labels = clusterer.predict(cluster_matrix)
        cluster_df = pd.DataFrame(
            {
                "customer_id": client_df["client_id"].astype("string"),
                "cluster_id": labels.astype(int),
            }
        )

        merged = forecaster.merge_feature_tables(
            client_product_df,
            product_df,
            client_df,
            cluster_df,
            source_names={
                "client_product": "snapshot_client_product_features",
                "product": "snapshot_products",
                "client": "snapshot_clients",
            },
            require_target=False,
        )
        target_df = _build_forward_target(sales, snapshot_date)
        merged = merged.merge(
            target_df.rename(columns={"client_id": "customer_id"}),
            how="left",
            on=["customer_id", "product_id"],
            validate="many_to_one",
        )
        merged["target_30d_sales"] = pd.to_numeric(merged["target_30d_sales"], errors="coerce").fillna(0.0)
        merged["baseline_30d_sales"] = pd.to_numeric(merged["rolling_sales_30d"], errors="coerce").fillna(0.0)
        merged["snapshot_date"] = pd.Timestamp(snapshot_date)
        merged["snapshot_month"] = int(snapshot_date.month)
        merged["snapshot_quarter"] = int(snapshot_date.quarter)
        frames.append(merged)

    panel = pd.concat(frames, ignore_index=True)
    panel = _normalize_frame_types(panel)
    panel["target_30d_sales"] = pd.to_numeric(panel["target_30d_sales"], errors="coerce").fillna(0.0)
    panel["baseline_30d_sales"] = pd.to_numeric(panel["baseline_30d_sales"], errors="coerce").fillna(0.0)
    panel = panel.sort_values(["snapshot_date", "customer_id", "product_id"]).reset_index(drop=True)
    return panel


def _build_latest_snapshot_frame(
    mode: str,
    project_root: Optional[Path] = None,
) -> Tuple[pd.DataFrame, pd.Timestamp]:
    project_root = (
        Path(project_root).resolve()
        if project_root is not None
        else PROJECT_ROOT
    )
    _ensure_feature_tables(mode, project_root)
    sales = _load_prepared_sales(mode, project_root)
    latest_snapshot_date = sales["sale_date"].max().normalize()
    features_dir = project_root / "backend" / "processed_data" / mode
    commodity_output_dir = project_root / "backend" / "commodity-ai-engine" / "output" / mode
    forecaster = DemandForecaster()
    latest_frame = forecaster.load_inputs(features_dir, commodity_output_dir)
    latest_frame["snapshot_date"] = latest_snapshot_date
    latest_frame["snapshot_month"] = int(latest_snapshot_date.month)
    latest_frame["snapshot_quarter"] = int(latest_snapshot_date.quarter)
    return latest_frame, latest_snapshot_date


def run_customer_clustering(
    mode: str,
    project_root: Optional[Path] = None,
    *,
    use_embedding_features: bool = False,
) -> Path:
    """Run the real customer clustering component for the latest available feature snapshot."""
    project_root = (
        Path(project_root).resolve()
        if project_root is not None
        else PROJECT_ROOT
    )
    _ensure_feature_tables(mode, project_root)
    features_dir = project_root / "backend" / "processed_data" / mode
    commodity_output_dir = project_root / "backend" / "commodity-ai-engine" / "output" / mode

    if mode == "daily":
        model_path = _clustering_model_path(project_root)
        clusterer = CommodityCustomerCluster.load_model(model_path)
        client_df = clusterer.load_inputs(features_dir)
        matrix = clusterer.prepare_matrix(client_df)
    else:
        clusterer = CommodityCustomerCluster(
            n_clusters=5,
            random_state=42,
            use_embedding_features=use_embedding_features,
        )
        client_df = clusterer.load_inputs(features_dir)
        matrix = clusterer.prepare_matrix(client_df)
        clusterer.fit(matrix, raw_df=client_df)
        clusterer.save_model(commodity_output_dir)
    labels = clusterer.predict(matrix)
    profiles = clusterer.build_cluster_profiles(client_df, labels)
    assignments_path, _ = clusterer.save_outputs(
        commodity_output_dir,
        client_df[clusterer._resolve_customer_id_column(client_df.columns)],
        labels,
        profiles,
    )
    metrics_path = _write_json(
        clusterer.compute_metrics(matrix, labels),
        _metrics_dir(commodity_output_dir) / "cluster_metrics.json",
    )
    logger.info("Saved clustering metrics to %s", metrics_path)
    return assignments_path


def _run_forecast_backtest(
    panel: pd.DataFrame,
    *,
    warmup_snapshots: int = 12,
    use_embedding_features: bool = False,
) -> Tuple[pd.DataFrame, dict]:
    if panel.empty:
        raise ValueError("Cannot run backtest on an empty panel")
    snapshot_dates = sorted(pd.to_datetime(panel["snapshot_date"]).dropna().unique())
    if len(snapshot_dates) <= warmup_snapshots:
        raise ValueError(
            f"Backtest requires more than {warmup_snapshots} snapshots; found {len(snapshot_dates)}"
        )

    prediction_frames: List[pd.DataFrame] = []
    for index in range(warmup_snapshots, len(snapshot_dates)):
        train_dates = snapshot_dates[:index]
        validation_date = snapshot_dates[index]
        train_df = panel.loc[panel["snapshot_date"].isin(train_dates)].reset_index(drop=True)
        validation_df = panel.loc[panel["snapshot_date"].eq(validation_date)].reset_index(drop=True)

        forecaster = DemandForecaster(use_embedding_features=use_embedding_features)
        X_train, y_train = forecaster.build_training_frame(train_df)
        forecaster.train(X_train, y_train)

        validation_raw = forecaster.build_prediction_frame(validation_df)
        validation_pred = forecaster.predict(validation_raw)
        validation_confidence = forecaster.estimate_confidence(validation_raw, validation_pred)
        baseline = pd.to_numeric(validation_df["baseline_30d_sales"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
        product_key = forecaster._resolved_product_key(validation_df)

        prediction_frame = pd.DataFrame(
            {
                "snapshot_date": validation_df["snapshot_date"].astype("string"),
                "customer_id": validation_df["customer_id"].astype("string"),
                product_key: validation_df[product_key].astype("string"),
                "cluster_id": pd.to_numeric(validation_df["cluster_id"], errors="coerce").fillna(-1).astype(int),
                "actual_30d_sales": pd.to_numeric(validation_df["target_30d_sales"], errors="coerce").fillna(0.0),
                "predicted_30d_sales": validation_pred,
                "baseline_30d_sales": baseline,
                "forecast_confidence": validation_confidence,
            }
        )
        prediction_frames.append(prediction_frame)

    backtest_predictions = pd.concat(prediction_frames, ignore_index=True)
    metrics = _compute_regression_metrics(
        backtest_predictions["actual_30d_sales"],
        backtest_predictions["predicted_30d_sales"],
        baseline=backtest_predictions["baseline_30d_sales"],
    )
    metrics.update(
        {
            "warmup_snapshots": int(warmup_snapshots),
            "evaluated_snapshots": int(len(snapshot_dates) - warmup_snapshots),
            "evaluated_rows": int(len(backtest_predictions)),
            "latest_evaluated_snapshot": str(pd.to_datetime(backtest_predictions["snapshot_date"]).max().date()),
            "use_embedding_features": bool(use_embedding_features),
            "passes_baseline": bool(
                metrics["rmse_improvement_vs_baseline"] > 0
                and metrics["wmape_improvement_vs_baseline"] > 0
            ),
        }
    )
    return backtest_predictions, metrics


def _select_forecast_variant(
    baseline_metrics: dict,
    embedding_metrics: dict,
) -> tuple[str, bool]:
    embedding_wins = (
        float(embedding_metrics.get("rmse", np.inf)) < float(baseline_metrics.get("rmse", np.inf))
        and float(embedding_metrics.get("wmape", np.inf)) < float(baseline_metrics.get("wmape", np.inf))
    )
    return ("embedding", True) if embedding_wins else ("baseline", False)


def run_model_evaluation(mode: str, project_root: Optional[Path] = None) -> dict[str, Path]:
    """Run historical training/evaluation or daily inference using persisted historical models."""
    project_root = (
        Path(project_root).resolve()
        if project_root is not None
        else PROJECT_ROOT
    )
    commodity_output_dir = project_root / "backend" / "commodity-ai-engine" / "output" / mode
    commodity_output_dir.mkdir(parents=True, exist_ok=True)

    if mode == "historical":
        sales = _load_prepared_sales(mode, project_root)
        baseline_panel = build_historical_training_panel(sales, use_embedding_features=False)
        baseline_backtest, baseline_metrics = _run_forecast_backtest(
            baseline_panel,
            use_embedding_features=False,
        )
        embedding_panel = build_historical_training_panel(sales, use_embedding_features=True)
        embedding_backtest, embedding_metrics = _run_forecast_backtest(
            embedding_panel,
            use_embedding_features=True,
        )
        selected_variant, use_embedding_features = _select_forecast_variant(
            baseline_metrics,
            embedding_metrics,
        )
        panel = embedding_panel if use_embedding_features else baseline_panel
        backtest_predictions = embedding_backtest if use_embedding_features else baseline_backtest
        forecast_metrics = embedding_metrics if use_embedding_features else baseline_metrics
        forecast_metrics["selected_variant"] = selected_variant
        forecast_metrics["embedding_candidate_beats_baseline"] = bool(use_embedding_features)
        experiment_report = {
            "selected_variant": selected_variant,
            "baseline": baseline_metrics,
            "embedding_candidate": embedding_metrics,
        }
        _write_json(
            experiment_report,
            _metrics_dir(commodity_output_dir) / "forecast_feature_experiment.json",
        )

        backtest_path = _write_parquet(
            backtest_predictions,
            _metrics_dir(commodity_output_dir) / "forecast_backtest_predictions.parquet",
        )
        metrics_path = _write_json(
            forecast_metrics,
            _metrics_dir(commodity_output_dir) / "forecast_metrics.json",
        )

        run_customer_clustering(
            mode,
            project_root,
            use_embedding_features=use_embedding_features,
        )
        latest_frame, latest_snapshot_date = _build_latest_snapshot_frame(mode, project_root)
        final_forecaster = DemandForecaster(use_embedding_features=use_embedding_features)
        X_all, y_all = final_forecaster.build_training_frame(panel)
        final_forecaster.train(X_all, y_all)
        final_forecaster.save_model(commodity_output_dir)
        latest_raw = final_forecaster.build_prediction_frame(latest_frame)
        latest_pred = final_forecaster.predict(latest_raw)
        latest_confidence = final_forecaster.estimate_confidence(latest_raw, latest_pred)
        forecast_path = final_forecaster.save_outputs(
            commodity_output_dir,
            latest_frame,
            latest_pred,
            latest_confidence,
        )
        leakage_artifacts = run_demand_leakage(
            mode,
            project_root=project_root,
            historical_panel=panel,
            backtest_predictions=backtest_predictions,
        )
    else:
        run_customer_clustering(mode, project_root)
        model_path = _forecast_model_path(project_root)
        latest_frame, latest_snapshot_date = _build_latest_snapshot_frame(mode, project_root)
        forecaster = DemandForecaster.load_model(model_path)
        latest_raw = forecaster.build_prediction_frame(latest_frame)
        latest_pred = forecaster.predict(latest_raw)
        latest_confidence = forecaster.estimate_confidence(latest_raw, latest_pred)
        forecast_path = forecaster.save_outputs(
            commodity_output_dir,
            latest_frame,
            latest_pred,
            latest_confidence,
        )
        inference_metrics = {
            "mode": "daily_inference",
            "model_source": str(model_path),
            "inference_rows": int(len(latest_frame)),
            "latest_snapshot_date": str(latest_snapshot_date.date()),
        }
        metrics_path = _write_json(
            inference_metrics,
            _metrics_dir(commodity_output_dir) / "forecast_inference_metrics.json",
        )
        backtest_path = model_path
        leakage_artifacts = run_demand_leakage(mode, project_root=project_root)
    capture_artifacts = run_capture_scoring(mode, project_root=project_root)
    next_purchase_artifacts = run_next_purchase_prediction(mode, project_root=project_root)
    logger.info("Latest operational forecast snapshot date: %s", latest_snapshot_date.date())
    return {
        "forecast_output": forecast_path,
        "forecast_metrics": metrics_path,
        "backtest_predictions": backtest_path,
        "leakage_output": leakage_artifacts["leakage_output"],
        "leakage_metrics": leakage_artifacts["leakage_metrics"],
        "capture_output": capture_artifacts["capture_output"],
        "capture_metrics": capture_artifacts["capture_metrics"],
        "next_purchase_output": next_purchase_artifacts["next_purchase_output"],
        "next_purchase_metrics": next_purchase_artifacts["next_purchase_metrics"],
    }




def run_consumption_forecast(mode: str, project_root: Optional[Path] = None) -> Path:
    """Run the historical evaluation pipeline and return the latest forecast artifact."""
    artifacts = run_model_evaluation(mode, project_root)
    return artifacts["forecast_output"]


def run_demand_leakage(
    mode: str,
    project_root: Optional[Path] = None,
    *,
    historical_panel: Optional[pd.DataFrame] = None,
    backtest_predictions: Optional[pd.DataFrame] = None,
) -> dict[str, Path]:
    """Score the latest demand leakage snapshot and optional historical validation."""
    project_root = (
        Path(project_root).resolve()
        if project_root is not None
        else PROJECT_ROOT
    )
    _ensure_feature_tables(mode, project_root)
    features_dir = project_root / "backend" / "processed_data" / mode
    commodity_output_dir = project_root / "backend" / "commodity-ai-engine" / "output" / mode

    detector = DemandLeakageDetector()
    latest_frame = detector.load_inputs(features_dir, commodity_output_dir)
    latest_scored = detector.compute_scores(latest_frame)
    latest_scored = detector.filter_actionable(latest_scored)
    leakage_output_path = detector.save_outputs(commodity_output_dir, latest_scored)

    leakage_metrics = detector.compute_metrics(latest_scored)
    if mode == "historical":
        if historical_panel is None:
            sales = _load_prepared_sales(mode, project_root)
            historical_panel = build_historical_training_panel(sales)
        if backtest_predictions is None:
            backtest_path = _metrics_dir(commodity_output_dir) / "forecast_backtest_predictions.parquet"
            backtest_predictions = _read_frame(backtest_path)
        historical_scored = detector.build_historical_evaluation_frame(
            historical_panel,
            backtest_predictions,
        )
        leakage_metrics["historical_validation"] = detector.compute_historical_metrics(historical_scored)

    metrics_output_path = _write_json(
        leakage_metrics,
        _metrics_dir(commodity_output_dir) / "demand_leakage_metrics.json",
    )
    _generate_commodity_explainability(mode, project_root)
    logger.info("Saved demand leakage metrics to %s", metrics_output_path)
    return {
        "leakage_output": leakage_output_path,
        "leakage_metrics": metrics_output_path,
    }


def run_capture_scoring(
    mode: str,
    project_root: Optional[Path] = None,
) -> dict[str, Path]:
    """Build the sales-ready capture opportunity queue from leakage outputs."""
    project_root = (
        Path(project_root).resolve()
        if project_root is not None
        else PROJECT_ROOT
    )
    _ensure_feature_tables(mode, project_root)
    features_dir = project_root / "backend" / "processed_data" / mode
    commodity_output_dir = project_root / "backend" / "commodity-ai-engine" / "output" / mode

    scorer = CaptureScoringEngine()
    source_df = scorer.load_inputs(features_dir, commodity_output_dir)
    scored = scorer.score(source_df)
    capture_output_path = scorer.save_outputs(commodity_output_dir, scored)
    historical_proxy = scorer.build_historical_proxy_validation(features_dir, commodity_output_dir) if mode == "historical" else None
    metrics = scorer.compute_metrics(
        scored,
        source_df=source_df,
        historical_proxy=historical_proxy,
    )
    metrics_output_path = _write_json(
        metrics,
        _metrics_dir(commodity_output_dir) / "capture_opportunity_metrics.json",
    )
    _generate_commodity_explainability(mode, project_root)
    logger.info("Saved capture opportunity metrics to %s", metrics_output_path)
    return {
        "capture_output": capture_output_path,
        "capture_metrics": metrics_output_path,
    }


def run_next_purchase_prediction(
    mode: str,
    project_root: Optional[Path] = None,
) -> dict[str, Path]:
    """Build next purchase timing predictions from capture opportunities."""
    project_root = (
        Path(project_root).resolve()
        if project_root is not None
        else PROJECT_ROOT
    )
    _ensure_feature_tables(mode, project_root)
    features_dir = project_root / "backend" / "processed_data" / mode
    commodity_output_dir = project_root / "backend" / "commodity-ai-engine" / "output" / mode

    predictor = NextPurchasePredictor()
    source_df = predictor.load_inputs(features_dir, commodity_output_dir)
    reference_date = pd.Timestamp.utcnow().normalize()
    forecast_path = commodity_output_dir / "consumption_forecast.parquet"
    if forecast_path.exists():
        forecast_df = _read_frame(forecast_path)
        if "forecast_date" in forecast_df.columns:
            parsed_reference = pd.to_datetime(forecast_df["forecast_date"], errors="coerce")
            if parsed_reference.notna().any():
                reference_date = parsed_reference.max().normalize()
    predictions = predictor.build_predictions(source_df, reference_date)
    next_purchase_output_path = predictor.save_outputs(commodity_output_dir, predictions)

    historical_proxy = None
    if mode == "historical":
        sales_path = _resolve_existing_path(features_dir, predictor._sales_candidates, "sales history table")
        sales_df = _read_frame(sales_path)
        historical_proxy = predictor.build_historical_proxy_validation(predictions, sales_df)
    metrics = predictor.compute_metrics(
        predictions,
        source_df=predictions,
        historical_proxy=historical_proxy,
    )
    metrics_output_path = _write_json(
        metrics,
        _metrics_dir(commodity_output_dir) / "next_purchase_metrics.json",
    )
    _generate_commodity_explainability(mode, project_root)
    logger.info("Saved next purchase metrics to %s", metrics_output_path)
    return {
        "next_purchase_output": next_purchase_output_path,
        "next_purchase_metrics": metrics_output_path,
    }
