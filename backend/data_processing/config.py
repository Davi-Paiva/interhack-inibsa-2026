from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


RunMode = Literal["historical", "daily"]


@dataclass(frozen=True)
class ProcessingConfig:
    raw_data_dir: Path = Path(__file__).resolve().parents[1] / "raw_data"
    processed_data_dir: Path = Path(__file__).resolve().parents[1] / "processed_data"
    metrics_dir_name: str = "metrics"
    historical_sales_file: str = "sales.csv"
    daily_sales_file: str = "sales.csv"
    clients_file: str = "clients.csv"
    products_file: str = "products.csv"
    campaigns_file: str = "campaigns.csv"
    potential_file: str = "potential.csv"
    date_format: str = "%m/%d/%Y"
    technical_block_name: str = "Productos Técnicos"
    parquet_compression: str = "snappy"

    def sales_file_for_mode(self, mode: RunMode) -> str:
        return self.historical_sales_file if mode == "historical" else self.daily_sales_file

    def output_dir_for_mode(self, mode: RunMode) -> Path:
        return self.processed_data_dir / mode

    def metrics_dir_for_mode(self, mode: RunMode) -> Path:
        return self.output_dir_for_mode(mode) / self.metrics_dir_name
