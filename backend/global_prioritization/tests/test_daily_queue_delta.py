from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.global_prioritization.service import GlobalPrioritizationService


def test_filter_new_daily_alerts_keeps_only_alerts_missing_from_previous_snapshot(tmp_path: Path) -> None:
    service = GlobalPrioritizationService(project_root=tmp_path)
    current = pd.DataFrame(
        [
            {"global_alert_id": "gq_1", "customer_id": "C001"},
            {"global_alert_id": "gq_2", "customer_id": "C002"},
        ]
    )
    previous = pd.DataFrame(
        [
            {"global_alert_id": "gq_1", "customer_id": "C001"},
        ]
    )

    filtered = service._filter_new_daily_alerts(current, previous_full_queue=previous)

    assert filtered["global_alert_id"].tolist() == ["gq_2"]


def test_mark_current_daily_snapshot_as_seen_persists_empty_public_queue_and_full_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    service = GlobalPrioritizationService(project_root=tmp_path)
    full_queue = pd.DataFrame(
        [
            {"global_alert_id": "gq_1", "customer_id": "C001"},
            {"global_alert_id": "gq_2", "customer_id": "C002"},
        ]
    )
    monkeypatch.setattr(service, "build_full_queue", lambda mode: full_queue.copy())

    outputs = service.mark_current_daily_snapshot_as_seen("daily")

    public_queue = pd.read_json(outputs["json"])
    full_state = pd.read_json(outputs["latest_full_state_json"])
    assert public_queue.empty
    assert full_state["global_alert_id"].tolist() == ["gq_1", "gq_2"]


def test_simulate_daily_first_run_publishes_current_full_snapshot(tmp_path: Path, monkeypatch) -> None:
    service = GlobalPrioritizationService(project_root=tmp_path)
    full_queue = pd.DataFrame(
        [
            {"global_alert_id": "gq_1", "customer_id": "C001"},
            {"global_alert_id": "gq_2", "customer_id": "C002"},
        ]
    )
    monkeypatch.setattr(service, "build_full_queue", lambda mode: full_queue.copy())

    outputs = service.simulate_daily_first_run("daily")

    public_queue = pd.read_json(outputs["json"])
    full_state = pd.read_json(outputs["latest_full_state_json"])
    assert public_queue["global_alert_id"].tolist() == ["gq_1", "gq_2"]
    assert full_state["global_alert_id"].tolist() == ["gq_1", "gq_2"]
