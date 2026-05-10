"""Build a globally prioritized operational alert queue from existing artifacts."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from backend.delegate_feedback.service import DelegateFeedbackService

from .domain import GlobalAlertRecord


COMMODITY_VARIANT_PRECEDENCE = {
    "commodity.next_purchase": 0,
    "commodity.capture_opportunity": 1,
    "commodity.demand_leakage": 2,
    "commodity.churn_risk": 3,
}

FINAL_QUEUE_LIMIT = 30
PROMISCUOUS_CLUSTER_ID = 2


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

    def state_dir_for_mode(self, mode: str) -> Path:
        path = self.project_root / "backend" / "global_prioritization" / "state" / mode
        path.mkdir(parents=True, exist_ok=True)
        return path

    def commodity_output_dir(self, mode: str) -> Path:
        return self.project_root / "backend" / "commodity-ai-engine" / "output" / mode

    def technical_output_dir(self, mode: str) -> Path:
        return self.project_root / "backend" / "technical_product_engine" / "output" / mode

    def explainability_output_dir(self, mode: str) -> Path:
        return self.project_root / "backend" / "explainability_engine" / "output" / mode

    def build_queue(self, mode: str) -> pd.DataFrame:
        full_queue = self.build_full_queue(mode)
        if mode != "daily":
            return full_queue
        previous_full_queue = self._load_previous_daily_full_queue(mode)
        return self._filter_new_daily_alerts(full_queue, previous_full_queue=previous_full_queue)

    def build_full_queue(self, mode: str) -> pd.DataFrame:
        reference_date = self._resolve_reference_date(mode)
        explanation_map, reason_map = self._load_explanation_bundle(mode)
        feedback_service = DelegateFeedbackService(self.project_root)
        feedback_frame = feedback_service.load_feedback_frame(mode)
        feedback_policy = feedback_service.load_policy(mode)
        commodity_rows = self._load_commodity_rows(mode)
        consolidated_commodity = self._consolidate_commodity_rows(
            commodity_rows,
            reference_date=reference_date,
            explanation_map=explanation_map,
            reason_map=reason_map,
        )
        technical_rows = self._build_technical_rows(
            self._load_technical_rows(mode),
            reference_date=reference_date,
            explanation_map=explanation_map,
            reason_map=reason_map,
        )
        queue_rows = consolidated_commodity + self._select_technical_candidates(technical_rows)
        queue_rows = [
            self._apply_feedback_enrichment(
                row,
                feedback_frame=feedback_frame,
                feedback_policy=feedback_policy,
                reference_date=reference_date,
            )
            for row in queue_rows
        ]
        ranked_records = self._rank_queue_rows(queue_rows, reference_date=reference_date)
        return self._records_to_frame(ranked_records[:FINAL_QUEUE_LIMIT])

    def persist_queue(
        self,
        queue: pd.DataFrame,
        mode: str,
        *,
        full_queue: pd.DataFrame | None = None,
    ) -> dict[str, Path]:
        output_dir = self.output_dir_for_mode(mode)
        parquet_path = output_dir / "global_alert_queue.parquet"
        json_path = output_dir / "global_alert_queue.json"
        self._write_parquet(queue, parquet_path)

        json_rows = queue.to_dict(orient="records")
        for row in json_rows:
            for key in ("source_variants", "explanation_ids", "source_row_keys"):
                if isinstance(row.get(key), str):
                    row[key] = json.loads(row[key])
            for key in ("process_on_date", "suppression_until"):
                process_value = row.get(key)
                if pd.isna(process_value):
                    row[key] = None
                    continue
                if hasattr(process_value, "date"):
                    row[key] = process_value.date().isoformat()
                elif process_value is not None:
                    row[key] = str(process_value)
        json_path.write_text(json.dumps(json_rows, indent=2, ensure_ascii=True), encoding="utf-8")
        outputs = {"parquet": parquet_path, "json": json_path}

        if mode == "daily":
            full_frame = full_queue if full_queue is not None else queue
            outputs.update(self._persist_daily_full_queue_state(full_frame, output_dir=output_dir, mode=mode))

        return outputs

    def _load_previous_daily_full_queue(self, mode: str) -> pd.DataFrame:
        candidates = [
            self.state_dir_for_mode(mode) / "latest_full_queue.json",
            self.output_dir_for_mode(mode) / "global_alert_queue_full.json",
            self.output_dir_for_mode(mode) / "global_alert_queue.json",
        ]
        for path in candidates:
            if not path.exists():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, list):
                continue
            frame = pd.DataFrame(payload)
            if "global_alert_id" not in frame.columns:
                continue
            return frame
        return pd.DataFrame(columns=["global_alert_id"])

    def _filter_new_daily_alerts(
        self,
        queue: pd.DataFrame,
        *,
        previous_full_queue: pd.DataFrame,
    ) -> pd.DataFrame:
        if queue.empty:
            return queue.copy()
        if previous_full_queue.empty or "global_alert_id" not in previous_full_queue.columns:
            return queue.copy()
        previous_ids = {
            self._string(value)
            for value in previous_full_queue["global_alert_id"].tolist()
            if self._string(value)
        }
        if not previous_ids:
            return queue.copy()
        filtered = queue.loc[~queue["global_alert_id"].astype("string").isin(previous_ids)].copy()
        return filtered.reset_index(drop=True)

    def _persist_daily_full_queue_state(
        self,
        full_queue: pd.DataFrame,
        *,
        output_dir: Path,
        mode: str,
    ) -> dict[str, Path]:
        full_parquet_path = output_dir / "global_alert_queue_full.parquet"
        full_json_path = output_dir / "global_alert_queue_full.json"
        self._write_parquet(full_queue, full_parquet_path)

        json_rows = full_queue.to_dict(orient="records")
        for row in json_rows:
            for key in ("source_variants", "explanation_ids", "source_row_keys"):
                if isinstance(row.get(key), str):
                    row[key] = json.loads(row[key])
            for key in ("process_on_date", "suppression_until"):
                process_value = row.get(key)
                if pd.isna(process_value):
                    row[key] = None
                    continue
                if hasattr(process_value, "date"):
                    row[key] = process_value.date().isoformat()
                elif process_value is not None:
                    row[key] = str(process_value)
        full_json_path.write_text(json.dumps(json_rows, indent=2, ensure_ascii=True), encoding="utf-8")

        state_dir = self.state_dir_for_mode(mode)
        latest_state_path = state_dir / "latest_full_queue.json"
        latest_state_path.write_text(json.dumps(json_rows, indent=2, ensure_ascii=True), encoding="utf-8")
        return {
            "full_parquet": full_parquet_path,
            "full_json": full_json_path,
            "latest_full_state_json": latest_state_path,
        }

    def reset_daily_state(self, mode: str = "daily") -> dict[str, list[str]]:
        paths = [
            self.state_dir_for_mode(mode) / "latest_full_queue.json",
            self.output_dir_for_mode(mode) / "global_alert_queue.json",
            self.output_dir_for_mode(mode) / "global_alert_queue.parquet",
            self.output_dir_for_mode(mode) / "global_alert_queue_full.json",
            self.output_dir_for_mode(mode) / "global_alert_queue_full.parquet",
        ]
        deleted: list[str] = []
        for path in paths:
            if path.exists():
                path.unlink()
                deleted.append(str(path))
        return {"deleted": deleted}

    def mark_current_daily_snapshot_as_seen(self, mode: str = "daily") -> dict[str, Path]:
        full_queue = self.build_full_queue(mode)
        empty_public_queue = full_queue.iloc[0:0].copy()
        return self.persist_queue(empty_public_queue, mode, full_queue=full_queue)

    def simulate_daily_first_run(self, mode: str = "daily") -> dict[str, Path]:
        self.reset_daily_state(mode)
        full_queue = self.build_full_queue(mode)
        return self.persist_queue(full_queue, mode, full_queue=full_queue)

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

    def _load_explanation_bundle(self, mode: str) -> tuple[dict[str, list[str]], dict[str, str]]:
        explainability_dir = self.explainability_output_dir(mode)
        records: list[dict[str, Any]] = []
        json_candidates = [explainability_dir / "all_explanations.json"]
        if not json_candidates[0].exists():
            json_candidates = [
                explainability_dir / "commodity_explanations.json",
                explainability_dir / "technical_explanations.json",
            ]
        for path in json_candidates:
            if path.exists():
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, list):
                    records.extend(payload)
        if not records:
            return {}, {}

        mapping: dict[str, list[str]] = {}
        reason_map: dict[str, str] = {}
        for row in records:
            source_row_key = self._string(row.get("source_row_key"))
            explanation_id = self._string(row.get("explanation_id"))
            if not source_row_key or not explanation_id:
                continue
            mapping.setdefault(source_row_key, []).append(explanation_id)
            reason_map[source_row_key] = self._reason_summary_from_explanation_row(row)
        return mapping, reason_map

    def _load_commodity_rows(self, mode: str) -> list[dict[str, Any]]:
        output_dir = self.commodity_output_dir(mode)
        rows: list[dict[str, Any]] = []

        leakage_path = output_dir / "demand_leakage_signals.parquet"
        if leakage_path.exists():
            leakage_df = pd.read_parquet(leakage_path)
            for row in leakage_df.to_dict(orient="records"):
                risk_level = self._string(row.get("risk_level"))
                if risk_level in {"", "none"}:
                    continue
                if bool(row.get("is_actionable")) and self._string(row.get("route_to_engine")) == "commodity_ai_engine":
                    rows.append(
                        {
                            **row,
                            "canonical_variant": "commodity.demand_leakage",
                            "severity_label": risk_level,
                            "priority_label": None,
                            "recommended_action": "",
                        }
                    )
                    continue
                if self._is_commodity_churn_candidate(row):
                    rows.append(
                        {
                            **row,
                            "canonical_variant": "commodity.churn_risk",
                            "explanation_variant": "commodity.demand_leakage",
                            "severity_label": risk_level,
                            "priority_label": None,
                            "recommended_action": self._commodity_churn_recommendation(
                                self._string(row.get("routing_reason"))
                            ),
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
        reason_map: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        reason_lookup = reason_map or {}
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in rows:
            customer_id = self._string(row.get("customer_id"))
            product_id = self._resolve_product_id(row)
            grouped.setdefault((customer_id, product_id), []).append(row)

        consolidated: list[dict[str, Any]] = []
        for (customer_id, product_id), group in grouped.items():
            ordered = sorted(group, key=lambda item: COMMODITY_VARIANT_PRECEDENCE[item["canonical_variant"]])
            canonical = self._merge_commodity_group_rows(ordered)
            source_variants = [self._string(item.get("canonical_variant")) for item in ordered]
            source_row_keys = [
                self._source_row_key(
                    self._string(item.get("explanation_variant")) or self._string(item.get("canonical_variant")),
                    customer_id,
                    product_id,
                )
                for item in ordered
            ]
            explanation_ids = self._collect_explanations(source_row_keys, explanation_map)
            canonical["customer_id"] = customer_id
            canonical["product_id"] = product_id
            canonical["source_engine"] = "commodity_ai_engine"
            canonical["source_variants"] = source_variants
            canonical["source_row_keys"] = source_row_keys
            canonical["explanation_ids"] = explanation_ids
            canonical["alert_reason_summary"] = self._collect_reason_summary(source_row_keys, reason_lookup) or self._commodity_reason_summary(canonical)
            canonical["process_on_date"] = self._commodity_process_date(canonical, reference_date=reference_date)
            canonical["process_day_bucket"] = self._bucket_for_date(canonical["process_on_date"], reference_date)
            canonical["global_priority_score"] = self._commodity_global_score(
                canonical,
                process_day_bucket=canonical["process_day_bucket"],
            )
            canonical["global_priority_band"] = self._global_priority_band_for_row(
                "commodity_ai_engine",
                score=canonical["global_priority_score"],
                priority_label=canonical.get("priority_label"),
            )
            canonical["global_alert_id"] = self._global_alert_id(
                canonical["source_engine"],
                self._string(canonical.get("canonical_variant")),
                customer_id,
                product_id,
            )
            consolidated.append(canonical)
        return consolidated

    def _merge_commodity_group_rows(self, ordered_rows: list[dict[str, Any]]) -> dict[str, Any]:
        """Preserve the highest-precedence variant while backfilling missing fields from sibling variants."""
        merged = dict(ordered_rows[0])
        for sibling in ordered_rows[1:]:
            for key, value in sibling.items():
                if key == "canonical_variant":
                    continue
                if key not in merged or self._is_missing_value(merged.get(key)):
                    merged[key] = value
        return merged

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
        reason_map: dict[str, str],
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
            global_priority_score = self._technical_global_score(row)
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
                    "alert_reason_summary": self._collect_reason_summary([source_row_key], reason_map) or self._technical_reason_summary(row),
                    "process_on_date": process_on_date,
                    "process_day_bucket": process_day_bucket,
                    "global_priority_score": global_priority_score,
                    "global_priority_band": self._global_priority_band_for_row(
                        "technical_product_engine",
                        score=global_priority_score,
                        priority_label=priority_level,
                    ),
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
        ordered = sorted(
            rows,
            key=lambda row: (
                -self._operational_rank_score(row, reference_date=reference_date),
                pd.Timestamp(row.get("_effective_process_on_date", row["process_on_date"])).normalize(),
                -self._float(row.get("_effective_priority_score", row.get("global_priority_score"))),
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
                    feedback_adjusted_priority=self._nullable_string(row.get("feedback_adjusted_priority")),
                    delegate_hint=self._string(row.get("delegate_hint")),
                    last_delegate_outcome=self._nullable_string(row.get("last_delegate_outcome")),
                    repeat_alert_count_30d=int(self._float(row.get("repeat_alert_count_30d"))),
                    suppression_until=self._date_or_none(row.get("suppression_until")),
                    alert_reason_summary=self._string(row.get("alert_reason_summary")),
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
            payload["suppression_until"] = (
                pd.Timestamp(payload["suppression_until"]) if payload.get("suppression_until") else pd.NaT
            )
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
                    "feedback_adjusted_priority",
                    "delegate_hint",
                    "last_delegate_outcome",
                    "repeat_alert_count_30d",
                    "suppression_until",
                    "alert_reason_summary",
                    "explanation_ids",
                    "source_row_keys",
                ]
            )
        return pd.DataFrame(rows)

    @staticmethod
    def _select_technical_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            row
            for row in rows
            if row.get("process_day_bucket") in {"today", "tomorrow", "this_week"}
            and row.get("global_priority_band") == "critical"
        ]

    def _apply_feedback_enrichment(
        self,
        row: dict[str, Any],
        *,
        feedback_frame: pd.DataFrame,
        feedback_policy: dict[str, Any],
        reference_date: pd.Timestamp,
    ) -> dict[str, Any]:
        enriched = dict(row)
        base_score = self._float(enriched.get("global_priority_score"))
        adjusted_score = base_score
        enriched["feedback_adjusted_priority"] = None
        enriched["delegate_hint"] = ""
        enriched["last_delegate_outcome"] = None
        enriched["repeat_alert_count_30d"] = 0
        enriched["suppression_until"] = None

        history = self._feedback_history_for_alert(feedback_frame, enriched.get("global_alert_id"), reference_date)
        repeat_count = self._repeat_alert_count_30d(history, reference_date)
        enriched["repeat_alert_count_30d"] = repeat_count

        hint_parts: list[str] = []
        if not history.empty:
            latest = history.iloc[0].to_dict()
            last_outcome = self._last_delegate_outcome_text(latest)
            suppression_until = self._suppression_until_from_feedback_row(latest)
            enriched["last_delegate_outcome"] = last_outcome
            enriched["suppression_until"] = suppression_until.date() if suppression_until is not None else None
            adjusted_score = self._apply_direct_history_adjustment(adjusted_score, latest, repeat_count)
            if self._string(latest.get("alert_validity")) == "falso_positivo":
                hint_parts.append("Hubo falsos positivos recientes en esta misma alerta.")
            elif self._string(latest.get("business_outcome")) == "pedido_generado":
                hint_parts.append("Una alerta igual acabo recientemente en pedido.")
            elif self._string(latest.get("root_cause")) == "cliente_ya_gestionado":
                hint_parts.append("Este cliente ya fue gestionado hace poco para esta misma senal.")

        variant_policy = feedback_policy.get("by_variant", {}).get(self._string(enriched.get("canonical_variant")), {})
        if variant_policy:
            adjusted_score = self._apply_variant_policy_adjustment(adjusted_score, variant_policy)
            policy_hint = self._string(variant_policy.get("delegate_hint"))
            if policy_hint:
                hint_parts.append(policy_hint)

        suppression_date = enriched.get("suppression_until")
        effective_process_on_date = pd.Timestamp(enriched.get("process_on_date")).normalize()
        if suppression_date:
            suppression_ts = pd.Timestamp(suppression_date).normalize()
            if suppression_ts >= reference_date.normalize():
                adjusted_score = min(adjusted_score, 5.0)
                effective_process_on_date = max(effective_process_on_date, suppression_ts + pd.Timedelta(days=1))

        if adjusted_score != base_score:
            enriched["feedback_adjusted_priority"] = self._priority_band(adjusted_score)
        enriched["delegate_hint"] = self._compose_hint(hint_parts)
        enriched["_effective_priority_score"] = adjusted_score
        enriched["_effective_process_on_date"] = effective_process_on_date
        return enriched

    def _operational_rank_score(self, row: dict[str, Any], *, reference_date: pd.Timestamp) -> float:
        effective_process_on_date = pd.Timestamp(
            row.get("_effective_process_on_date", row.get("process_on_date"))
        ).normalize()
        effective_bucket = self._bucket_for_date(effective_process_on_date, reference_date)
        urgency_bonus = {
            "overdue": 8.0,
            "today": 7.0,
            "tomorrow": 5.0,
            "this_week": 2.0,
            "later": 0.0,
        }.get(effective_bucket, 0.0)
        effective_score = self._float(row.get("_effective_priority_score", row.get("global_priority_score")))
        return effective_score + urgency_bonus

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
        base_offsets = {"critical": 2, "high": 5, "medium": 10, "low": 14}
        process_on_date = reference_date + pd.Timedelta(days=base_offsets.get(priority_level, 14))

        inactivity_ratio = self._float(row.get("inactivity_ratio"))
        drift_signal_count = int(self._float(row.get("drift_signal_count")))
        if inactivity_ratio >= 8.0 and drift_signal_count >= 3:
            return reference_date
        if inactivity_ratio >= 6.0 and drift_signal_count >= 3 and priority_level == "critical":
            process_on_date = min(process_on_date, reference_date + pd.Timedelta(days=1))
        if drift_signal_count >= 4 and priority_level in ("high", "critical"):
            candidate = reference_date + pd.Timedelta(days=3)
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
            # Reduce slightly to balance with technical
            return min(100.0, (0.62 * capture_score) + (24.0 * purchase_probability) + timing_bonus + 2.0)
        if variant == "commodity.churn_risk":
            # Reduce power exponent closer to 1.0 for less aggressive boost
            leakage_score = self._float(row.get("leakage_score"))
            boosted_score = (leakage_score ** 0.90) * 105.0 + 8.0
            return min(100.0, boosted_score)
        if variant == "commodity.capture_opportunity":
            # Reduce multiplier
            return min(100.0, self._float(row.get("capture_score")) * 1.08 + 4.0)
        # Default demand_leakage variant
        leakage_score = self._float(row.get("leakage_score"))
        boosted_score = (leakage_score ** 0.90) * 105.0 + 8.0
        return min(100.0, boosted_score)

    def _technical_global_score(self, row: dict[str, Any]) -> float:
        priority_score = self._float(row.get("priority_score"))
        drift_signal_count = int(self._float(row.get("drift_signal_count")))
        # Much more aggressive scaling - median priority_score is 0.6, max is 8.4
        # Scale to use full 0-80 range more evenly
        base_score = min(priority_score / 10.0, 1.0) * 75.0
        # Reward multiple drift signals
        if drift_signal_count >= 4:
            drift_bonus = 5.0
        elif drift_signal_count >= 3:
            drift_bonus = 3.0
        else:
            drift_bonus = 0.0
        return min(base_score + drift_bonus, 100.0)

    def _priority_band(self, score: float) -> str:
        if score >= 95.0:
            return "critical"
        if score >= 80.0:
            return "high"
        if score >= 55.0:
            return "medium"
        return "low"

    def _global_priority_band_for_row(
        self,
        source_engine: str,
        *,
        score: float,
        priority_label: Any = None,
    ) -> str:
        if source_engine == "technical_product_engine":
            return self._technical_priority_band(score)
        return self._priority_band(score)

    @staticmethod
    def _technical_priority_band(score: float) -> str:
        if score >= 60.0:
            return "critical"
        if score >= 50.0:
            return "high"
        if score >= 40.0:
            return "medium"
        return "low"

    def _technical_recommendation(self, priority_level: str | None, inactivity_ratio: float) -> str:
        drift_count = 0  # Not available in this context
        if inactivity_ratio >= 8.0:
            return "URGENT: Customer fully disengaged with multiple drift signals - immediate retention call required."
        if priority_level == "critical":
            return "High-priority retention case - schedule outreach within 2-3 days."
        if priority_level == "high":
            return "Notable risk detected - contact customer within a week to assess needs."
        if priority_level == "medium":
            return "Monitor relationship and plan proactive check-in within 2 weeks."
        return "Track for patterns - routine monitoring sufficient."

    def _is_commodity_churn_candidate(self, row: dict[str, Any]) -> bool:
        routing_reason = self._string(row.get("routing_reason"))
        return (
            self._string(row.get("route_to_engine")) == "technical_product_engine"
            and self._string(row.get("risk_level")) in {"high", "medium"}
            and self._is_promiscuous_cluster(row.get("cluster_id"))
            and ("inactive_customer" in routing_reason or "stale_customer" in routing_reason)
        )

    def _is_promiscuous_cluster(self, cluster_id: Any) -> bool:
        try:
            numeric = float(cluster_id)
        except (TypeError, ValueError):
            return False
        return not pd.isna(numeric) and numeric == float(PROMISCUOUS_CLUSTER_ID)

    def _commodity_churn_recommendation(self, routing_reason: str) -> str:
        if "inactive_customer" in routing_reason or "stale_customer" in routing_reason:
            return "Promiscuous commodity relationship is going inactive; verify churn risk and assess reactivation opportunity."
        return "Review this promiscuous commodity relationship for a possible reactivation opportunity."

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

    def _collect_reason_summary(self, source_row_keys: list[str], reason_map: dict[str, str]) -> str:
        collected: list[str] = []
        for key in source_row_keys:
            reason = self._string(reason_map.get(key))
            if reason and reason not in collected:
                collected.append(reason)
        if not collected:
            return ""
        return " | ".join(collected[:2])

    def _commodity_reason_summary(self, row: dict[str, Any]) -> str:
        variant = self._string(row.get("canonical_variant"))
        if variant == "commodity.next_purchase":
            probability = self._float(row.get("purchase_probability"))
            if probability >= 0.7:
                return "Salta por alta probabilidad de recompra, ventana de contacto cercana y patron de compra conocido."
            return "Salta por proximidad de la siguiente compra esperada y patron historico de recompra."
        if variant == "commodity.capture_opportunity":
            return "Salta por combinacion de leakage, valor del cliente y urgencia comercial."
        gap_ratio = self._float(row.get("gap_ratio"))
        if gap_ratio > 0:
            return "Salta por caida frente a la demanda esperada y riesgo de leakage comercial."
        return "Salta por deterioro reciente frente a la demanda estimada."

    def _technical_reason_summary(self, row: dict[str, Any]) -> str:
        reasons: list[str] = []
        if self._float(row.get("inactivity_score")) > 0:
            reasons.append("inactividad reciente")
        if self._float(row.get("interval_drift_score")) > 0:
            reasons.append("alargamiento del ciclo de compra")
        if self._float(row.get("volume_drift_score")) > 0:
            reasons.append("caida de volumen")
        if self._float(row.get("peer_drift_score")) > 0:
            reasons.append("peor comportamiento frente a clientes parecidos")
        if reasons:
            return "Salta por " + ", ".join(reasons[:3]) + "."
        return "Salta por deterioro tecnico reciente de la relacion cliente-producto."

    def _reason_summary_from_explanation_row(self, row: dict[str, Any]) -> str:
        factors = row.get("contributing_factors") or []
        if isinstance(factors, str):
            try:
                factors = json.loads(factors)
            except json.JSONDecodeError:
                factors = []
        names = []
        for factor in factors:
            factor_name = self._string(factor.get("name")) if isinstance(factor, dict) else self._string(factor)
            label = self._human_factor_label(factor_name)
            if label and label not in names:
                names.append(label)
        if names:
            return "Salta por " + ", ".join(names[:3]) + "."
        why_text = self._string(row.get("why_triggered_text")).strip()
        if why_text:
            sentences = why_text.split(".")
            return sentences[0].strip() + "."
        return self._string(row.get("summary_text")).strip()

    def _feedback_history_for_alert(
        self,
        feedback_frame: pd.DataFrame,
        global_alert_id: Any,
        reference_date: pd.Timestamp,
    ) -> pd.DataFrame:
        if feedback_frame.empty:
            return feedback_frame
        filtered = feedback_frame.copy()
        filtered = filtered.loc[filtered["global_alert_id"].astype(str) == self._string(global_alert_id)].copy()
        if filtered.empty:
            return filtered
        filtered["resolved_at"] = pd.to_datetime(filtered["resolved_at"], errors="coerce")
        filtered = filtered.loc[filtered["resolved_at"].notna()]
        comparison_date = pd.Timestamp(reference_date)
        tz = getattr(filtered["resolved_at"].dt, "tz", None)
        if tz is not None:
            if comparison_date.tzinfo is None:
                comparison_date = comparison_date.tz_localize(tz)
            else:
                comparison_date = comparison_date.tz_convert(tz)
        elif comparison_date.tzinfo is not None:
            comparison_date = comparison_date.tz_localize(None)
        filtered = filtered.loc[filtered["resolved_at"] <= comparison_date + pd.Timedelta(days=1)]
        return filtered.sort_values("resolved_at", ascending=False)

    def _repeat_alert_count_30d(self, history: pd.DataFrame, reference_date: pd.Timestamp) -> int:
        if history.empty:
            return 0
        recent_threshold = reference_date.normalize() - pd.Timedelta(days=30)
        return int((history["resolved_at"] >= recent_threshold).sum())

    def _apply_direct_history_adjustment(
        self,
        score: float,
        latest_feedback: dict[str, Any],
        repeat_count_30d: int,
    ) -> float:
        adjusted = score
        alert_validity = self._string(latest_feedback.get("alert_validity"))
        resolution_status = self._string(latest_feedback.get("resolution_status"))
        business_outcome = self._string(latest_feedback.get("business_outcome"))
        root_cause = self._string(latest_feedback.get("root_cause"))

        if alert_validity == "falso_positivo":
            adjusted -= 20.0
        elif alert_validity == "correcta":
            adjusted += 5.0

        if business_outcome == "pedido_generado":
            adjusted += 12.0
        elif business_outcome == "interes_detectado":
            adjusted += 6.0
        elif business_outcome == "sin_oportunidad":
            adjusted -= 10.0

        if resolution_status == "pospuesto":
            adjusted -= 8.0
        if resolution_status == "descartado":
            adjusted -= 6.0
        if root_cause == "cliente_ya_gestionado":
            adjusted -= 8.0

        if repeat_count_30d >= 2 and alert_validity == "falso_positivo":
            adjusted -= 20.0
        return min(max(adjusted, 0.0), 100.0)

    def _apply_variant_policy_adjustment(self, score: float, policy: dict[str, Any]) -> float:
        adjusted = score
        useful_rate = self._float(policy.get("useful_feedback_rate"))
        false_positive_rate = self._float(policy.get("false_positive_rate"))
        top_outcome = self._string(policy.get("top_business_outcome"))

        if false_positive_rate >= 0.5:
            adjusted -= 10.0
        elif useful_rate >= 0.6:
            adjusted += 5.0

        if top_outcome == "pedido_generado":
            adjusted += 5.0
        elif top_outcome == "sin_oportunidad":
            adjusted -= 4.0
        return min(max(adjusted, 0.0), 100.0)

    def _suppression_until_from_feedback_row(self, feedback_row: dict[str, Any]) -> pd.Timestamp | None:
        service = DelegateFeedbackService(self.project_root)
        return service.suppression_until_for_feedback(feedback_row)

    def _last_delegate_outcome_text(self, feedback_row: dict[str, Any]) -> str:
        outcome = self._string(feedback_row.get("business_outcome"))
        validity = self._string(feedback_row.get("alert_validity"))
        if outcome and validity:
            return f"{outcome} / {validity}"
        return outcome or validity

    @staticmethod
    def _compose_hint(hints: list[str]) -> str:
        deduped: list[str] = []
        for hint in hints:
            text = hint.strip()
            if text and text not in deduped:
                deduped.append(text)
        return " ".join(deduped[:2])

    @staticmethod
    def _human_factor_label(name: str) -> str:
        mapping = {
            "inactivity_score": "inactividad reciente",
            "volume_drift_score": "caida de volumen",
            "interval_drift_score": "alargamiento del ciclo de compra",
            "peer_drift_score": "peor comportamiento frente a clientes parecidos",
            "client_product_embedding_cosine": "baja afinidad historica",
            "client_product_preference_gap": "gap entre demanda observada y afinidad esperada",
            "gap_ratio": "caida frente a la demanda esperada",
            "confidence_factor": "alta confianza del forecast",
            "leakage_component": "presion de leakage",
            "value_component": "alto valor del cliente",
            "urgency_component": "urgencia comercial",
            "confidence_component": "confianza de la oportunidad",
            "purchase_probability": "alta probabilidad de recompra",
            "days_until_expected_purchase": "proximidad de la siguiente compra",
            "expected_interval_days": "patron de recompra conocido",
        }
        return mapping.get(name, "")

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

    @staticmethod
    def _is_missing_value(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value == ""
        try:
            return bool(pd.isna(value))
        except TypeError:
            return False

    @staticmethod
    def _date_or_none(value: Any) -> date | None:
        if value in (None, "", pd.NaT):
            return None
        parsed = pd.Timestamp(value)
        if pd.isna(parsed):
            return None
        return parsed.date()


def build_global_alert_queue(
    mode: str,
    *,
    project_root: Path,
) -> dict[str, Path]:
    service = GlobalPrioritizationService(project_root)
    full_queue = service.build_full_queue(mode)
    queue = full_queue if mode != "daily" else service._filter_new_daily_alerts(
        full_queue,
        previous_full_queue=service._load_previous_daily_full_queue(mode),
    )
    return service.persist_queue(queue, mode, full_queue=full_queue)
