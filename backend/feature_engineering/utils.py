from __future__ import annotations

import importlib.util
import json
import logging
from pathlib import Path

import pandas as pd


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def parquet_engine() -> str:
    if importlib.util.find_spec("pyarrow") is not None:
        return "pyarrow"
    if importlib.util.find_spec("fastparquet") is not None:
        return "fastparquet"
    raise RuntimeError(
        "Parquet support requires either 'pyarrow' or 'fastparquet' to be installed."
    )


def read_parquet_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required parquet input was not found: {path}")
    return pd.read_parquet(path, engine=parquet_engine())


def write_parquet_frame(
    df: pd.DataFrame,
    output_path: Path,
    compression: str,
) -> Path:
    ensure_directory(output_path.parent)
    df.to_parquet(
        output_path,
        index=False,
        compression=compression,
        engine=parquet_engine(),
    )
    return output_path


def write_json(payload: dict, output_path: Path) -> Path:
    ensure_directory(output_path.parent)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    return output_path

