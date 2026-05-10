from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd

from backend.feature_engineering.config import FeatureConfig
from backend.feature_engineering.features import (
    CLIENT_FEATURE_COLUMNS,
    CLIENT_PRODUCT_FEATURE_COLUMNS,
    PRODUCT_FEATURE_COLUMNS,
    align_feature_tables_to_contract,
    compute_daily_feature_delta,
    persist_feature_state,
)


def _aligned_frames(payload: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    frames, _ = align_feature_tables_to_contract(payload)
    return frames


def test_daily_feature_delta_uses_persisted_state(tmp_path: Path) -> None:
    config = replace(FeatureConfig(), artifacts_root_dir=tmp_path / "artifacts")

    initial_frames = _aligned_frames(
        {
            "client_features": pd.DataFrame(
                [
                    {"client_id": "C001", "customer_total_revenue": 100.0},
                ],
                columns=CLIENT_FEATURE_COLUMNS,
            ),
            "product_features": pd.DataFrame(
                [
                    {"product_id": "P001", "product_total_revenue": 200.0},
                ],
                columns=PRODUCT_FEATURE_COLUMNS,
            ),
            "client_product_features": pd.DataFrame(
                [
                    {"client_id": "C001", "product_id": "P001", "rolling_sales_30d": 50.0},
                ],
                columns=CLIENT_PRODUCT_FEATURE_COLUMNS,
            ),
        }
    )

    changed_frames, removed_keys, manifest = compute_daily_feature_delta(
        initial_frames,
        mode="daily",
        config=config,
        source_rows=1,
        snapshot_date=pd.Timestamp("2026-01-28"),
    )
    assert len(changed_frames["client_features"]) == 1
    assert manifest["tables"]["client_features"]["previous_rows"] == 0
    persist_feature_state(initial_frames, manifest, mode="daily", config=config)

    next_frames = _aligned_frames(
        {
            "client_features": pd.DataFrame(
                [
                    {"client_id": "C001", "customer_total_revenue": 150.0},
                    {"client_id": "C002", "customer_total_revenue": 80.0},
                ],
                columns=CLIENT_FEATURE_COLUMNS,
            ),
            "product_features": pd.DataFrame(
                [
                    {"product_id": "P001", "product_total_revenue": 200.0},
                ],
                columns=PRODUCT_FEATURE_COLUMNS,
            ),
            "client_product_features": pd.DataFrame(
                [
                    {"client_id": "C001", "product_id": "P001", "rolling_sales_30d": 55.0},
                ],
                columns=CLIENT_PRODUCT_FEATURE_COLUMNS,
            ),
        }
    )

    changed_frames, removed_keys, manifest = compute_daily_feature_delta(
        next_frames,
        mode="daily",
        config=config,
        source_rows=2,
        snapshot_date=pd.Timestamp("2026-01-29"),
    )

    assert set(changed_frames["client_features"]["client_id"].tolist()) == {"C001", "C002"}
    assert manifest["tables"]["client_features"]["changed_rows"] == 2
    assert manifest["tables"]["product_features"]["changed_rows"] == 0
    assert manifest["tables"]["client_product_features"]["changed_rows"] == 1
    assert removed_keys["product_features"].empty
