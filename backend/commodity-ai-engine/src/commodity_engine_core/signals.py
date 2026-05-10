from __future__ import annotations

from .common import *
from .capture import CaptureScoringEngine
from .leakage import DemandLeakageDetector

class CommoditySignalGenerator:
    """
    Legacy orchestration wrapper.

    The production path for clustering and forecasting now lives in
    `run_customer_clustering()` and `run_model_evaluation()`.
    """

    def __init__(self, sales_df: pd.DataFrame, clients_df: pd.DataFrame, products_df: pd.DataFrame):
        self.sales_df = sales_df
        self.clients_df = clients_df
        self.products_df = products_df
        self.leakage_detector = DemandLeakageDetector()
        self.scorer = CaptureScoringEngine()

    def generate_signals(self) -> List[CommoditySignal]:
        raise NotImplementedError(
            "CommoditySignalGenerator is not wired to the new historical evaluation path yet. "
            "Use run_customer_clustering() and run_model_evaluation() instead."
        )

    def export_signals(self, signals: List[CommoditySignal], output_path: str) -> None:
        data = [asdict(signal) for signal in signals]
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        logger.info("Exported %s signals to %s", len(signals), output_path)


