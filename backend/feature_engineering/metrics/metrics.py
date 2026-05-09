from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

try:
    from ..utils import write_json
except (ImportError, ValueError):
    from utils import write_json


def _safe_ratio(numerator: int | float, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


def build_feature_metrics(
    features: pd.DataFrame,
    *,
    mode: str,
    source_rows: int,
) -> dict[str, Any]:
    row_count = len(features)
    column_count = len(features.columns)
    missing_cells = int(features.isna().sum().sum()) if row_count else 0

    metrics: dict[str, Any] = {
        "mode": mode,
        "source_rows": source_rows,
        "feature_rows": row_count,
        "feature_columns": column_count,
        "missing_ratio": round(
            _safe_ratio(missing_cells, max(row_count * max(column_count, 1), 1)),
            6,
        ),
        "date_span": {
            "min": None,
            "max": None,
        },
        "daily_incremental_features": {
            "status": "todo",
            "note": "Future support should only recompute impacted entities for daily runs.",
        },
        "feature_drift_monitoring": {
            "status": "todo",
            "note": "Add daily-vs-historical feature drift checks once daily feature outputs exist.",
        },
        "feature_store_support": {
            "status": "todo",
            "note": "Add export adapters for an external feature store when the serving layer is defined.",
        },
    }

    if row_count and "first_purchase_date" in features.columns and "last_purchase_date" in features.columns:
        metrics["date_span"] = {
            "min": str(features["first_purchase_date"].min()),
            "max": str(features["last_purchase_date"].max()),
        }

    return metrics


def save_feature_metrics(metrics: dict[str, Any], output_path: Path) -> Path:
    return write_json(metrics, output_path)


def build_feature_metrics_bundle(
    *,
    mode: str,
    source_dataset: str,
    source_sales: pd.DataFrame,
    tables: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    source_rows = len(source_sales)
    table_metrics = {
        table_name: build_feature_metrics(frame, mode=mode, source_rows=source_rows)
        for table_name, frame in tables.items()
    }

    return {
        "mode": mode,
        "source_dataset": source_dataset,
        "source_rows": source_rows,
        "table_count": len(tables),
        "table_metrics": table_metrics,
        "daily_incremental_features": {
            "status": "todo",
            "note": "Future support should only recompute impacted entities for daily runs.",
        },
        "feature_drift_monitoring": {
            "status": "todo",
            "note": "Add daily-vs-historical feature drift checks once daily feature outputs exist.",
        },
        "feature_store_support": {
            "status": "todo",
            "note": "Add export adapters for an external feature store when the serving layer is defined.",
        },
    }


def save_feature_metrics_bundle(metrics_bundle: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    metrics_path = output_dir / "feature_metrics.json"
    return {"feature_metrics": write_json(metrics_bundle, metrics_path)}

