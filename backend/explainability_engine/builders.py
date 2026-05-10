"""Shared builders and formatting helpers for explanations."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from .domain import ContributingFactor, ExplanationRecord


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
        if math.isnan(numeric) or math.isinf(numeric):
            return default
        return numeric
    except (TypeError, ValueError):
        return default


def format_decimal(value: Any, digits: int = 2) -> str:
    return f"{_safe_float(value):.{digits}f}"


def format_percent(value: Any, digits: int = 1) -> str:
    return f"{_safe_float(value) * 100:.{digits}f}%"


def canonical_product_id(row: dict[str, Any]) -> str:
    for key in ("product_id", "product_family", "family"):
        value = row.get(key)
        if value is not None and str(value) != "":
            return str(value)
    return ""


def build_source_row_key(alert_variant: str, customer_id: str, product_id: str) -> str:
    return f"{alert_variant}|{customer_id}|{product_id}"


def build_entity_id(source_engine: str, alert_variant: str, customer_id: str, product_id: str) -> str:
    return f"{source_engine}:{build_source_row_key(alert_variant, customer_id, product_id)}"


def build_explanation_id(source_engine: str, alert_variant: str, customer_id: str, product_id: str) -> str:
    raw = build_entity_id(source_engine, alert_variant, customer_id, product_id)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"exp_{digest}"


def rank_factors(factors: list[ContributingFactor]) -> list[ContributingFactor]:
    ordered = sorted(
        factors,
        key=lambda factor: (
            -(factor.weight if factor.weight is not None else _safe_float(factor.raw_value)),
            factor.name,
        ),
    )
    return [
        ContributingFactor(
            name=factor.name,
            kind=factor.kind,
            direction=factor.direction,
            raw_value=factor.raw_value,
            display_value=factor.display_value,
            threshold=factor.threshold,
            weight=factor.weight,
            importance_rank=index + 1,
            explanation_text=factor.explanation_text,
        )
        for index, factor in enumerate(ordered)
    ]


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def explanation_row(record: ExplanationRecord) -> dict[str, Any]:
    payload = record.to_json_dict()
    payload["contributing_factors"] = json_dumps(payload["contributing_factors"])
    payload["supporting_metrics"] = json_dumps(payload["supporting_metrics"])
    payload["decision_trace"] = json_dumps(payload["decision_trace"])
    return payload
