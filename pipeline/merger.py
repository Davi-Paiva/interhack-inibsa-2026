from __future__ import annotations

from typing import Any

import pandas as pd


def merge_engine_outputs(
    commodity_results: pd.DataFrame | list[Any],
    technical_results: pd.DataFrame | list[Any],
) -> pd.DataFrame | list[Any]:
    if isinstance(commodity_results, pd.DataFrame) and isinstance(technical_results, pd.DataFrame):
        return pd.concat([commodity_results, technical_results], ignore_index=True)

    if isinstance(commodity_results, list) and isinstance(technical_results, list):
        return commodity_results + technical_results

    return commodity_results + technical_results
