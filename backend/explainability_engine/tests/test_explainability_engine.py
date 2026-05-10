from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from backend.explainability_engine.commodity_explainer import (
    explain_capture_frame,
    explain_leakage_frame,
    explain_next_purchase_frame,
)
from backend.explainability_engine.service import ExplainabilityService
from backend.explainability_engine.technical_explainer import explain_technical_payload


def test_explain_leakage_frame_builds_expected_record() -> None:
    df = pd.DataFrame(
        [
            {
                "customer_id": "C001",
                "product_id": "P001",
                "predicted_30d_sales": 120.0,
                "observed_30d_sales": 80.0,
                "gap_units": 40.0,
                "gap_ratio": 0.333,
                "volatility_penalty": 0.8,
                "campaign_softener": 0.9,
                "return_penalty": 0.95,
                "confidence_factor": 0.7,
                "leakage_score": 0.22,
                "risk_level": "medium",
                "is_actionable": True,
                "routing_reason": "commodity_actionable",
            }
        ]
    )
    records = explain_leakage_frame(df, source_artifact="demand_leakage_signals.parquet")
    assert len(records) == 1
    assert records[0].alert_variant == "commodity.demand_leakage"
    assert records[0].severity_label == "medium"
    assert "Expected next-30-day demand" in records[0].why_triggered_text


def test_explain_capture_frame_preserves_priority_labels() -> None:
    df = pd.DataFrame(
        [
            {
                "customer_id": "C001",
                "product_id": "P001",
                "capture_score": 42.0,
                "priority_rank": 1,
                "priority_band": "critical",
                "recommended_action": "Call within 24h",
                "leakage_component": 0.4,
                "value_component": 0.3,
                "urgency_component": 0.2,
                "confidence_component": 0.1,
            }
        ]
    )
    records = explain_capture_frame(df, source_artifact="capture_opportunities.parquet")
    assert records[0].severity_label == "critical"
    assert records[0].priority_label == "critical"
    assert "capture score" in records[0].why_triggered_text.lower()


def test_explain_next_purchase_frame_mentions_contact_window() -> None:
    df = pd.DataFrame(
        [
            {
                "customer_id": "C001",
                "product_id": "P001",
                "priority_band": "high",
                "estimated_interval_days": 30.0,
                "days_until_expected_purchase": 4,
                "expected_next_purchase_date": "2026-05-14",
                "purchase_probability": 0.73,
                "contact_window_start": "2026-05-12",
                "contact_window_end": "2026-05-13",
                "contact_recommendation": "Contact this week",
            }
        ]
    )
    records = explain_next_purchase_frame(df, source_artifact="next_purchase_predictions.parquet")
    assert "contact window" in records[0].temporal_summary_text.lower()
    assert records[0].priority_label == "high"


def test_explain_technical_payload_includes_drift_signals() -> None:
    payload = [
        {
            "client_id": "CL001",
            "product_id": "P001",
            "risk_score": 0.65,
            "priority_score": 1.2,
            "risk_level": "high",
            "priority_level": "critical",
            "inactivity_score": 0.7,
            "inactivity_ratio": 2.4,
            "expected_cycle_days": 15.0,
            "days_since_last_order": 36,
            "volume_drift_score": 0.5,
            "interval_drift_score": 0.8,
            "peer_drift_score": 0.3,
            "potential_gap": 2500.0,
            "drift_signal_count": 2,
            "drift_signals": [
                {"signal_type": "interval_drift", "severity": 0.8, "metric_value": 2.4, "threshold": 1.5},
                {"signal_type": "volume_drift", "severity": 0.5, "metric_value": 0.35, "threshold": 0.2},
            ],
        }
    ]
    records = explain_technical_payload(payload, source_artifact="technical_explanation_inputs.json")
    assert records[0].alert_variant == "technical.risk_assessment"
    assert any("interval_drift" in trace for trace in records[0].decision_trace)


def test_records_to_frame_serializes_nested_fields() -> None:
    payload = [
        {
            "client_id": "CL001",
            "product_id": "P001",
            "risk_score": 0.65,
            "priority_score": 1.2,
            "risk_level": "high",
            "priority_level": "critical",
            "inactivity_score": 0.7,
            "inactivity_ratio": 2.4,
            "expected_cycle_days": 15.0,
            "days_since_last_order": 36,
            "volume_drift_score": 0.5,
            "interval_drift_score": 0.8,
            "peer_drift_score": 0.3,
            "potential_gap": 2500.0,
            "drift_signal_count": 1,
            "drift_signals": [
                {"signal_type": "interval_drift", "severity": 0.8, "metric_value": 2.4, "threshold": 1.5}
            ],
        }
    ]
    service = ExplainabilityService(project_root=".")
    records = explain_technical_payload(payload, source_artifact="technical_explanation_inputs.json")
    frame = service._records_to_frame(records)
    assert isinstance(frame.loc[0, "contributing_factors"], str)
    assert isinstance(json.loads(frame.loc[0, "supporting_metrics"]), dict)


def test_technical_output_dir_is_mode_specific(tmp_path: Path) -> None:
    service = ExplainabilityService(project_root=tmp_path)
    assert service.technical_output_dir("daily") == (
        tmp_path / "backend" / "technical_product_engine" / "output" / "daily"
    )
