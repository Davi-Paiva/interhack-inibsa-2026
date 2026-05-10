"""Persistence and lightweight learning for delegate feedback."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .domain import DelegateFeedbackRecord


FEEDBACK_COLUMNS = [
    "feedback_id",
    "global_alert_id",
    "source_engine",
    "canonical_variant",
    "customer_id",
    "product_id",
    "delegate_id",
    "resolution_status",
    "alert_validity",
    "action_taken",
    "business_outcome",
    "root_cause",
    "free_note",
    "resolved_at",
    "created_at",
    "global_priority_score",
    "global_priority_band",
    "recommended_action",
    "alert_reason_summary",
]

RESOLUTION_STATUS_OPTIONS = ["contactado", "descartado", "pospuesto", "sin_respuesta"]
ALERT_VALIDITY_OPTIONS = ["correcta", "dudosa", "falso_positivo"]
ACTION_TAKEN_OPTIONS = ["llamada", "email", "visita", "sin_accion"]
BUSINESS_OUTCOME_OPTIONS = [
    "pedido_generado",
    "interes_detectado",
    "sin_oportunidad",
    "incidencia_operativa",
    "otro",
]
ROOT_CAUSE_OPTIONS_BY_VARIANT = {
    "commodity.next_purchase": [
        "recompra_inminente_confirmada",
        "cliente_ya_gestionado",
        "timing_incorrecto",
        "stock_ya_cubierto",
        "sin_contexto_comercial",
    ],
    "commodity.capture_opportunity": [
        "potencial_real",
        "cliente_ya_gestionado",
        "prioridad_baja",
        "timing_incorrecto",
        "sin_presupuesto",
    ],
    "commodity.demand_leakage": [
        "caida_real_de_consumo",
        "cliente_ya_gestionado",
        "estacionalidad_o_campana",
        "pedido_desplazado",
        "falso_positivo_operativo",
    ],
    "technical.risk_assessment": [
        "abandono_real",
        "cliente_ya_gestionado",
        "incidencia_operativa",
        "ciclo_de_compra_largo",
        "falso_positivo_operativo",
    ],
}
DEFAULT_ROOT_CAUSE_OPTIONS = [
    "cliente_ya_gestionado",
    "timing_incorrecto",
    "sin_oportunidad",
    "incidencia_operativa",
    "otro",
]


class DelegateFeedbackService:
    """Store delegate feedback and build lightweight policy artifacts."""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()

    @property
    def output_root(self) -> Path:
        return self.project_root / "backend" / "delegate_feedback" / "output"

    def output_dir_for_mode(self, mode: str) -> Path:
        path = self.output_root / mode
        path.mkdir(parents=True, exist_ok=True)
        return path

    def feedback_json_path(self, mode: str) -> Path:
        return self.output_dir_for_mode(mode) / "alert_feedback.json"

    def feedback_csv_path(self, mode: str) -> Path:
        return self.output_dir_for_mode(mode) / "alert_feedback.csv"

    def policy_json_path(self, mode: str) -> Path:
        return self.output_dir_for_mode(mode) / "feedback_policy.json"

    def load_feedback_frame(self, mode: str) -> pd.DataFrame:
        json_path = self.feedback_json_path(mode)
        if not json_path.exists():
            return pd.DataFrame(columns=FEEDBACK_COLUMNS)
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        frame = pd.DataFrame(payload)
        for column in FEEDBACK_COLUMNS:
            if column not in frame.columns:
                frame[column] = None
        return frame[FEEDBACK_COLUMNS]

    def load_policy(self, mode: str) -> dict[str, Any]:
        path = self.policy_json_path(mode)
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def root_cause_options(self, canonical_variant: str) -> list[str]:
        return ROOT_CAUSE_OPTIONS_BY_VARIANT.get(canonical_variant, DEFAULT_ROOT_CAUSE_OPTIONS)

    def record_feedback(
        self,
        mode: str,
        alert_row: dict[str, Any],
        *,
        delegate_id: str,
        resolution_status: str,
        alert_validity: str,
        action_taken: str,
        business_outcome: str,
        root_cause: str,
        free_note: str = "",
        resolved_at: datetime | None = None,
        rebuild_policy: bool = True,
    ) -> dict[str, Path]:
        record = self._build_feedback_record(
            alert_row,
            delegate_id=delegate_id,
            resolution_status=resolution_status,
            alert_validity=alert_validity,
            action_taken=action_taken,
            business_outcome=business_outcome,
            root_cause=root_cause,
            free_note=free_note,
            resolved_at=resolved_at,
        )
        frame = self.load_feedback_frame(mode)
        updated = pd.concat([frame, pd.DataFrame([record.to_json_dict()])], ignore_index=True)
        updated = updated.sort_values(["resolved_at", "created_at", "feedback_id"], ascending=[True, True, True])

        json_path = self.feedback_json_path(mode)
        csv_path = self.feedback_csv_path(mode)
        json_path.write_text(
            json.dumps(updated.to_dict(orient="records"), indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        updated.to_csv(csv_path, index=False)

        paths = {"json": json_path, "csv": csv_path}
        if rebuild_policy:
            paths["policy"] = self.build_policy(mode)
        return paths

    def build_policy(self, mode: str) -> Path:
        frame = self.load_feedback_frame(mode)
        if frame.empty:
            payload = {
                "mode": mode,
                "generated_at": datetime.now(UTC).isoformat(),
                "by_variant": {},
            }
        else:
            payload = {
                "mode": mode,
                "generated_at": datetime.now(UTC).isoformat(),
                "by_variant": {},
            }
            for canonical_variant, variant_frame in frame.groupby("canonical_variant", dropna=False):
                variant_name = self._string(canonical_variant)
                if not variant_name:
                    continue
                helpful_rate = float(
                    (
                        (variant_frame["alert_validity"] == "correcta")
                        | (variant_frame["business_outcome"].isin(["pedido_generado", "interes_detectado"]))
                    ).mean()
                )
                false_positive_rate = float((variant_frame["alert_validity"] == "falso_positivo").mean())
                top_action = self._mode_or_default(variant_frame["action_taken"], default="sin_accion")
                top_outcome = self._mode_or_default(variant_frame["business_outcome"], default="otro")
                top_root_cause = self._mode_or_default(variant_frame["root_cause"], default="otro")
                payload["by_variant"][variant_name] = {
                    "feedback_count": int(len(variant_frame)),
                    "useful_feedback_rate": round(helpful_rate, 4),
                    "false_positive_rate": round(false_positive_rate, 4),
                    "top_action_taken": top_action,
                    "top_business_outcome": top_outcome,
                    "top_root_cause": top_root_cause,
                    "delegate_hint": self._policy_delegate_hint(
                        helpful_rate=helpful_rate,
                        false_positive_rate=false_positive_rate,
                        top_action_taken=top_action,
                        top_business_outcome=top_outcome,
                    ),
                }

        path = self.policy_json_path(mode)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
        return path

    def load_global_queue(self, mode: str) -> list[dict[str, Any]]:
        path = self.project_root / "backend" / "global_prioritization" / "output" / mode / "global_alert_queue.json"
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def find_alert_row(self, mode: str, global_alert_id: str) -> dict[str, Any] | None:
        for row in self.load_global_queue(mode):
            if self._string(row.get("global_alert_id")) == global_alert_id:
                return row
        return None

    def _build_feedback_record(
        self,
        alert_row: dict[str, Any],
        *,
        delegate_id: str,
        resolution_status: str,
        alert_validity: str,
        action_taken: str,
        business_outcome: str,
        root_cause: str,
        free_note: str,
        resolved_at: datetime | None,
    ) -> DelegateFeedbackRecord:
        resolved_at_value = resolved_at or datetime.now(UTC)
        created_at_value = datetime.now(UTC)
        raw = "|".join(
            [
                self._string(alert_row.get("global_alert_id")),
                self._string(delegate_id),
                resolved_at_value.isoformat(),
                self._string(root_cause),
            ]
        )
        feedback_id = f"fb_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:16]}"
        return DelegateFeedbackRecord(
            feedback_id=feedback_id,
            global_alert_id=self._string(alert_row.get("global_alert_id")),
            source_engine=self._string(alert_row.get("source_engine")),
            canonical_variant=self._string(alert_row.get("canonical_variant")),
            customer_id=self._string(alert_row.get("customer_id")),
            product_id=self._string(alert_row.get("product_id")),
            delegate_id=self._string(delegate_id),
            resolution_status=self._validated_option(
                resolution_status,
                RESOLUTION_STATUS_OPTIONS,
                field_name="resolution_status",
            ),
            alert_validity=self._validated_option(
                alert_validity,
                ALERT_VALIDITY_OPTIONS,
                field_name="alert_validity",
            ),
            action_taken=self._validated_option(action_taken, ACTION_TAKEN_OPTIONS, field_name="action_taken"),
            business_outcome=self._validated_option(
                business_outcome,
                BUSINESS_OUTCOME_OPTIONS,
                field_name="business_outcome",
            ),
            root_cause=self._string(root_cause) or "otro",
            free_note=self._string(free_note).strip()[:280],
            resolved_at=resolved_at_value,
            created_at=created_at_value,
            global_priority_score=self._float(alert_row.get("global_priority_score")),
            global_priority_band=self._string(alert_row.get("global_priority_band")),
            recommended_action=self._string(alert_row.get("recommended_action")),
            alert_reason_summary=self._string(alert_row.get("alert_reason_summary")),
        )

    def suppression_until_for_feedback(self, feedback_row: dict[str, Any]) -> pd.Timestamp | None:
        resolved_at = pd.to_datetime(feedback_row.get("resolved_at"), errors="coerce")
        if pd.isna(resolved_at):
            return None
        alert_validity = self._string(feedback_row.get("alert_validity"))
        resolution_status = self._string(feedback_row.get("resolution_status"))
        business_outcome = self._string(feedback_row.get("business_outcome"))
        root_cause = self._string(feedback_row.get("root_cause"))

        if alert_validity == "falso_positivo":
            return resolved_at.normalize() + pd.Timedelta(days=14)
        if root_cause == "cliente_ya_gestionado":
            return resolved_at.normalize() + pd.Timedelta(days=10)
        if resolution_status == "pospuesto":
            return resolved_at.normalize() + pd.Timedelta(days=3)
        if resolution_status == "descartado" or business_outcome == "sin_oportunidad":
            return resolved_at.normalize() + pd.Timedelta(days=7)
        return None

    @staticmethod
    def _mode_or_default(series: pd.Series, *, default: str) -> str:
        non_empty = [str(value) for value in series.fillna("").tolist() if str(value)]
        if not non_empty:
            return default
        counts = pd.Series(non_empty).value_counts()
        return str(counts.index[0]) if not counts.empty else default

    @staticmethod
    def _policy_delegate_hint(
        *,
        helpful_rate: float,
        false_positive_rate: float,
        top_action_taken: str,
        top_business_outcome: str,
    ) -> str:
        if false_positive_rate >= 0.5:
            return "Este tipo de alerta acumula bastante ruido reciente; valida motivo y timing antes de contactar."
        if top_business_outcome == "pedido_generado":
            return (
                f"Las alertas similares convierten mejor cuando se actuan rapido, normalmente con {top_action_taken}."
            )
        if top_business_outcome == "interes_detectado":
            return f"Las alertas similares suelen abrir conversacion cuando se gestionan con {top_action_taken}."
        if helpful_rate >= 0.6:
            return "La senal ha sido util en el historico reciente; prioriza una gestion comercial clara."
        return "Usa esta alerta como senal de revision y confirma con contexto comercial antes de escalar."

    @staticmethod
    def _validated_option(value: str, options: list[str], *, field_name: str) -> str:
        if value not in options:
            raise ValueError(f"Invalid {field_name}: {value!r}. Expected one of {options!r}.")
        return value

    @staticmethod
    def _string(value: Any) -> str:
        return "" if value is None else str(value)

    @staticmethod
    def _float(value: Any) -> float:
        try:
            numeric = float(value)
            if pd.isna(numeric):
                return 0.0
            return numeric
        except (TypeError, ValueError):
            return 0.0
