from __future__ import annotations

import argparse
import logging
from dataclasses import replace
from pathlib import Path

try:
    from .cleaning import run_cleaning_pipeline
    from .config import ProcessingConfig, RunMode
except ImportError:
    from cleaning import run_cleaning_pipeline
    from config import ProcessingConfig, RunMode


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
        help="Optional override for the processed parquet output directory.",
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
    print(f"Cleaning pipeline finished for '{mode}' mode.")
    for dataset_name, output_paths in outputs.items():
        if dataset_name == "quality_metrics":
            print(f" - {dataset_name}: json={output_paths['json']}")
            continue
        print(f" - {dataset_name}: parquet={output_paths['parquet']} csv={output_paths['csv']}")


if __name__ == "__main__":
    main()
