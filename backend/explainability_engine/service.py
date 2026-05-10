"""Persistence and orchestration service for explainability artifacts."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .builders import explanation_row
from .commodity_explainer import (
    explain_capture_frame,
    explain_leakage_frame,
    explain_next_purchase_frame,
)
from .domain import ExplanationRecord
from .technical_explainer import explain_technical_payload


class ExplainabilityService:
    """Generate and persist explainability artifacts for existing engine outputs."""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()

    @property
    def output_root(self) -> Path:
        return self.project_root / "backend" / "explainability_engine" / "output"

    def output_dir_for_mode(self, mode: str) -> Path:
        path = self.output_root / mode
        path.mkdir(parents=True, exist_ok=True)
        return path

    def commodity_output_dir(self, mode: str) -> Path:
        return self.project_root / "backend" / "commodity-ai-engine" / "output" / mode

    def technical_output_dir(self, mode: str) -> Path:
        return self.project_root / "backend" / "technical_product_engine" / "output" / mode

    def generate_commodity_records(self, mode: str) -> list[ExplanationRecord]:
        output_dir = self.commodity_output_dir(mode)
        records: list[ExplanationRecord] = []
        leakage_path = output_dir / "demand_leakage_signals.parquet"
        if leakage_path.exists():
            records.extend(explain_leakage_frame(pd.read_parquet(leakage_path), source_artifact=leakage_path.name))
        capture_path = output_dir / "capture_opportunities.parquet"
        if capture_path.exists():
            records.extend(explain_capture_frame(pd.read_parquet(capture_path), source_artifact=capture_path.name))
        next_purchase_path = output_dir / "next_purchase_predictions.parquet"
        if next_purchase_path.exists():
            records.extend(explain_next_purchase_frame(pd.read_parquet(next_purchase_path), source_artifact=next_purchase_path.name))
        return records

    def generate_technical_records(self, mode: str) -> list[ExplanationRecord]:
        output_dir = self.technical_output_dir(mode)
        input_path = output_dir / "technical_explanation_inputs.json"
        if not input_path.exists():
            return []
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        return explain_technical_payload(payload, source_artifact=input_path.name)

    def _records_to_frame(self, records: list[ExplanationRecord]) -> pd.DataFrame:
        if not records:
            return pd.DataFrame(
                columns=[
                    "explanation_id",
                    "source_engine",
                    "alert_variant",
                    "entity_id",
                    "customer_id",
                    "product_id",
                    "severity_label",
                    "priority_label",
                    "headline",
                    "summary_text",
                    "why_triggered_text",
                    "confidence_text",
                    "temporal_summary_text",
                    "contributing_factors",
                    "supporting_metrics",
                    "decision_trace",
                    "source_artifact",
                    "source_row_key",
                ]
            )
        return pd.DataFrame([explanation_row(record) for record in records])

    def persist_records(self, records: list[ExplanationRecord], mode: str, stem: str) -> dict[str, Path]:
        output_dir = self.output_dir_for_mode(mode)
        frame = self._records_to_frame(records)
        parquet_path = output_dir / f"{stem}.parquet"
        json_path = output_dir / f"{stem}.json"
        self._write_parquet(frame, parquet_path)
        json_payload = [record.to_json_dict() for record in records]
        json_path.write_text(json.dumps(json_payload, indent=2, ensure_ascii=True), encoding="utf-8")
        return {"parquet": parquet_path, "json": json_path}

    def sync_all_explanations(self, mode: str) -> dict[str, Path]:
        output_dir = self.output_dir_for_mode(mode)
        frames: list[pd.DataFrame] = []
        for name in ("commodity_explanations.parquet", "technical_explanations.parquet"):
            path = output_dir / name
            if path.exists():
                frames.append(pd.read_parquet(path))
        combined = pd.concat(frames, ignore_index=True) if frames else self._records_to_frame([])
        parquet_path = output_dir / "all_explanations.parquet"
        json_path = output_dir / "all_explanations.json"
        self._write_parquet(combined, parquet_path)
        records = combined.to_dict(orient="records")
        for row in records:
            for key in ("contributing_factors", "supporting_metrics", "decision_trace"):
                value = row.get(key)
                if isinstance(value, str):
                    row[key] = json.loads(value)
        json_path.write_text(json.dumps(records, indent=2, ensure_ascii=True), encoding="utf-8")
        return {"parquet": parquet_path, "json": json_path}

    @staticmethod
    def _parquet_engine() -> str:
        if importlib.util.find_spec("pyarrow") is not None:
            return "pyarrow"
        if importlib.util.find_spec("fastparquet") is not None:
            return "fastparquet"
        raise RuntimeError(
            "Explainability parquet output requires either 'pyarrow' or 'fastparquet' to be installed."
        )

    def _write_parquet(self, frame: pd.DataFrame, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(path, index=False, compression="snappy", engine=self._parquet_engine())


def generate_commodity_explanations(
    mode: str,
    *,
    project_root: Path,
) -> dict[str, Path]:
    service = ExplainabilityService(project_root)
    records = service.generate_commodity_records(mode)
    paths = service.persist_records(records, mode, "commodity_explanations")
    service.sync_all_explanations(mode)
    return paths


def generate_technical_explanations(
    mode: str,
    *,
    project_root: Path,
) -> dict[str, Path]:
    service = ExplainabilityService(project_root)
    records = service.generate_technical_records(mode)
    paths = service.persist_records(records, mode, "technical_explanations")
    service.sync_all_explanations(mode)
    return paths


def sync_all_explanations(
    mode: str,
    *,
    project_root: Path,
) -> dict[str, Path]:
    service = ExplainabilityService(project_root)
    return service.sync_all_explanations(mode)
