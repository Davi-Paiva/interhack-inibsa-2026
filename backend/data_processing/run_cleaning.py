from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import replace
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from .cleaning import run_cleaning_pipeline
    from .config import ProcessingConfig, RunMode
    from ..feature_engineering.config import FeatureConfig
    from ..feature_engineering.features import run_feature_pipeline
except ImportError:
    from cleaning import run_cleaning_pipeline
    from config import ProcessingConfig, RunMode
    from feature_engineering.config import FeatureConfig
    from feature_engineering.features import run_feature_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the data cleaning pipeline.")
    parser.add_argument(
        "--mode",
        choices=("historical", "daily"),
        default="historical",
        help="Pipeline mode: full historical load or daily incoming load.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=None,
        help="Optional override for the raw input directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional override for the processed CSV output directory.",
    )
    parser.add_argument(
        "--sales-file",
        type=Path,
        default=None,
        help="Optional override for the sales file to process.",
    )
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> ProcessingConfig:
    config = ProcessingConfig()
    if args.input_dir is not None:
        config = replace(config, raw_data_dir=args.input_dir.resolve())
    if args.output_dir is not None:
        config = replace(config, processed_data_dir=args.output_dir.resolve())
    return config


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    args = parse_args()
    mode: RunMode = args.mode
    config = build_config(args)
    sales_path = args.sales_file.resolve() if args.sales_file is not None else None

    outputs = run_cleaning_pipeline(mode=mode, config=config, sales_path=sales_path)
    feature_outputs = run_feature_pipeline(
        mode=mode,
        config=FeatureConfig(
            processed_data_dir=config.processed_data_dir,
            raw_data_dir=config.raw_data_dir,
        ),
    )
    print(f"Cleaning pipeline finished for '{mode}' mode.")
    for dataset_name, output_path in outputs.items():
        print(f" - {dataset_name}: csv={output_path}")
    if feature_outputs:
        print("Feature engineering finished after cleaning.")
        for artifact_name, output_path in feature_outputs.items():
            print(f" - {artifact_name}: {output_path}")
    else:
        print(f"Feature engineering produced no materialized outputs for '{mode}' mode.")


if __name__ == "__main__":
    main()
