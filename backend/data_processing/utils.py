from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Iterable

import pandas as pd


def read_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False)
        except UnicodeDecodeError:
            continue

    raise UnicodeDecodeError("utf-8", b"", 0, 1, f"Could not decode {path}")


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_required_columns(
    df: pd.DataFrame,
    required_columns: Iterable[str],
    dataset_name: str,
) -> None:
    missing_columns = sorted(set(required_columns) - set(df.columns))
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"{dataset_name} is missing required columns: {missing}")


def normalize_identifier(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def normalize_text(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def parse_decimal_series(series: pd.Series) -> pd.Series:
    normalized = series.astype("string").str.strip()
    has_comma = normalized.str.contains(",", na=False)

    cleaned = normalized.where(
        ~has_comma,
        normalized.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
    )
    return pd.to_numeric(cleaned, errors="coerce")


def parse_datetime_series(series: pd.Series, date_format: str) -> pd.Series:
    return pd.to_datetime(series, format=date_format, errors="coerce")


def parquet_engine() -> str:
    if importlib.util.find_spec("pyarrow") is not None:
        return "pyarrow"
    if importlib.util.find_spec("fastparquet") is not None:
        return "fastparquet"
    raise RuntimeError(
        "Parquet output requires either 'pyarrow' or 'fastparquet' to be installed."
    )


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


def write_csv_frame(df: pd.DataFrame, output_path: Path) -> Path:
    ensure_directory(output_path.parent)
    df.to_csv(output_path, index=False)
    return output_path
