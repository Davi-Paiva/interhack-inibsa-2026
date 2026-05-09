from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


RunMode = Literal["historical", "daily"]


@dataclass(frozen=True)
class FeatureConfig:
    processed_data_dir: Path = Path(__file__).resolve().parents[1] / "processed_data"
    features_dir_name: str = "features"
    metrics_dir_name: str = "metrics"
    source_dataset_name: str = "sales_enriched.parquet"
    output_dataset_name: str = "commodity_features.parquet"
    parquet_compression: str = "snappy"
    group_by_columns: tuple[str, ...] = ("client_id", "family")
    rolling_windows_days: tuple[int, ...] = (30, 90)
    trend_window_days: int = 90

    def input_dir_for_mode(self, mode: RunMode) -> Path:
        return self.processed_data_dir / mode

    def features_dir_for_mode(self, mode: RunMode) -> Path:
        return self.input_dir_for_mode(mode) / self.features_dir_name

    def metrics_dir_for_mode(self, mode: RunMode) -> Path:
        return self.features_dir_for_mode(mode) / self.metrics_dir_name
