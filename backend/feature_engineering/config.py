from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


RunMode = Literal["historical", "daily"]


@dataclass(frozen=True)
class FeatureConfig:
    processed_data_dir: Path = Path(__file__).resolve().parents[1] / "processed_data"
    raw_data_dir: Path = Path(__file__).resolve().parents[1] / "raw_data"
    artifacts_root_dir: Path = Path(__file__).resolve().parent / "artifacts"
    source_dataset_name: str = "sales_enriched.csv"
    group_by_columns: tuple[str, ...] = ("client_id", "family")
    rolling_windows_days: tuple[int, ...] = (30, 90)
    trend_window_days: int = 90

    def input_dir_for_mode(self, mode: RunMode) -> Path:
        return self.processed_data_dir / mode

    def features_dir_for_mode(self, mode: RunMode) -> Path:
        return self.input_dir_for_mode(mode)

    def state_dir_for_mode(self, mode: RunMode) -> Path:
        return self.artifacts_root_dir / "state" / mode

    def delta_dir_for_mode(self, mode: RunMode) -> Path:
        return self.artifacts_root_dir / "delta" / mode
