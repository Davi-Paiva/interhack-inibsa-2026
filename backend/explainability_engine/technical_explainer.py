"""Explainer for technical risk assessment outputs."""

from __future__ import annotations

from typing import Any

from .builders import (
    build_entity_id,
    build_explanation_id,
    build_source_row_key,
    format_decimal,
    rank_factors,
)
from .domain import ContributingFactor, ExplanationRecord
from .variants import SOURCE_ENGINES, TECHNICAL_RISK_ASSESSMENT


def _string(value: Any) -> str:
    return "" if value is None else str(value)


def _metric(signal: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = signal.get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def explain_technical_payload(payload: list[dict[str, Any]], *, source_artifact: str) -> list[ExplanationRecord]:
    records: list[ExplanationRecord] = []
    variant = TECHNICAL_RISK_ASSESSMENT
    source_engine = SOURCE_ENGINES[variant]
    for row in payload:
        customer_id = _string(row.get("client_id"))
        product_id = _string(row.get("product_id"))
        drift_signals = row.get("drift_signals") or []
        ranked_signal_factors = [
            ContributingFactor(
                name=_string(signal.get("signal_type")),
                kind="threshold_trigger",
                direction="increase",
                raw_value=_metric(signal, "severity"),
                display_value=format_decimal(signal.get("severity")),
                threshold=signal.get("threshold"),
                weight=_metric(signal, "severity"),
                explanation_text=(
                    f"{_string(signal.get('signal_type'))} triggered at metric "
                    f"{format_decimal(signal.get('metric_value'))} against threshold "
                    f"{format_decimal(signal.get('threshold'))}."
                ),
            )
            for signal in drift_signals
        ]
        factors = rank_factors(
            [
                ContributingFactor(
                    name="inactivity_score",
                    kind="score_component",
                    direction="increase",
                    raw_value=row.get("inactivity_score"),
                    display_value=format_decimal(row.get("inactivity_score")),
                    threshold=None,
                    weight=float(row.get("inactivity_score", 0.0) or 0.0),
                    explanation_text="Higher inactivity score increases technical abandonment risk.",
                ),
                ContributingFactor(
                    name="volume_drift_score",
                    kind="score_component",
                    direction="increase",
                    raw_value=row.get("volume_drift_score"),
                    display_value=format_decimal(row.get("volume_drift_score")),
                    threshold=None,
                    weight=float(row.get("volume_drift_score", 0.0) or 0.0),
                    explanation_text="Recent negative volume trend adds risk pressure.",
                ),
                ContributingFactor(
                    name="interval_drift_score",
                    kind="timing_signal",
                    direction="increase",
                    raw_value=row.get("interval_drift_score"),
                    display_value=format_decimal(row.get("interval_drift_score")),
                    threshold=None,
                    weight=float(row.get("interval_drift_score", 0.0) or 0.0),
                    explanation_text="Purchase interval drift signals that buying cadence is stretching.",
                ),
                ContributingFactor(
                    name="peer_drift_score",
                    kind="business_context",
                    direction="increase",
                    raw_value=row.get("peer_drift_score"),
                    display_value=format_decimal(row.get("peer_drift_score")),
                    threshold=None,
                    weight=float(row.get("peer_drift_score", 0.0) or 0.0),
                    explanation_text="Peer drift shows the relationship is underperforming against comparable peers.",
                ),
                ContributingFactor(
                    name="client_product_embedding_cosine",
                    kind="latent_affinity",
                    direction="decrease",
                    raw_value=row.get("client_product_embedding_cosine"),
                    display_value=format_decimal(row.get("client_product_embedding_cosine")),
                    threshold=None,
                    weight=abs(float(row.get("client_product_embedding_cosine", 0.0) or 0.0)),
                    explanation_text="Latent affinity summarizes how naturally this product fits the client's historical basket.",
                ),
                ContributingFactor(
                    name="client_product_preference_gap",
                    kind="latent_affinity",
                    direction="increase",
                    raw_value=row.get("client_product_preference_gap"),
                    display_value=format_decimal(row.get("client_product_preference_gap")),
                    threshold=None,
                    weight=abs(float(row.get("client_product_preference_gap", 0.0) or 0.0)),
                    explanation_text="Preference gap compares observed demand with embedding-based expected fit for peer-aware context.",
                ),
            ]
            + ranked_signal_factors
        )
        why_text = (
            f"Technical risk score {format_decimal(row.get('risk_score'))} is driven by inactivity and drift signals "
            f"for customer {customer_id} and product {product_id}."
        )
        confidence_text = (
            "This engine is deterministic and does not expose a separate probabilistic confidence score; "
            "interpret confidence through the strength and count of inactivity and drift evidence."
        )
        temporal_summary = (
            f"Expected purchase cycle is {format_decimal(row.get('expected_cycle_days'))} days, while the last order "
            f"was {int(row.get('days_since_last_order', 0) or 0)} days ago, yielding an inactivity ratio of "
            f"{format_decimal(row.get('inactivity_ratio'))}."
        )
        decision_trace = [
            f"Inactivity_score={format_decimal(row.get('inactivity_score'))}",
            f"Volume_drift_score={format_decimal(row.get('volume_drift_score'))}",
            f"Interval_drift_score={format_decimal(row.get('interval_drift_score'))}",
            f"Peer_drift_score={format_decimal(row.get('peer_drift_score'))}",
            f"Peer_group_type={_string(row.get('peer_group_type'))}",
            f"Risk_score={format_decimal(row.get('risk_score'))}",
            f"Priority_score={format_decimal(row.get('priority_score'))}",
        ]
        for signal in drift_signals:
            decision_trace.append(
                f"Drift_signal={_string(signal.get('signal_type'))}:{format_decimal(signal.get('severity'))}"
            )
        source_row_key = build_source_row_key(variant, customer_id, product_id)
        records.append(
            ExplanationRecord(
                explanation_id=build_explanation_id(source_engine, variant, customer_id, product_id),
                source_engine=source_engine,
                alert_variant=variant,
                entity_id=build_entity_id(source_engine, variant, customer_id, product_id),
                customer_id=customer_id,
                product_id=product_id,
                severity_label=_string(row.get("risk_level")) or None,
                priority_label=_string(row.get("priority_level")) or None,
                headline=f"Technical relationship risk for customer {customer_id} and product {product_id}",
                summary_text=(
                    f"Risk level {_string(row.get('risk_level'))} and priority {_string(row.get('priority_level'))} "
                    "come from the existing technical scoring engine and are explained here without recalculation."
                ),
                why_triggered_text=why_text,
                confidence_text=confidence_text,
                temporal_summary_text=temporal_summary,
                contributing_factors=factors,
                supporting_metrics={
                    "risk_score": row.get("risk_score"),
                    "priority_score": row.get("priority_score"),
                    "inactivity_score": row.get("inactivity_score"),
                    "inactivity_ratio": row.get("inactivity_ratio"),
                    "expected_cycle_days": row.get("expected_cycle_days"),
                    "days_since_last_order": row.get("days_since_last_order"),
                    "volume_drift_score": row.get("volume_drift_score"),
                    "interval_drift_score": row.get("interval_drift_score"),
                    "peer_drift_score": row.get("peer_drift_score"),
                    "peer_avg_growth": row.get("peer_avg_growth"),
                    "peer_avg_similarity": row.get("peer_avg_similarity"),
                    "peer_group_type": row.get("peer_group_type"),
                    "potential_gap": row.get("potential_gap"),
                    "drift_signal_count": row.get("drift_signal_count"),
                    "client_product_embedding_cosine": row.get("client_product_embedding_cosine"),
                    "client_product_preference_gap": row.get("client_product_preference_gap"),
                },
                decision_trace=decision_trace,
                source_artifact=source_artifact,
                source_row_key=source_row_key,
            )
        )
    return records
