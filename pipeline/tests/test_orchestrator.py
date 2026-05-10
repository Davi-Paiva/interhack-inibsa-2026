from __future__ import annotations

from pathlib import Path

from pipeline.orchestrator import GlobalPipeline


def test_global_pipeline_propagates_daily_mode(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, object]] = []

    def fake_load_raw_data(data_dir: str) -> dict[str, object]:
        calls.append(("load_raw_data", data_dir))
        return {"sales": object()}

    def fake_run_feature_pipeline(raw_data: dict[str, object], *, data_dir: str, mode: str) -> dict[str, object]:
        calls.append(("run_feature_pipeline", {"raw_data": raw_data, "data_dir": data_dir, "mode": mode}))
        return {"client_product_features": tmp_path / "client_product_features.csv"}

    def fake_run_commodity_pipeline(features: dict[str, object], *, mode: str) -> list[str]:
        calls.append(("run_commodity_pipeline", {"features": features, "mode": mode}))
        return ["commodity"]

    def fake_run_technical_pipeline(features: dict[str, object], *, mode: str) -> list[str]:
        calls.append(("run_technical_pipeline", {"features": features, "mode": mode}))
        return ["technical"]

    def fake_merge_engine_outputs(commodity_results: list[str], technical_results: list[str], *, mode: str) -> dict[str, object]:
        calls.append(
            (
                "merge_engine_outputs",
                {
                    "commodity_results": commodity_results,
                    "technical_results": technical_results,
                    "mode": mode,
                },
            )
        )
        return {"final_queue": tmp_path / "global_alert_queue.json"}

    monkeypatch.setattr("pipeline.orchestrator.load_raw_data", fake_load_raw_data)
    monkeypatch.setattr("pipeline.orchestrator.run_feature_pipeline", fake_run_feature_pipeline)
    monkeypatch.setattr("pipeline.orchestrator.run_commodity_pipeline", fake_run_commodity_pipeline)
    monkeypatch.setattr("pipeline.orchestrator.run_technical_pipeline", fake_run_technical_pipeline)
    monkeypatch.setattr("pipeline.orchestrator.merge_engine_outputs", fake_merge_engine_outputs)

    pipeline = GlobalPipeline()
    result = pipeline.run(str(tmp_path), mode="daily")

    assert result == {"final_queue": tmp_path / "global_alert_queue.json"}
    assert calls[0] == ("load_raw_data", str(tmp_path))
    assert calls[1][0] == "run_feature_pipeline"
    assert calls[1][1]["mode"] == "daily"
    assert calls[2][0] == "run_commodity_pipeline"
    assert calls[2][1]["mode"] == "daily"
    assert calls[3][0] == "run_technical_pipeline"
    assert calls[3][1]["mode"] == "daily"
    assert calls[4][0] == "merge_engine_outputs"
    assert calls[4][1]["mode"] == "daily"
