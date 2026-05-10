from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from backend.global_prioritization.service import GlobalPrioritizationService


def test_commodity_rows_are_consolidated_with_next_purchase_precedence(tmp_path: Path) -> None:
    service = GlobalPrioritizationService(project_root=tmp_path)
    explanation_map = {
        "commodity.demand_leakage|C001|P001": ["exp_l"],
        "commodity.capture_opportunity|C001|P001": ["exp_c"],
        "commodity.next_purchase|C001|P001": ["exp_n"],
    }
    rows = [
        {"canonical_variant": "commodity.demand_leakage", "customer_id": "C001", "product_id": "P001", "severity_label": "high", "leakage_score": 0.3, "is_actionable": True, "route_to_engine": "commodity_ai_engine"},
        {"canonical_variant": "commodity.capture_opportunity", "customer_id": "C001", "product_id": "P001", "priority_label": "high", "capture_score": 35.0, "recommended_action": "Follow up"},
        {"canonical_variant": "commodity.next_purchase", "customer_id": "C001", "product_id": "P001", "priority_label": "critical", "capture_score": 35.0, "purchase_probability": 0.8, "contact_window_start": "2026-05-10", "recommended_action": "Contact today"},
    ]

    consolidated = service._consolidate_commodity_rows(
        rows,
        reference_date=pd.Timestamp("2026-05-10"),
        explanation_map=explanation_map,
    )

    assert len(consolidated) == 1
    assert consolidated[0]["canonical_variant"] == "commodity.next_purchase"
    assert consolidated[0]["source_variants"] == [
        "commodity.next_purchase",
        "commodity.capture_opportunity",
        "commodity.demand_leakage",
    ]
    assert consolidated[0]["explanation_ids"] == ["exp_n", "exp_c", "exp_l"]


def test_commodity_merge_backfills_capture_score_into_next_purchase(tmp_path: Path) -> None:
    service = GlobalPrioritizationService(project_root=tmp_path)
    rows = [
        {
            "canonical_variant": "commodity.capture_opportunity",
            "customer_id": "C001",
            "product_id": "P001",
            "capture_score": 35.0,
            "priority_label": "high",
            "recommended_action": "Follow up",
        },
        {
            "canonical_variant": "commodity.next_purchase",
            "customer_id": "C001",
            "product_id": "P001",
            "priority_label": "critical",
            "purchase_probability": 0.8,
            "contact_window_start": "2026-05-10",
            "recommended_action": "Contact today",
        },
    ]

    consolidated = service._consolidate_commodity_rows(
        rows,
        reference_date=pd.Timestamp("2026-05-10"),
        explanation_map={},
    )

    assert len(consolidated) == 1
    assert consolidated[0]["canonical_variant"] == "commodity.next_purchase"
    assert consolidated[0]["capture_score"] == 35.0
    assert consolidated[0]["global_priority_score"] == 56.0
    assert consolidated[0]["global_priority_band"] == "medium"


def test_technical_process_date_defaults_to_priority_window(tmp_path: Path) -> None:
    service = GlobalPrioritizationService(project_root=tmp_path)
    reference = pd.Timestamp("2026-05-10")
    row = {
        "priority_level": "medium",
        "inactivity_ratio": 3.2,
        "drift_signal_count": 2,
    }
    process_on_date = service._technical_process_date(row, reference_date=reference)
    assert process_on_date == reference
    assert service._bucket_for_date(process_on_date, reference) == "today"


def test_technical_rows_keep_source_priority_band(tmp_path: Path) -> None:
    service = GlobalPrioritizationService(project_root=tmp_path)
    rows = [
        {
            "client_id": "C002",
            "product_id": "P002",
            "risk_level": "critical",
            "priority_level": "critical",
            "priority_score": 6.0,
            "inactivity_ratio": 4.0,
            "drift_signal_count": 1,
        }
    ]

    built = service._build_technical_rows(
        rows,
        reference_date=pd.Timestamp("2026-05-10"),
        explanation_map={},
    )

    assert built[0]["global_priority_score"] == 45.0
    assert built[0]["global_priority_band"] == "critical"


