"""
Main entry point for the technical product engine.

This module orchestrates the complete technical product risk analysis pipeline,
from data loading through risk assessment and final output generation.
"""
import csv
import logging
from pathlib import Path
from dataclasses import asdict

from .services import DataAggregator, TechnicalProductEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration: Which analytic block to analyze
ANALYTIC_BLOCK = "Productos Técnicos"


def export_assessments_to_csv(assessments, output_path: Path):
    """Export technical risk assessments to CSV file.
    
    Args:
        assessments: List of TechnicalRiskAssessment objects
        output_path: Path to output CSV file
    """
    if not assessments:
        logger.warning("No assessments to export")
        return
    
    logger.info(f"Exporting {len(assessments)} assessments to {output_path}")
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert assessments to dictionaries
    fieldnames = [
        'client_id',
        'product_id',
        'risk_score',
        'priority_score',
        'risk_level',
        'priority_level',
        'inactivity_score',
        'inactivity_ratio',
        'expected_cycle_days',
        'days_since_last_order',
        'is_inactive',
        'volume_drift_score',
        'interval_drift_score',
        'peer_drift_score',
        'potential_gap',
        'drift_signal_count',
    ]
    
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for assessment in assessments:
            writer.writerow(asdict(assessment))
    
    logger.info(f"Export complete: {output_path}")


def main():
    """Main entry point for the technical product engine.
    
    Orchestrates the complete pipeline:
    1. Load data
    2. Build analytical contexts
    3. Run risk analysis
    4. Export results
    """
    logger.info("=" * 70)
    logger.info("TECHNICAL PRODUCT ENGINE - STARTING")
    logger.info("=" * 70)
    
    # Define paths
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "processed_data" / "historical"
    output_dir = base_dir / "technical_product_engine" / "output"
    output_file = output_dir / "technical_risk_assessments.csv"
    
    # Step 1: Load data
    logger.info("Step 1: Loading data...")
    aggregator = DataAggregator(data_dir)
    aggregator.load_all_data()
    
    # Step 2: Build analytical contexts (technical products only)
    logger.info(f"Step 2: Building analytical contexts for '{ANALYTIC_BLOCK}' products...")
    contexts = aggregator.build_client_product_contexts(
        technical_only=True,
        analytic_block=ANALYTIC_BLOCK
    )
    
    if not contexts:
        logger.error("No contexts generated. Exiting.")
        return
    
    logger.info(f"Built {len(contexts)} client-product contexts for analysis")
    
    # Step 2.5: Compute peer metrics for drift detection
    logger.info("Step 2.5: Computing peer metrics...")
    peer_metrics_map = aggregator.compute_peer_metrics(contexts)
    
    # Step 3: Initialize engine and run analysis
    logger.info("Step 3: Running risk analysis...")
    engine = TechnicalProductEngine()
    assessments = engine.analyze_batch(contexts, peer_metrics_map=peer_metrics_map)
    
    if not assessments:
        logger.error("No assessments generated. Exiting.")
        return
    
    # Step 4: Generate summary statistics
    logger.info("Step 4: Generating summary statistics...")
    summary = engine.get_summary_statistics(assessments)
    
    logger.info("=" * 70)
    logger.info("ANALYSIS SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total relationships analyzed: {summary['total_relationships']:,}")
    logger.info(f"Average risk score: {summary['avg_risk_score']:.3f}")
    logger.info(f"Average priority score: {summary['avg_priority_score']:.3f}")
    logger.info(f"Inactive relationships: {summary['inactive_count']:,} ({summary['inactive_percentage']:.1f}%)")
    logger.info(f"Average drift signals per relationship: {summary['avg_drift_signals']:.2f}")
    logger.info("")
    logger.info("Risk Level Distribution:")
    for level in ['low', 'medium', 'high', 'critical']:
        count = summary['risk_level_counts'].get(level, 0)
        pct = (count / summary['total_relationships']) * 100 if summary['total_relationships'] > 0 else 0
        logger.info(f"  {level.capitalize():8s}: {count:5,} ({pct:5.1f}%)")
    logger.info("=" * 70)
    
    # Step 5: Export results
    logger.info("Step 5: Exporting results...")
    export_assessments_to_csv(assessments, output_file)
    
    # Step 6: Export high-risk subset
    high_risk = engine.get_high_risk_relationships(assessments, min_risk_level="high")
    if high_risk:
        high_risk_file = output_dir / "high_risk_relationships.csv"
        export_assessments_to_csv(high_risk, high_risk_file)
        logger.info(f"Exported {len(high_risk)} high-risk relationships to {high_risk_file}")
    
    logger.info("=" * 70)
    logger.info("TECHNICAL PRODUCT ENGINE - COMPLETE")
    logger.info("=" * 70)
    
    return aggregator, contexts, assessments


if __name__ == "__main__":
    main()
