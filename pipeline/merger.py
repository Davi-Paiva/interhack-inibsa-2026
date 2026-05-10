from __future__ import annotations

from typing import Any
from pathlib import Path

import pandas as pd


def merge_engine_outputs(
    commodity_results: pd.DataFrame | list[Any],
    technical_results: pd.DataFrame | list[Any],
    *,
    mode: str,
) -> pd.DataFrame | list[Any]:
    del commodity_results
    del technical_results

    from backend.global_prioritization.service import GlobalPrioritizationService

    project_root = Path(__file__).resolve().parents[1]
    service = GlobalPrioritizationService(project_root=project_root)
    full_queue = service.build_full_queue(mode)
    queue = full_queue if mode != "daily" else service._filter_new_daily_alerts(
        full_queue,
        previous_full_queue=service._load_previous_daily_full_queue(mode),
    )
    service.persist_queue(queue, mode, full_queue=full_queue)
    return queue
