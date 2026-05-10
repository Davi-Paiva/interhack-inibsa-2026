from __future__ import annotations

import math
from typing import Iterable

import pandas as pd

from .structures import PriorityLevel, UrgencyLevel


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    numeric = safe_float(value, lower)
    if math.isnan(numeric):
        return lower
    return max(lower, min(upper, numeric))


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(result) or math.isinf(result):
        return default
    return result


def safe_str(value: object, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "<na>"}:
        return default
    return text


def score_to_priority(score: float) -> PriorityLevel:
    if score >= 85:
        return PriorityLevel.CRITICAL
    if score >= 70:
        return PriorityLevel.HIGH
    if score >= 50:
        return PriorityLevel.MEDIUM
    return PriorityLevel.LOW


def score_to_urgency(score: float) -> UrgencyLevel:
    if score >= 0.85:
        return UrgencyLevel.CRITICAL
    if score >= 0.70:
        return UrgencyLevel.HIGH
    if score >= 0.45:
        return UrgencyLevel.MEDIUM
    return UrgencyLevel.LOW


def minmax_series(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)
    if numeric.empty or numeric.nunique() <= 1:
        return pd.Series(0.0, index=numeric.index, dtype=float)
    return (numeric - numeric.min()) / (numeric.max() - numeric.min())


def first_existing(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    column_set = set(columns)
    for candidate in candidates:
        if candidate in column_set:
            return candidate
    return None
