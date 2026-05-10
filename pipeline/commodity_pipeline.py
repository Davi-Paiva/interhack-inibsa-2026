from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import pandas as pd


def run_commodity_pipeline(
    features: dict[str, object],
    *,
    mode: str,
) -> pd.DataFrame:
    del features

    project_root = Path(__file__).resolve().parents[1]
    commodity_src = project_root / "backend" / "commodity-ai-engine" / "src"
    if str(commodity_src) not in sys.path:
        sys.path.insert(0, str(commodity_src))

    pipeline_module = import_module("commodity_engine_core.pipeline")

    artifacts = pipeline_module.run_model_evaluation(mode, project_root=project_root)

    output_path = artifacts["next_purchase_output"]
    return pd.read_parquet(output_path)