def test_ranking_sorts_by_process_date_then_score(tmp_path: Path) -> None:
    service = GlobalPrioritizationService(project_root=tmp_path)
    rows = [
        {
            "global_alert_id": "a1",
            "source_engine": "commodity_ai_engine",
            "canonical_variant": "commodity.capture_opportunity",
            "source_variants": ["commodity.capture_opportunity"],
            "customer_id": "C001",
            "product_id": "P001",
            "severity_label": "high",
            "priority_label": "high",
            "global_priority_score": 55.0,
            "global_priority_band": "medium",
            "process_on_date": pd.Timestamp("2026-05-10"),
            "process_day_bucket": "today",
            "recommended_action": "Later",
            "explanation_ids": [],
            "source_row_keys": [],
        },
        {
            "global_alert_id": "a2",
            "source_engine": "technical_product_engine",
            "canonical_variant": "technical.risk_assessment",
            "source_variants": ["technical.risk_assessment"],
            "customer_id": "C002",
            "product_id": "P002",
            "severity_label": "critical",
            "priority_label": "critical",
            "global_priority_score": 65.0,
            "global_priority_band": "critical",
            "process_on_date": pd.Timestamp("2026-05-12"),
            "process_day_bucket": "this_week",
            "recommended_action": "Now",
            "explanation_ids": [],
            "source_row_keys": [],
        },
    ]
    ranked = service._rank_queue_rows(rows, reference_date=pd.Timestamp("2026-05-10"))
    assert ranked[0].global_alert_id == "a2"
    assert ranked[0].queue_rank == 1
    assert ranked[1].queue_rank == 2


def test_records_frame_serializes_list_fields(tmp_path: Path) -> None:
    service = GlobalPrioritizationService(project_root=tmp_path)
    rows = [
        {
            "global_alert_id": "a2",
            "source_engine": "technical_product_engine",
            "canonical_variant": "technical.risk_assessment",
            "source_variants": ["technical.risk_assessment"],
            "customer_id": "C002",
            "product_id": "P002",
            "severity_label": "critical",
            "priority_label": "critical",
            "global_priority_score": 90.0,
            "global_priority_band": "critical",
            "process_on_date": pd.Timestamp("2026-05-10"),
            "process_day_bucket": "today",
            "recommended_action": "Now",
            "explanation_ids": ["exp_1"],
            "source_row_keys": ["technical.risk_assessment|C002|P002"],
        }
    ]
    ranked = service._rank_queue_rows(rows, reference_date=pd.Timestamp("2026-05-10"))
    frame = service._records_to_frame(ranked)
    assert isinstance(frame.loc[0, "source_variants"], str)
    assert json.loads(frame.loc[0, "explanation_ids"]) == ["exp_1"]


def test_technical_output_dir_is_mode_specific(tmp_path: Path) -> None:
    service = GlobalPrioritizationService(project_root=tmp_path)
    assert service.technical_output_dir("daily") == (
        tmp_path / "backend" / "technical_product_engine" / "output" / "daily"
    )


def test_technical_candidates_filter_to_urgent_critical_rows(tmp_path: Path) -> None:
    service = GlobalPrioritizationService(project_root=tmp_path)
    rows = [
        {
            "source_engine": "technical_product_engine",
            "canonical_variant": "technical.risk_assessment",
            "source_variants": ["technical.risk_assessment"],
            "customer_id": "T1",
            "product_id": "P1",
            "severity_label": "high",
            "priority_label": "critical",
            "global_priority_score": 62.0,
            "global_priority_band": "critical",
            "process_on_date": pd.Timestamp("2026-05-10"),
            "process_day_bucket": "today",
            "recommended_action": "Now",
            "explanation_ids": [],
            "source_row_keys": [],
        },
        {
            "source_engine": "technical_product_engine",
            "canonical_variant": "technical.risk_assessment",
            "source_variants": ["technical.risk_assessment"],
            "customer_id": "T2",
            "product_id": "P2",
            "severity_label": "high",
            "priority_label": "high",
            "global_priority_score": 51.0,
            "global_priority_band": "high",
            "process_on_date": pd.Timestamp("2026-05-11"),
            "process_day_bucket": "tomorrow",
            "recommended_action": "Technical",
            "explanation_ids": [],
            "source_row_keys": [],
        },
        {
            "source_engine": "technical_product_engine",
            "canonical_variant": "technical.risk_assessment",
            "source_variants": ["technical.risk_assessment"],
            "customer_id": "T3",
            "product_id": "P3",
            "severity_label": "medium",
            "priority_label": "medium",
            "global_priority_score": 44.0,
            "global_priority_band": "medium",
            "process_on_date": pd.Timestamp("2026-05-12"),
            "process_day_bucket": "this_week",
            "recommended_action": "Monitor",
            "explanation_ids": [],
            "source_row_keys": [],
        },
        {
            "source_engine": "technical_product_engine",
            "canonical_variant": "technical.risk_assessment",
            "source_variants": ["technical.risk_assessment"],
            "customer_id": "T4",
            "product_id": "P4",
            "severity_label": "critical",
            "priority_label": "critical",
            "global_priority_score": 63.0,
            "global_priority_band": "critical",
            "process_on_date": pd.Timestamp("2026-05-20"),
            "process_day_bucket": "later",
            "recommended_action": "Later",
            "explanation_ids": [],
            "source_row_keys": [],
        },
    ]

    selected = service._select_technical_candidates(rows)

    assert [(row["customer_id"], row["product_id"]) for row in selected] == [("T1", "P1")]
