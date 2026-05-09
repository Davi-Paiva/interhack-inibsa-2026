"""
Main entry point for the technical product engine.

This module serves as the primary entry point for running
the technical product engine and coordinating all components.
"""
import logging
from pathlib import Path

from .services import DataAggregator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the application."""
    # Define the data directory path
    # Adjust this path based on where your processed CSV files will be located
    data_dir = Path(__file__).parent.parent / "processed_data"
    
    # Alternative: use raw_data for testing
    # data_dir = Path(__file__).parent.parent / "raw_data"
    
    logger.info(f"Initializing Technical Product Engine with data directory: {data_dir}")
    
    # Create data aggregator and load all data
    aggregator = DataAggregator(data_dir)
    aggregator.load_all_data()
    
    # Build unified contexts for technical products
    contexts = aggregator.build_client_product_contexts(technical_only=True)
    
    logger.info(f"Ready to process {len(contexts)} client-product contexts")
    
    # TODO: Add additional processing logic here
    # Now you can pass contexts to downstream functions:
    # - Feature engineering
    # - Risk scoring
    # - Drift detection
    # - Inactivity analysis
    #
    # Example: process_risk_scoring(contexts)
    # Example: detect_drift(contexts)
    
    return aggregator, contexts


if __name__ == "__main__":
    main()
