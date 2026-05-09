from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd


def normalize_header(column_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(column_name))
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    return normalized.strip("_")


def read_raw_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return pd.read_csv(path, dtype=str, encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Unable to decode CSV file: {path}")


def strip_string_columns(df: pd.DataFrame) -> pd.DataFrame:
    for column in df.columns:
        df[column] = df[column].map(lambda value: value.strip() if isinstance(value, str) else value)
    return df.replace({"": pd.NA})


def clean_identifier(series: pd.Series, zero_fill: int | None = None) -> pd.Series:
    cleaned = series.astype("string").str.strip()
    cleaned = cleaned.str.replace(r"\.0$", "", regex=True)
    if zero_fill is not None:
        cleaned = cleaned.str.zfill(zero_fill)
    return cleaned


def parse_us_date(series: pd.Series) -> tuple[pd.Series, int]:
    parsed = pd.to_datetime(series, format="%m/%d/%Y", errors="coerce")
    invalid_count = int(series.notna().sum() - parsed.notna().sum())
    return parsed.dt.strftime("%Y-%m-%d"), invalid_count


def parse_european_numeric(series: pd.Series, as_integer: bool) -> tuple[pd.Series, int]:
    normalized = (
        series.astype("string")
        .str.strip()
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    parsed = pd.to_numeric(normalized, errors="coerce")
    invalid_count = int(series.notna().sum() - parsed.notna().sum())
    if as_integer:
        return parsed.round().astype("Int64"), invalid_count
    return parsed.round(2), invalid_count


def first_non_null_value(series: pd.Series) -> object:
    non_null = series.dropna()
    if non_null.empty:
        return pd.NA
    return non_null.iloc[0]