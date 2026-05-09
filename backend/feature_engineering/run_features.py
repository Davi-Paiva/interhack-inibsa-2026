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
        prepare_all_product_feature_source_frame,
        build_client_features,
        build_client_product_features,
        build_product_features,
        load_feature_source_frame,
        prepare_feature_source_frame,
        write_feature_frames,
    )
except ImportError:
    from config import FeatureConfig, RunMode
    from features import (
        CLIENT_FEATURE_COLUMNS,
        CLIENT_PRODUCT_FEATURE_COLUMNS,
        PRODUCT_FEATURE_COLUMNS,
        align_feature_tables_to_contract,
        prepare_all_product_feature_source_frame,
        build_client_features,
        build_client_product_features,
        build_product_features,
        load_feature_source_frame,
        prepare_feature_source_frame,
        write_feature_frames,
    )


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


def build_feature_tables(commodity_sales, all_product_sales) -> dict[str, object]:
    return {
        "client_features": build_client_features(commodity_sales),
        "product_features": build_product_features(all_product_sales),
        "client_product_features": build_client_product_features(commodity_sales),
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
    source_frame = load_feature_source_frame("historical", config)

    logger.info("Feature pipeline stage: prepare feature source")
    commodity_sales = prepare_feature_source_frame(source_frame)
    all_product_sales = prepare_all_product_feature_source_frame(source_frame)

    logger.info("Feature pipeline stage: generate feature tables")
    tables = (
        build_feature_tables(commodity_sales, all_product_sales)
        if not commodity_sales.empty or not all_product_sales.empty
        else empty_feature_tables()
    )
    tables, _ = align_feature_tables_to_contract(tables)

    logger.info("Feature pipeline stage: save CSV outputs")
    csv_outputs = write_feature_frames(tables, mode="historical", config=config)

    return {
        "source_rows": len(source_frame),
        "prepared_rows": len(commodity_sales),
        "tables": tables,
        "csv_outputs": csv_outputs,
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
        "csv_outputs": {},
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

    tables = result["tables"]
    for table_name, frame in tables.items():
        print(f" - {table_name}: rows={len(frame)} cols={len(frame.columns)}")

    csv_outputs = result["csv_outputs"]
    for artifact_name, output_path in csv_outputs.items():
        print(f"   csv -> {artifact_name}: {output_path}")


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)
    mode: RunMode = args.mode
    config = build_config(args)
    result = run_feature_orchestration(mode, config)
    print_execution_summary(mode, result, config)


if __name__ == "__main__":
    main()
