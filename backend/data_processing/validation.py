from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd


logger = logging.getLogger(__name__)


def _safe_ratio(numerator: int | float, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


def tag_amount_outliers(df: pd.DataFrame, amount_column: str = "amount") -> pd.DataFrame:
    tagged = df.copy()
    if amount_column not in tagged.columns or tagged.empty:
        tagged["is_amount_outlier"] = False
        tagged["anomaly_tag"] = "normal"
        return tagged

    q1 = tagged[amount_column].quantile(0.25)
    q3 = tagged[amount_column].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    tagged["is_amount_outlier"] = tagged[amount_column].lt(lower_bound) | tagged[amount_column].gt(
        upper_bound
    )
    tagged["anomaly_tag"] = "normal"
    tagged.loc[tagged["is_return"], "anomaly_tag"] = "return"
    tagged.loc[tagged["is_campaign_period"], "anomaly_tag"] = "campaign_period"
    tagged.loc[tagged["is_amount_outlier"], "anomaly_tag"] = "amount_outlier"
    tagged.loc[
        tagged["is_amount_outlier"] & tagged["is_campaign_period"],
        "anomaly_tag",
    ] = "campaign_amount_outlier"
    tagged.loc[
        tagged["is_amount_outlier"] & tagged["is_return"],
        "anomaly_tag",
    ] = "return_amount_outlier"
    return tagged


def remove_non_campaign_outliers(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "is_amount_outlier" not in df.columns or "is_campaign_period" not in df.columns:
        return df

    filtered = df.loc[~(df["is_amount_outlier"] & ~df["is_campaign_period"])].copy()
    removed_rows = len(df) - len(filtered)
    if removed_rows:
        logger.warning(
            "Removed %s amount outliers outside campaign periods.",
            removed_rows,
        )
    return filtered.reset_index(drop=True)


def build_quality_metrics(
    df: pd.DataFrame,
    *,
    dataset_name: str,
    date_column: str = "sale_date",
    duplicate_subset: list[str] | None = None,
    outlier_column: str = "is_amount_outlier",
) -> dict[str, Any]:
    row_count = len(df)
    missing_ratio = _safe_ratio(int(df.isna().sum().sum()), row_count * max(len(df.columns), 1))
    duplicate_ratio = _safe_ratio(
        int(df.duplicated(subset=duplicate_subset).sum()),
        row_count,
    )
    invalid_date_ratio = 0.0
    if date_column in df.columns:
        invalid_date_ratio = _safe_ratio(int(df[date_column].isna().sum()), row_count)
    outlier_ratio = 0.0
    if outlier_column in df.columns:
        outlier_ratio = _safe_ratio(int(df[outlier_column].fillna(False).sum()), row_count)

    metrics = {
        "dataset_name": dataset_name,
        "row_count": row_count,
        "missing_ratio": round(missing_ratio, 6),
        "duplicate_ratio": round(duplicate_ratio, 6),
        "invalid_date_ratio": round(invalid_date_ratio, 6),
        "outlier_ratio": round(outlier_ratio, 6),
    }
    return metrics


def build_drift_metrics(
    historical_df: pd.DataFrame,
    daily_df: pd.DataFrame,
    numeric_columns: list[str],
) -> dict[str, Any]:
    drift: dict[str, Any] = {"status": "not_available", "features": {}}
    if historical_df.empty or daily_df.empty:
        logger.warning("Drift monitoring skipped because one of the datasets is empty.")
        return drift

    drift["status"] = "ok"
    for column in numeric_columns:
        if column not in historical_df.columns or column not in daily_df.columns:
            continue

        hist_mean = float(historical_df[column].dropna().mean())
        daily_mean = float(daily_df[column].dropna().mean())
        hist_std = float(historical_df[column].dropna().std())
        mean_shift = daily_mean - hist_mean
        std_scale = hist_std if hist_std > 1e-9 else 1.0
        z_score_shift = mean_shift / std_scale

        drift["features"][column] = {
            "historical_mean": round(hist_mean, 6),
            "daily_mean": round(daily_mean, 6),
            "mean_shift": round(mean_shift, 6),
            "z_score_shift": round(z_score_shift, 6),
            "warning": abs(z_score_shift) >= 2.0,
        }

        if abs(z_score_shift) >= 2.0:
            logger.warning("Potential drift detected for %s: z-score shift %.2f", column, z_score_shift)

    return drift


def save_metrics_json(metrics: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=True), encoding="utf-8")
    logger.info("Saved quality metrics to %s", output_path)
    return output_path
