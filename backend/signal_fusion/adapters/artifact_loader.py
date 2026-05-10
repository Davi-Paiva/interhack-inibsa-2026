from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ..domain.structures import FusionTables


@dataclass(frozen=True)
class ArtifactPaths:
    project_root: Path
    mode: str = "historical"

    @property
    def processed_dir(self) -> Path:
        return self.project_root / "backend" / "processed_data" / self.mode

    @property
    def commodity_output_dir(self) -> Path:
        return self.project_root / "backend" / "commodity-ai-engine" / "output" / self.mode

    @property
    def technical_output_dir(self) -> Path:
        return self.project_root / "backend" / "technical_product_engine" / "output"


class SignalFusionLoader:
    def __init__(self, paths: ArtifactPaths) -> None:
        self.paths = paths

    def load(self) -> FusionTables:
        return FusionTables(
            clients=self._read_csv(self.paths.processed_dir / "clients.csv"),
            products=self._read_csv(self.paths.processed_dir / "products.csv"),
            potential=self._read_csv(self.paths.processed_dir / "potential.csv"),
            client_product_features=self._read_csv(
                self.paths.processed_dir / "client_product_features.csv"
            ),
            commodity_forecast=self._read_parquet(
                self.paths.commodity_output_dir / "consumption_forecast.parquet"
            ),
            demand_leakage=self._read_parquet(
                self.paths.commodity_output_dir / "demand_leakage_signals.parquet"
            ),
            capture_opportunities=self._read_parquet(
                self.paths.commodity_output_dir / "capture_opportunities.parquet"
            ),
            next_purchase=self._read_parquet(
                self.paths.commodity_output_dir / "next_purchase_predictions.parquet"
            ),
            technical_risk=self._read_csv(
                self.paths.technical_output_dir / "technical_risk_assessments.csv"
            ),
        )

    @staticmethod
    def _read_csv(path: Path) -> pd.DataFrame | None:
        if not path.exists():
            return None
        return _normalize_ids(pd.read_csv(path, low_memory=False))

    @staticmethod
    def _read_parquet(path: Path) -> pd.DataFrame | None:
        if not path.exists():
            return None
        try:
            return _normalize_ids(pd.read_parquet(path))
        except ImportError as exc:
            raise ImportError(
                "Reading signal fusion parquet inputs requires pyarrow or fastparquet. "
                "Run with the project virtualenv or install one parquet engine."
            ) from exc


def _normalize_ids(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for column in ("client_id", "customer_id", "product_id", "family", "product_family"):
        if column in normalized.columns:
            normalized[column] = normalized[column].astype("string").str.strip()
    return normalized
