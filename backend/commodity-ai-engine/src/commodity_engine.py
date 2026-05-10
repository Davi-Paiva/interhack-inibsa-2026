"""Commodity AI Engine public entrypoint."""

from __future__ import annotations

import argparse

from commodity_engine_core import (
    CaptureScoringEngine,
    CommodityCustomerCluster,
    CommoditySignal,
    CommoditySignalGenerator,
    CustomerCluster,
    DemandForecaster,
    DemandLeakageDetector,
    NextPurchasePredictor,
    build_historical_training_panel,
    run_capture_scoring,
    run_consumption_forecast,
    run_customer_clustering,
    run_demand_leakage,
    run_model_evaluation,
    run_next_purchase_prediction,
)
from commodity_engine_core.common import logger

__all__ = [
    "CaptureScoringEngine",
    "CommodityCustomerCluster",
    "CommoditySignal",
    "CommoditySignalGenerator",
    "CustomerCluster",
    "DemandForecaster",
    "DemandLeakageDetector",
    "NextPurchasePredictor",
    "build_historical_training_panel",
    "run_capture_scoring",
    "run_consumption_forecast",
    "run_customer_clustering",
    "run_demand_leakage",
    "run_model_evaluation",
    "run_next_purchase_prediction",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the commodity AI engine components")
    parser.add_argument(
        "--mode",
        default="historical",
        choices=("historical", "daily"),
        help="Input/output mode for the commodity pipeline",
    )
    parser.add_argument(
        "--task",
        default="forecast",
        choices=("clustering", "forecast", "evaluation", "leakage", "capture", "next_purchase"),
        help="Commodity task to execute",
    )
    args = parser.parse_args()

    if args.task == "clustering":
        output_path = run_customer_clustering(args.mode)
        logger.info("Customer clustering completed: %s", output_path)
    elif args.task == "evaluation":
        artifacts = run_model_evaluation(args.mode)
        logger.info("Commodity evaluation completed: %s", artifacts)
    elif args.task == "leakage":
        artifacts = run_demand_leakage(args.mode)
        logger.info("Demand leakage completed: %s", artifacts)
    elif args.task == "capture":
        artifacts = run_capture_scoring(args.mode)
        logger.info("Capture opportunity scoring completed: %s", artifacts)
    elif args.task == "next_purchase":
        artifacts = run_next_purchase_prediction(args.mode)
        logger.info("Next purchase prediction completed: %s", artifacts)
    else:
        output_path = run_consumption_forecast(args.mode)
        logger.info("Consumption forecast completed: %s", output_path)


if __name__ == "__main__":
    main()
