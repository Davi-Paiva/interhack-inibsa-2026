from __future__ import annotations

from pathlib import Path

import pandas as pd


def run_technical_pipeline(
    features: dict[str, object],
    *,
    mode: str,
) -> pd.DataFrame:
    del features

    from backend.technical_product_engine.main import main as run_technical_engine

    project_root = Path(__file__).resolve().parents[1]
    run_technical_engine(
        mode=mode,
        processed_data_dir=project_root / "backend" / "processed_data",
        output_dir=project_root / "backend" / "technical_product_engine" / "output",
    )
    output_path = (
        project_root
        / "backend"
        / "technical_product_engine"
        / "output"
        / mode
        / "technical_risk_assessments.csv"
    )
    return pd.read_csv(output_path)
