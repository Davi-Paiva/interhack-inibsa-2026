from __future__ import annotations

from pathlib import Path

import pandas as pd


def run_technical_pipeline(features: dict[str, pd.DataFrame]) -> pd.DataFrame:
    del features

    from backend.technical_product_engine.main import main as run_technical_engine

    run_technical_engine()
    output_path = (
        Path(__file__).resolve().parents[1]
        / "backend"
        / "technical_product_engine"
        / "output"
        / "technical_risk_assessments.csv"
    )
    return pd.read_csv(output_path)
