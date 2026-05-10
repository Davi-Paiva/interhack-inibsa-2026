from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from backend.delegate_feedback.service import DelegateFeedbackService
from backend.global_prioritization.service import GlobalPrioritizationService


def _alert_row() -> dict[str, object]:
    return {
        "global_alert_id": "gq_demo",
        "source_engine": "technical_product_engine",
        "canonical_variant": "technical.risk_assessment",
        "customer_id": "C001",
        "product_id": "P001",
        "global_priority_score": 72.0,
        "global_priority_band": "high",
        "recommended_action": "Review within one day.",
        "alert_reason_summary": "Salta por inactividad, alargamiento del ciclo y peor comportamiento frente a pares.",
    }


def test_record_feedback_persists_json_csv_and_policy(tmp_path: Path) -> None:
    service = DelegateFeedbackService(project_root=tmp_path)
    paths = service.record_feedback(
        "daily",
        _alert_row(),
        delegate_id="delegate-1",
        resolution_status="contactado",
        alert_validity="correcta",
        action_taken="llamada",
        business_outcome="pedido_generado",
        root_cause="abandono_real",
        free_note="Cliente recuperado.",
        rebuild_policy=True,
    )

    assert paths["json"].exists()
    assert paths["csv"].exists()
    assert paths["policy"].exists()

    rows = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert len(rows) == 1
    assert rows[0]["delegate_id"] == "delegate-1"

    policy = json.loads(paths["policy"].read_text(encoding="utf-8"))
    assert policy["by_variant"]["technical.risk_assessment"]["top_business_outcome"] == "pedido_generado"


def test_feedback_adjustment_pushes_repeated_false_positives_down(tmp_path: Path) -> None:
    feedback_service = DelegateFeedbackService(project_root=tmp_path)
    alert_row = {
        "global_alert_id": "gq_repeat",
        "source_engine": "technical_product_engine",
        "canonical_variant": "technical.risk_assessment",
        "customer_id": "C001",
        "product_id": "P001",
        "global_priority_score": 80.0,
        "global_priority_band": "high",
        "recommended_action": "Review within one day.",
        "alert_reason_summary": "Salta por inactividad y drift.",
    }
    for day in ("2026-05-01T10:00:00", "2026-05-05T10:00:00"):
        feedback_service.record_feedback(
            "daily",
            alert_row,
            delegate_id="delegate-1",
            resolution_status="descartado",
            alert_validity="falso_positivo",
            action_taken="sin_accion",
            business_outcome="sin_oportunidad",
            root_cause="falso_positivo_operativo",
            resolved_at=pd.Timestamp(day).to_pydatetime(),
            rebuild_policy=False,
        )
    feedback_service.build_policy("daily")

    prioritization = GlobalPrioritizationService(project_root=tmp_path)
    enriched = prioritization._apply_feedback_enrichment(
        {
            **alert_row,
            "process_on_date": pd.Timestamp("2026-05-10"),
            "process_day_bucket": "today",
            "severity_label": "high",
            "priority_label": "high",
            "source_variants": ["technical.risk_assessment"],
            "explanation_ids": [],
            "source_row_keys": ["technical.risk_assessment|C001|P001"],
        },
        feedback_frame=feedback_service.load_feedback_frame("daily"),
        feedback_policy=feedback_service.load_policy("daily"),
        reference_date=pd.Timestamp("2026-05-10"),
    )

    assert enriched["repeat_alert_count_30d"] == 2
    assert enriched["feedback_adjusted_priority"] == "low"
    assert enriched["suppression_until"] == pd.Timestamp("2026-05-19").date()


def test_reason_summary_falls_back_to_contributing_factors() -> None:
    service = GlobalPrioritizationService(project_root=Path("."))
    reason = service._reason_summary_from_explanation_row(
        {
            "why_triggered_text": "",
            "contributing_factors": [
                {"name": "interval_drift_score"},
                {"name": "peer_drift_score"},
                {"name": "inactivity_score"},
            ],
        }
    )
    assert "alargamiento del ciclo" in reason
