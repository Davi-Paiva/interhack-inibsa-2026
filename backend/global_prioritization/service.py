"""Build a globally prioritized operational alert queue from existing artifacts."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from .domain import GlobalAlertRecord


COMMODITY_VARIANT_PRECEDENCE = {
    "commodity.next_purchase": 0,
    "commodity.capture_opportunity": 1,
    "commodity.demand_leakage": 2,
}


class GlobalPrioritizationService:
    """Generate the consolidated global operational queue."""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()

    @property
    def output_root(self) -> Path:
        return self.project_root / "backend" / "global_prioritization" / "output"

    def output_dir_for_mode(self, mode: str) -> Path:
        path = self.output_root / mode
        path.mkdir(parents=True, exist_ok=True)
        return path

    def commodity_output_dir(self, mode: str) -> Path:
        return self.project_root / "backend" / "commodity-ai-engine" / "output" / mode

    def technical_output_dir(self, mode: str) -> Path:
        return self.project_root / "backend" / "technical_product_engine" / "output" / mode

    def explainability_output_dir(self, mode: str) -> Path:
        return self.project_root / "backend" / "explainability_engine" / "output" / mode

    def build_queue(self, mode: str) -> pd.DataFrame:
        reference_date = self._resolve_reference_date(mode)
        explanation_map = self._load_explanation_map(mode)
        commodity_rows = self._load_commodity_rows(mode)
        consolidated_commodity = self._consolidate_commodity_rows(
            commodity_rows,
            reference_date=reference_date,
            explanation_map=explanation_map,
        )
        technical_rows = self._build_technical_rows(
            self._load_technical_rows(mode),
            reference_date=reference_date,
            explanation_map=explanation_map,
        )
        queue_rows = consolidated_commodity + technical_rows
        ranked_records = self._rank_queue_rows(queue_rows, reference_date=reference_date)
        return self._records_to_frame(ranked_records)

    def persist_queue(self, queue: pd.DataFrame, mode: str) -> dict[str, Path]:
        output_dir = self.output_dir_for_mode(mode)
        parquet_path = output_dir / "global_alert_queue.parquet"
        json_path = output_dir / "global_alert_queue.json"
        self._write_parquet(queue, parquet_path)

        json_rows = queue.to_dict(orient="records")
        for row in json_rows:
            for key in ("source_variants", "explanation_ids", "source_row_keys"):
                if isinstance(row.get(key), str):
                    row[key] = json.loads(row[key])
            process_value = row.get("process_on_date")
            if hasattr(process_value, "date"):
                row["process_on_date"] = process_value.date().isoformat()
            elif process_value is not None:
                row["process_on_date"] = str(process_value)
        json_path.write_text(json.dumps(json_rows, indent=2, ensure_ascii=True), encoding="utf-8")
        return {"parquet": parquet_path, "json": json_path}

    def _resolve_reference_date(self, mode: str) -> pd.Timestamp:
        commodity_output_dir = self.commodity_output_dir(mode)
        forecast_path = commodity_output_dir / "consumption_forecast.parquet"
        if forecast_path.exists():
            forecast_df = pd.read_parquet(forecast_path)
            if "forecast_date" in forecast_df.columns:
                parsed = pd.to_datetime(forecast_df["forecast_date"], errors="coerce")
                if parsed.notna().any():
                    return parsed.max().normalize()

        next_purchase_path = commodity_output_dir / "next_purchase_predictions.parquet"
        if next_purchase_path.exists():
            next_purchase_df = pd.read_parquet(next_purchase_path)
            if {"expected_next_purchase_date", "days_until_expected_purchase"} <= set(next_purchase_df.columns):
                expected = pd.to_datetime(next_purchase_df["expected_next_purchase_date"], errors="coerce")
                offsets = pd.to_numeric(next_purchase_df["days_until_expected_purchase"], errors="coerce")
                derived = expected - pd.to_timedelta(offsets.fillna(0.0), unit="D")
                if derived.notna().any():
                    return derived.max().normalize()

        return pd.Timestamp.utcnow().normalize()

    def _load_explanation_map(self, mode: str) -> dict[str, list[str]]:
        explainability_dir = self.explainability_output_dir(mode)
        all_path = explainability_dir / "all_explanations.parquet"
        candidates = [all_path]
        if not all_path.exists():
            candidates = [
                explainability_dir / "commodity_explanations.parquet",
                explainability_dir / "technical_explanations.parquet",
            ]

        frames: list[pd.DataFrame] = []
        for path in candidates:
            if path.exists():
                frames.append(pd.read_parquet(path))
        if not frames:
            return {}

        combined = pd.concat(frames, ignore_index=True)
        mapping: dict[str, list[str]] = {}
        for row in combined.to_dict(orient="records"):
            source_row_key = self._string(row.get("source_row_key"))
            explanation_id = self._string(row.get("explanation_id"))
            if not source_row_key or not explanation_id:
                continue
            mapping.setdefault(source_row_key, []).append(explanation_id)
        return mapping

    def _load_commodity_rows(self, mode: str) -> list[dict[str, Any]]:
        output_dir = self.commodity_output_dir(mode)
        rows: list[dict[str, Any]] = []

        leakage_path = output_dir / "demand_leakage_signals.parquet"
        if leakage_path.exists():
            leakage_df = pd.read_parquet(leakage_path)
            for row in leakage_df.to_dict(orient="records"):
                if not bool(row.get("is_actionable")):
                    continue
                if self._string(row.get("route_to_engine")) != "commodity_ai_engine":
                    continue
                risk_level = self._string(row.get("risk_level"))
                if risk_level in {"", "none"}:
                    continue
                rows.append(
                    {
                        **row,
                        "canonical_variant": "commodity.demand_leakage",
                        "severity_label": risk_level,
                        "priority_label": None,
                        "recommended_action": "",
                    }
                )

        capture_path = output_dir / "capture_opportunities.parquet"
        if capture_path.exists():
            capture_df = pd.read_parquet(capture_path)
            for row in capture_df.to_dict(orient="records"):
                rows.append(
                    {
                        **row,
                        "canonical_variant": "commodity.capture_opportunity",
                        "severity_label": self._string(row.get("priority_band")) or None,
                        "priority_label": self._string(row.get("priority_band")) or None,
                        "recommended_action": self._string(row.get("recommended_action")),
                    }
                )

        next_purchase_path = output_dir / "next_purchase_predictions.parquet"
        if next_purchase_path.exists():
            next_purchase_df = pd.read_parquet(next_purchase_path)
            for row in next_purchase_df.to_dict(orient="records"):
                rows.append(
                    {
                        **row,
                        "canonical_variant": "commodity.next_purchase",
                        "severity_label": self._string(row.get("priority_band")) or None,
                        "priority_label": self._string(row.get("priority_band")) or None,
                        "recommended_action": self._string(row.get("contact_recommendation")),
                    }
                )
        return rows

    def _consolidate_commodity_rows(
        self,
        rows: list[dict[str, Any]],
        *,
        reference_date: pd.Timestamp,
        explanation_map: dict[str, list[str]],
    ) -> list[dict[str, Any]]:
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in rows:
            customer_id = self._string(row.get("customer_id"))
            product_id = self._resolve_product_id(row)
            grouped.setdefault((customer_id, product_id), []).append(row)

        consolidated: list[dict[str, Any]] = []
        for (customer_id, product_id), group in grouped.items():
            ordered = sorted(group, key=lambda item: COMMODITY_VARIANT_PRECEDENCE[item["canonical_variant"]])
            canonical = dict(ordered[0])
            source_variants = [self._string(item.get("canonical_variant")) for item in ordered]
            source_row_keys = [
                self._source_row_key(self._string(item.get("canonical_variant")), customer_id, product_id)
                for item in ordered
            ]
            explanation_ids = self._collect_explanations(source_row_keys, explanation_map)
            canonical["customer_id"] = customer_id
            canonical["product_id"] = product_id
            canonical["source_engine"] = "commodity_ai_engine"
            canonical["source_variants"] = source_variants
            canonical["source_row_keys"] = source_row_keys
            canonical["explanation_ids"] = explanation_ids
            canonical["process_on_date"] = self._commodity_process_date(canonical, reference_date=reference_date)
            canonical["process_day_bucket"] = self._bucket_for_date(canonical["process_on_date"], reference_date)
            canonical["global_priority_score"] = self._commodity_global_score(
                canonical,
                process_day_bucket=canonical["process_day_bucket"],
            )
            canonical["global_priority_band"] = self._priority_band(canonical["global_priority_score"])
            canonical["global_alert_id"] = self._global_alert_id(
                canonical["source_engine"],
                self._string(canonical.get("canonical_variant")),
                customer_id,
                product_id,
            )
            consolidated.append(canonical)
        return consolidated

    def _load_technical_rows(self, mode: str) -> list[dict[str, Any]]:
        path = self.technical_output_dir(mode) / "technical_risk_assessments.csv"
        if not path.exists():
            return []
        technical_df = pd.read_csv(path)
        return technical_df.to_dict(orient="records")

    def _build_technical_rows(
        self,
        rows: list[dict[str, Any]],
        *,
        reference_date: pd.Timestamp,
        explanation_map: dict[str, list[str]],
    ) -> list[dict[str, Any]]:
        built: list[dict[str, Any]] = []
        for row in rows:
            customer_id = self._string(row.get("client_id"))
            product_id = self._string(row.get("product_id"))
            source_variant = "technical.risk_assessment"
            source_row_key = self._source_row_key(source_variant, customer_id, product_id)
            process_on_date = self._technical_process_date(row, reference_date=reference_date)
            process_day_bucket = self._bucket_for_date(process_on_date, reference_date)
            priority_level = self._string(row.get("priority_level")) or None
            inactivity_ratio = self._float(row.get("inactivity_ratio"))
            built.append(
                {
                    **row,
                    "customer_id": customer_id,
                    "product_id": product_id,
                    "source_engine": "technical_product_engine",
                    "canonical_variant": source_variant,
                    "source_variants": [source_variant],
                    "severity_label": self._string(row.get("risk_level")) or None,
                    "priority_label": priority_level,
                    "recommended_action": self._technical_recommendation(priority_level, inactivity_ratio),
                    "source_row_keys": [source_row_key],
                    "explanation_ids": self._collect_explanations([source_row_key], explanation_map),
                    "process_on_date": process_on_date,
                    "process_day_bucket": process_day_bucket,
                    "global_priority_score": self._technical_global_score(row),
                    "global_priority_band": self._priority_band(self._technical_global_score(row)),
                    "global_alert_id": self._global_alert_id(
                        "technical_product_engine",
                        source_variant,
                        customer_id,
                        product_id,
                    ),
                }
            )
        return built

    def _rank_queue_rows(
        self,
        rows: list[dict[str, Any]],
        *,
        reference_date: pd.Timestamp,
    ) -> list[GlobalAlertRecord]:
        del reference_date
        ordered = sorted(
            rows,
            key=lambda row: (
                pd.Timestamp(row["process_on_date"]).normalize(),
                -self._float(row.get("global_priority_score")),
                self._string(row.get("source_engine")),
                self._string(row.get("customer_id")),
                self._string(row.get("product_id")),
            ),
        )
        records: list[GlobalAlertRecord] = []
        for index, row in enumerate(ordered, start=1):
            records.append(
                GlobalAlertRecord(
                    global_alert_id=self._string(row.get("global_alert_id")),
                    source_engine=self._string(row.get("source_engine")),
                    canonical_variant=self._string(row.get("canonical_variant")),
                    source_variants=[self._string(value) for value in row.get("source_variants", [])],
                    customer_id=self._string(row.get("customer_id")),
                    product_id=self._string(row.get("product_id")),
                    severity_label=self._nullable_string(row.get("severity_label")),
                    priority_label=self._nullable_string(row.get("priority_label")),
                    global_priority_score=round(self._float(row.get("global_priority_score")), 4),
                    global_priority_band=self._string(row.get("global_priority_band")),
                    process_on_date=pd.Timestamp(row.get("process_on_date")).date(),
                    process_day_bucket=self._string(row.get("process_day_bucket")),
                    queue_rank=index,
                    recommended_action=self._string(row.get("recommended_action")),
                    explanation_ids=[self._string(value) for value in row.get("explanation_ids", [])],
                    source_row_keys=[self._string(value) for value in row.get("source_row_keys", [])],
                )
            )
        return records

    def _records_to_frame(self, records: list[GlobalAlertRecord]) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for record in records:
            payload = record.to_json_dict()
            payload["source_variants"] = json.dumps(payload["source_variants"], ensure_ascii=True)
            payload["explanation_ids"] = json.dumps(payload["explanation_ids"], ensure_ascii=True)
            payload["source_row_keys"] = json.dumps(payload["source_row_keys"], ensure_ascii=True)
            payload["process_on_date"] = pd.Timestamp(payload["process_on_date"])
            rows.append(payload)
        if not rows:
            return pd.DataFrame(
                columns=[
                    "global_alert_id",
                    "source_engine",
                    "canonical_variant",
                    "source_variants",
                    "customer_id",
                    "product_id",
                    "severity_label",
                    "priority_label",
                    "global_priority_score",
                    "global_priority_band",
                    "process_on_date",
                    "process_day_bucket",
                    "queue_rank",
                    "recommended_action",
                    "explanation_ids",
                    "source_row_keys",
                ]
            )
        return pd.DataFrame(rows)

    def _commodity_process_date(self, row: dict[str, Any], *, reference_date: pd.Timestamp) -> pd.Timestamp:
        variant = self._string(row.get("canonical_variant"))
        if variant == "commodity.next_purchase":
            start = pd.to_datetime(row.get("contact_window_start"), errors="coerce")
            if pd.notna(start):
                return start.normalize()
            return reference_date

        priority_label = self._string(row.get("priority_label"))
        if variant == "commodity.capture_opportunity":
            offset_map = {"critical": 0, "high": 1, "medium": 3, "low": 7}
            return reference_date + pd.Timedelta(days=offset_map.get(priority_label, 7))

        severity_label = self._string(row.get("severity_label"))
        leakage_offsets = {"high": 1, "medium": 3, "low": 7}
        return reference_date + pd.Timedelta(days=leakage_offsets.get(severity_label, 7))

    def _technical_process_date(self, row: dict[str, Any], *, reference_date: pd.Timestamp) -> pd.Timestamp:
        priority_level = self._string(row.get("priority_level"))
        base_offsets = {"critical": 0, "high": 1, "medium": 3, "low": 7}
        process_on_date = reference_date + pd.Timedelta(days=base_offsets.get(priority_level, 7))

        inactivity_ratio = self._float(row.get("inactivity_ratio"))
        drift_signal_count = int(self._float(row.get("drift_signal_count")))
        if inactivity_ratio >= 3.0:
            return reference_date
        if inactivity_ratio >= 2.0 and process_on_date > reference_date + pd.Timedelta(days=1):
            process_on_date = reference_date + pd.Timedelta(days=1)
        if drift_signal_count >= 2 and priority_level == "medium":
            candidate = reference_date + pd.Timedelta(days=2)
            if candidate < process_on_date:
                process_on_date = candidate
        return process_on_date

    def _bucket_for_date(self, process_on_date: pd.Timestamp, reference_date: pd.Timestamp) -> str:
        normalized = pd.Timestamp(process_on_date).normalize()
        reference = pd.Timestamp(reference_date).normalize()
        delta_days = int((normalized - reference).days)
        if delta_days < 0:
            return "overdue"
        if delta_days == 0:
            return "today"
        if delta_days == 1:
            return "tomorrow"
        if delta_days <= 6:
            return "this_week"
        return "later"

    def _commodity_global_score(self, row: dict[str, Any], *, process_day_bucket: str) -> float:
        variant = self._string(row.get("canonical_variant"))
        if variant == "commodity.next_purchase":
            capture_score = self._float(row.get("capture_score"))
            purchase_probability = self._float(row.get("purchase_probability"))
            timing_bonus = {
                "today": 15.0,
                "tomorrow": 10.0,
                "this_week": 5.0,
                "later": 0.0,
                "overdue": 15.0,
            }.get(process_day_bucket, 0.0)
            return min(100.0, (0.60 * capture_score) + (25.0 * purchase_probability) + timing_bonus)
        if variant == "commodity.capture_opportunity":
            return min(100.0, self._float(row.get("capture_score")))
        return min(100.0, self._float(row.get("leakage_score")) * 100.0)

    def _technical_global_score(self, row: dict[str, Any]) -> float:
        priority_score = self._float(row.get("priority_score"))
        inactivity_ratio = self._float(row.get("inactivity_ratio"))
        base_score = min(priority_score / 1.20, 1.0) * 90.0
        if inactivity_ratio >= 3.0:
            urgency_bonus = 10.0
        elif inactivity_ratio >= 2.0:
            urgency_bonus = 5.0
        else:
            urgency_bonus = 0.0
        return min(base_score + urgency_bonus, 100.0)

    def _priority_band(self, score: float) -> str:
        if score >= 85.0:
            return "critical"
        if score >= 65.0:
            return "high"
        if score >= 40.0:
            return "medium"
        return "low"

    def _technical_recommendation(self, priority_level: str | None, inactivity_ratio: float) -> str:
        if priority_level == "critical":
            return "Review today and trigger immediate retention outreach for this technical relationship."
        if priority_level == "high":
            return "Review within one day and validate the recent commercial deterioration with the sales owner."
        if inactivity_ratio >= 2.0:
            return "Review this week and confirm whether the customer has missed the expected reorder cycle."
        return "Keep in the technical review queue and monitor the next scheduled cycle."

    def _collect_explanations(
        self,
        source_row_keys: list[str],
        explanation_map: dict[str, list[str]],
    ) -> list[str]:
        collected: list[str] = []
        for key in source_row_keys:
            for explanation_id in explanation_map.get(key, []):
                if explanation_id not in collected:
                    collected.append(explanation_id)
        return collected

    def _source_row_key(self, variant: str, customer_id: str, product_id: str) -> str:
        return f"{variant}|{customer_id}|{product_id}"

    def _global_alert_id(self, source_engine: str, variant: str, customer_id: str, product_id: str) -> str:
        raw = f"{source_engine}|{variant}|{customer_id}|{product_id}"
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
        return f"gq_{digest}"

    def _resolve_product_id(self, row: dict[str, Any]) -> str:
        for key in ("product_id", "product_family", "family"):
            value = row.get(key)
            if value is not None and str(value) != "":
                return str(value)
        return ""

    def _write_parquet(self, frame: pd.DataFrame, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(path, index=False, compression="snappy", engine=self._parquet_engine())

    @staticmethod
    def _parquet_engine() -> str:
        if importlib.util.find_spec("pyarrow") is not None:
            return "pyarrow"
        if importlib.util.find_spec("fastparquet") is not None:
            return "fastparquet"
        raise RuntimeError(
            "Global prioritization parquet output requires either 'pyarrow' or 'fastparquet' to be installed."
        )

    @staticmethod
    def _string(value: Any) -> str:
        return "" if value is None else str(value)

    @staticmethod
    def _nullable_string(value: Any) -> str | None:
        text = "" if value is None else str(value)
        return text or None

    @staticmethod
    def _float(value: Any) -> float:
        try:
            numeric = float(value)
            if pd.isna(numeric):
                return 0.0
            return numeric
        except (TypeError, ValueError):
            return 0.0


def build_global_alert_queue(
    mode: str,
    *,
    project_root: Path,
) -> dict[str, Path]:
    service = GlobalPrioritizationService(project_root)
    queue = service.build_queue(mode)
    return service.persist_queue(queue, mode)
