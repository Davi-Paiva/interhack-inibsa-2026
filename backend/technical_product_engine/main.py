"""
Main entry point for the technical product engine.

This module orchestrates the complete technical product risk analysis pipeline,
from data loading through risk assessment and final output generation.
"""
from __future__ import annotations

import argparse
import csv
import json
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the technical product engine.")
    parser.add_argument(
        "--mode",
        choices=("historical", "daily"),
        default="historical",
        help="Pipeline mode to read/write processed and engine artifacts.",
    )
    parser.add_argument(
        "--processed-data-dir",
        type=Path,
        default=None,
        help="Optional override for the processed data root directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional override for the technical output root directory.",
    )
    return parser


def export_assessments_to_csv(assessments, output_path: Path):
    """Export technical risk assessments to CSV file.
    
    Args:
        assessments: List of TechnicalRiskAssessment objects
        output_path: Path to output CSV file
    """
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Exporting {len(assessments)} assessments to {output_path}")
    
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
        'peer_avg_growth',
        'peer_avg_similarity',
        'peer_group_type',
        'client_product_embedding_cosine',
        'client_product_preference_gap',
    ]
    
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for assessment in assessments:
            writer.writerow({field: getattr(assessment, field) for field in fieldnames})
    
    logger.info(f"Export complete: {output_path}")


def export_explanation_inputs_to_json(assessments, output_path: Path):
    """Export technical explanation inputs with drift-signal detail."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(assessment) for assessment in assessments]
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    logger.info("Exported %s technical explanation inputs to %s", len(payload), output_path)


def _persist_empty_outputs(output_file: Path, explanation_input_file: Path) -> None:
    export_assessments_to_csv([], output_file)
    export_explanation_inputs_to_json([], explanation_input_file)


def main(
    mode: str = "historical",
    *,
    processed_data_dir: Path | None = None,
    output_dir: Path | None = None,
):
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
    data_root = processed_data_dir.resolve() if processed_data_dir is not None else (base_dir / "processed_data")
    technical_output_root = output_dir.resolve() if output_dir is not None else (base_dir / "technical_product_engine" / "output")
    data_dir = data_root / mode
    output_dir = technical_output_root / mode
    output_file = output_dir / "technical_risk_assessments.csv"
    explanation_input_file = output_dir / "technical_explanation_inputs.json"
    
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
        logger.warning("No contexts generated. Writing empty technical outputs for '%s' mode.", mode)
        _persist_empty_outputs(output_file, explanation_input_file)
        try:
            from backend.explainability_engine.service import generate_technical_explanations

            generate_technical_explanations(mode, project_root=base_dir.parent)
        except Exception as exc:
            logger.warning("Explainability generation failed for empty technical run: %s", exc)
        return aggregator, [], []
    
    logger.info(f"Built {len(contexts)} client-product contexts for analysis")
    
    # Step 2.5: Compute peer metrics for drift detection
    logger.info("Step 2.5: Computing peer metrics...")
    peer_metrics_map = aggregator.compute_peer_metrics(contexts)
    
    # Step 3: Initialize engine and run analysis
    logger.info("Step 3: Running risk analysis...")
    engine = TechnicalProductEngine()
    assessments = engine.analyze_batch(contexts, peer_metrics_map=peer_metrics_map)
    
    if not assessments:
        logger.warning("No assessments generated. Writing empty technical outputs for '%s' mode.", mode)
        _persist_empty_outputs(output_file, explanation_input_file)
        try:
            from backend.explainability_engine.service import generate_technical_explanations

            generate_technical_explanations(mode, project_root=base_dir.parent)
        except Exception as exc:
            logger.warning("Explainability generation failed for empty technical run: %s", exc)
        return aggregator, contexts, []
    
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
    export_explanation_inputs_to_json(assessments, explanation_input_file)
    
    # Step 6: Export high-risk subset
    high_risk = engine.get_high_risk_relationships(assessments, min_risk_level="high")
    if high_risk:
        high_risk_file = output_dir / "high_risk_relationships.csv"
        export_assessments_to_csv(high_risk, high_risk_file)
        logger.info(f"Exported {len(high_risk)} high-risk relationships to {high_risk_file}")

    try:
        from backend.explainability_engine.service import generate_technical_explanations

        generate_technical_explanations(mode, project_root=base_dir.parent)
    except Exception as exc:
        logger.warning("Explainability generation failed for technical engine: %s", exc)
    
    logger.info("=" * 70)
    logger.info("TECHNICAL PRODUCT ENGINE - COMPLETE")
    logger.info("=" * 70)
    
    return aggregator, contexts, assessments


if __name__ == "__main__":
    args = _build_parser().parse_args()
    main(
        mode=args.mode,
        processed_data_dir=args.processed_data_dir,
        output_dir=args.output_dir,
    )
