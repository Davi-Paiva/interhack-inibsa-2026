from __future__ import annotations

import pandas as pd


def is_missing(df: pd.DataFrame | None) -> bool:
    return df is None or df.empty


def numeric(df: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in df.columns:
        return pd.Series(default, index=df.index, dtype=float)
    return pd.to_numeric(df[column], errors="coerce").fillna(default).astype(float)


def text(df: pd.DataFrame, column: str, default: str = "") -> pd.Series:
    if column not in df.columns:
        return pd.Series(default, index=df.index, dtype="string")
    return df[column].astype("string").fillna(default).str.strip()


def normalize_customer_column(df: pd.DataFrame) -> pd.DataFrame:
    if "client_id" in df.columns and "customer_id" not in df.columns:
        return df.rename(columns={"client_id": "customer_id"})
    return df
