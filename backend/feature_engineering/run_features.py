from __future__ import annotations

import argparse
import logging
from dataclasses import replace
from pathlib import Path

import pandas as pd

try:
    from .config import FeatureConfig, RunMode
    from .features import (
        CLIENT_FEATURE_COLUMNS,
        CLIENT_PRODUCT_FEATURE_COLUMNS,
        PRODUCT_FEATURE_COLUMNS,
        align_feature_tables_to_contract,
        build_client_features,
        build_client_product_features,
        build_product_features,
        load_feature_source_frame,
        prepare_feature_source_frame,
        resolve_feature_source_path,
        write_removed_feature_log,
        write_feature_frames,
    )
    from .metrics.metrics import build_feature_metrics_bundle, save_feature_metrics_bundle
except ImportError:
    from config import FeatureConfig, RunMode
    from features import (
        CLIENT_FEATURE_COLUMNS,
        CLIENT_PRODUCT_FEATURE_COLUMNS,
        PRODUCT_FEATURE_COLUMNS,
        align_feature_tables_to_contract,
        build_client_features,
        build_client_product_features,
        build_product_features,
        load_feature_source_frame,
        prepare_feature_source_frame,
        resolve_feature_source_path,
        write_removed_feature_log,
        write_feature_frames,
    )
    from metrics.metrics import build_feature_metrics_bundle, save_feature_metrics_bundle


logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run feature engineering after the data cleaning stage."
    )
    parser.add_argument(
        "--mode",
        choices=("historical", "daily"),
        default="historical",
        help="Pipeline mode. Historical is implemented now; daily is scaffolded for future incremental ingestion.",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=None,
        help="Optional override for the processed data root directory.",
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
        help="Logging verbosity for the orchestration run.",
    )
    return parser.parse_args()


def configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def build_config(args: argparse.Namespace) -> FeatureConfig:
    config = FeatureConfig()
    if args.processed_dir is not None:
        config = replace(config, processed_data_dir=args.processed_dir.resolve())
    return config


def build_feature_tables(sales) -> dict[str, object]:
    return {
        "client_features": build_client_features(sales),
        "product_features": build_product_features(sales),
        "client_product_features": build_client_product_features(sales),
    }


def empty_feature_tables() -> dict[str, object]:
    return {
        "client_features": pd.DataFrame(
            columns=CLIENT_FEATURE_COLUMNS
        ),
        "product_features": pd.DataFrame(
            columns=PRODUCT_FEATURE_COLUMNS
        ),
        "client_product_features": pd.DataFrame(
            columns=CLIENT_PRODUCT_FEATURE_COLUMNS
        ),
    }


def run_historical_feature_flow(config: FeatureConfig) -> dict[str, object]:
    logger.info("Feature pipeline stage: load cleaned outputs")
    source_path = resolve_feature_source_path("historical", config)
    source_frame = load_feature_source_frame("historical", config)

    logger.info("Feature pipeline stage: prepare feature source")
    sales = prepare_feature_source_frame(source_frame)

    logger.info("Feature pipeline stage: generate feature tables")
    tables = build_feature_tables(sales) if not sales.empty else empty_feature_tables()
    tables, removed_columns_by_table = align_feature_tables_to_contract(tables)

    logger.info("Feature pipeline stage: save parquet outputs")
    parquet_outputs = write_feature_frames(tables, mode="historical", config=config)
    parquet_outputs["removed_extra_features"] = write_removed_feature_log(
        removed_columns_by_table,
        mode="historical",
        config=config,
    )

    logger.info("Feature pipeline stage: validate features and save metrics")
    metrics_bundle = build_feature_metrics_bundle(
        mode="historical",
        source_dataset=source_path.name,
        source_sales=sales,
        tables=tables,
    )
    metric_outputs = save_feature_metrics_bundle(metrics_bundle, config.metrics_dir_for_mode("historical"))

    return {
        "source_rows": len(source_frame),
        "prepared_rows": len(sales),
        "tables": tables,
        "parquet_outputs": parquet_outputs,
        "metric_outputs": metric_outputs,
    }


def run_daily_feature_flow(config: FeatureConfig) -> dict[str, object]:
    logger.info("Daily feature mode is not implemented yet.")
    logger.info("Expected future flow: cleaned daily parquet -> incremental features -> validation -> metrics.")
    # TODO: Load only the latest cleaned daily outputs.
    # TODO: Recompute impacted client, product, and client-product feature rows only.
    # TODO: Reuse the same validation and output contracts as historical mode.
    return {
        "source_rows": 0,
        "prepared_rows": 0,
        "tables": {},
        "parquet_outputs": {},
        "metric_outputs": {},
    }


def run_feature_orchestration(mode: RunMode, config: FeatureConfig) -> dict[str, object]:
    if mode == "daily":
        return run_daily_feature_flow(config)
    return run_historical_feature_flow(config)


def print_execution_summary(mode: RunMode, result: dict[str, object], config: FeatureConfig) -> None:
    print(f"Feature engineering finished for '{mode}' mode.")
    print("Pipeline: RAW -> DATA CLEANING -> FEATURE ENGINEERING -> COMMODITY AI ENGINE -> TECHNICAL PRODUCT ENGINE")

    if mode == "daily":
        print("Daily mode is scaffolded but no outputs were materialized yet.")
        return

    print(f" - cleaned source rows: {result['source_rows']}")
    print(f" - prepared commodity rows: {result['prepared_rows']}")
    print(f" - feature output dir: {config.features_dir_for_mode(mode)}")
    print(f" - metrics output dir: {config.metrics_dir_for_mode(mode)}")

    tables = result["tables"]
    for table_name, frame in tables.items():
        print(f" - {table_name}: rows={len(frame)} cols={len(frame.columns)}")

    parquet_outputs = result["parquet_outputs"]
    for artifact_name, output_path in parquet_outputs.items():
        print(f"   parquet -> {artifact_name}: {output_path}")

    metric_outputs = result["metric_outputs"]
    for artifact_name, output_path in metric_outputs.items():
        print(f"   metrics -> {artifact_name}: {output_path}")


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)
    mode: RunMode = args.mode
    config = build_config(args)
    result = run_feature_orchestration(mode, config)
    print_execution_summary(mode, result, config)


if __name__ == "__main__":
    main()
