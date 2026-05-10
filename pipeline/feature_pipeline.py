from __future__ import annotations

import pandas as pd
from dataclasses import replace
from pathlib import Path

from backend.data_processing.cleaning import run_cleaning_pipeline
from backend.data_processing.config import ProcessingConfig
from backend.feature_engineering.config import FeatureConfig
from backend.feature_engineering.features import run_feature_pipeline as run_backend_feature_pipeline


def run_feature_pipeline(
    raw_data: dict[str, pd.DataFrame],
    *,
    data_dir: str,
    mode: str,
) -> dict[str, Path]:
    del raw_data

    project_root = Path(__file__).resolve().parents[1]
    processed_data_dir = project_root / "backend" / "processed_data"
    processing_config = replace(
        ProcessingConfig(),
        raw_data_dir=Path(data_dir).resolve(),
        processed_data_dir=processed_data_dir,
    )
    run_cleaning_pipeline(mode=mode, config=processing_config)
    return run_backend_feature_pipeline(
        mode=mode,
        config=FeatureConfig(
            processed_data_dir=processed_data_dir,
            raw_data_dir=Path(data_dir).resolve(),
        ),
    )
