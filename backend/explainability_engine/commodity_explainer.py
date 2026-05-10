"""Explainers for commodity alert variants."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .builders import (
    build_entity_id,
    build_explanation_id,
    build_source_row_key,
    canonical_product_id,
    format_decimal,
    format_percent,
    rank_factors,
)
from .domain import ContributingFactor, ExplanationRecord
from .variants import (
    COMMODITY_CAPTURE_OPPORTUNITY,
    COMMODITY_DEMAND_LEAKAGE,
    COMMODITY_NEXT_PURCHASE,
    SOURCE_ENGINES,
)


def _string(value: Any) -> str:
    return "" if value is None else str(value)


def explain_leakage_frame(df: pd.DataFrame, *, source_artifact: str) -> list[ExplanationRecord]:
    records: list[ExplanationRecord] = []
    variant = COMMODITY_DEMAND_LEAKAGE
    source_engine = SOURCE_ENGINES[variant]
    for row in df.to_dict(orient="records"):
        customer_id = _string(row.get("customer_id"))
        product_id = canonical_product_id(row)
        factors = rank_factors(
            [
                ContributingFactor(
                    name="gap_ratio",
                    kind="score_component",
                    direction="increase",
                    raw_value=row.get("gap_ratio"),
                    display_value=format_percent(row.get("gap_ratio")),
                    threshold=0.20,
                    weight=1.0,
                    explanation_text="A larger expected-vs-observed gap increases leakage pressure.",
                ),
                ContributingFactor(
                    name="volatility_penalty",
                    kind="score_component",
                    direction="decrease",
                    raw_value=row.get("volatility_penalty"),
                    display_value=format_decimal(row.get("volatility_penalty")),
                    threshold=None,
                    weight=0.8,
                    explanation_text="Higher customer volatility softens the final leakage severity.",
                ),
                ContributingFactor(
                    name="campaign_softener",
                    kind="business_context",
                    direction="decrease",
                    raw_value=row.get("campaign_softener"),
                    display_value=format_decimal(row.get("campaign_softener")),
                    threshold=None,
                    weight=0.6,
                    explanation_text="Campaign uplift can partly explain temporary demand changes.",
                ),
                ContributingFactor(
                    name="return_penalty",
                    kind="business_context",
                    direction="decrease",
                    raw_value=row.get("return_penalty"),
                    display_value=format_decimal(row.get("return_penalty")),
                    threshold=None,
                    weight=0.5,
                    explanation_text="Return behavior reduces confidence that the observed drop is pure leakage.",
                ),
                ContributingFactor(
                    name="confidence_factor",
                    kind="score_component",
                    direction="increase",
                    raw_value=row.get("confidence_factor"),
                    display_value=format_decimal(row.get("confidence_factor")),
                    threshold=None,
                    weight=0.7,
                    explanation_text="Higher forecast confidence makes the leakage signal more reliable.",
                ),
            ]
        )
        gap_units = format_decimal(row.get("gap_units"))
        predicted_sales = format_decimal(row.get("predicted_30d_sales"))
        observed_sales = format_decimal(row.get("observed_30d_sales"))
        leakage_score = format_decimal(row.get("leakage_score"))
        why_text = (
            f"Expected next-30-day demand ({predicted_sales}) is above recent observed 30-day sales "
            f"({observed_sales}), creating a gap of {gap_units} units."
        )
        confidence_text = (
            f"Forecast confidence factor is {format_decimal(row.get('confidence_factor'))}; "
            f"volatility, campaign, and return adjustments were already applied before the final leakage score."
        )
        temporal_summary = "Recent 30-day observed sales are below expected next-30-day demand."
        decision_trace = [
            f"Predicted_30d_sales={predicted_sales}",
            f"Observed_30d_sales={observed_sales}",
            f"Gap_ratio={format_percent(row.get('gap_ratio'))}",
            f"Leakage_score={leakage_score}",
            f"Routing_reason={_string(row.get('routing_reason'))}",
        ]
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
                priority_label=None,
                headline=f"Demand leakage signal for customer {customer_id} and product {product_id}",
                summary_text=(
                    f"Leakage score {leakage_score} reflects a forecasted demand gap after volatility, campaign, "
                    "return, and confidence adjustments."
                ),
                why_triggered_text=why_text,
                confidence_text=confidence_text,
                temporal_summary_text=temporal_summary,
                contributing_factors=factors,
                supporting_metrics={
                    "predicted_30d_sales": row.get("predicted_30d_sales"),
                    "observed_30d_sales": row.get("observed_30d_sales"),
                    "gap_units": row.get("gap_units"),
                    "gap_ratio": row.get("gap_ratio"),
                    "volatility_penalty": row.get("volatility_penalty"),
                    "campaign_softener": row.get("campaign_softener"),
                    "return_penalty": row.get("return_penalty"),
                    "confidence_factor": row.get("confidence_factor"),
                    "leakage_score": row.get("leakage_score"),
                    "is_actionable": row.get("is_actionable"),
                    "routing_reason": row.get("routing_reason"),
                },
                decision_trace=decision_trace,
                source_artifact=source_artifact,
                source_row_key=source_row_key,
            )
        )
    return records


def explain_capture_frame(df: pd.DataFrame, *, source_artifact: str) -> list[ExplanationRecord]:
    records: list[ExplanationRecord] = []
    variant = COMMODITY_CAPTURE_OPPORTUNITY
    source_engine = SOURCE_ENGINES[variant]
    for row in df.to_dict(orient="records"):
        customer_id = _string(row.get("customer_id"))
        product_id = canonical_product_id(row)
        factors = rank_factors(
            [
                ContributingFactor(
                    name="leakage_component",
                    kind="score_component",
                    direction="increase",
                    raw_value=row.get("leakage_component", row.get("leakage_score")),
                    display_value=format_decimal(row.get("leakage_component", row.get("leakage_score"))),
                    threshold=None,
                    weight=0.40,
                    explanation_text="Leakage contributes 40% of the capture ranking.",
                ),
                ContributingFactor(
                    name="value_component",
                    kind="business_context",
                    direction="increase",
                    raw_value=row.get("value_component"),
                    display_value=format_decimal(row.get("value_component")),
                    threshold=None,
                    weight=0.30,
                    explanation_text="Customer value contributes 30% of the capture ranking.",
                ),
                ContributingFactor(
                    name="urgency_component",
                    kind="timing_signal",
                    direction="increase",
                    raw_value=row.get("urgency_component"),
                    display_value=format_decimal(row.get("urgency_component")),
                    threshold=None,
                    weight=0.20,
                    explanation_text="Urgency contributes 20% of the capture ranking.",
                ),
                ContributingFactor(
                    name="confidence_component",
                    kind="score_component",
                    direction="increase",
                    raw_value=row.get("confidence_component"),
                    display_value=format_decimal(row.get("confidence_component")),
                    threshold=None,
                    weight=0.10,
                    explanation_text="Confidence contributes 10% of the capture ranking.",
                ),
            ]
        )
        why_text = (
            f"This opportunity is prioritized because leakage, customer value, urgency, and confidence combine "
            f"into a capture score of {format_decimal(row.get('capture_score'))}."
        )
        confidence_text = (
            f"Confidence component is {format_decimal(row.get('confidence_component'))}; "
            "this influences ranking but does not change the original priority band."
        )
        temporal_summary = (
            f"Priority rank {int(row.get('priority_rank', 0))} reflects current urgency and recent account behavior."
        )
        decision_trace = [
            f"Leakage_component={format_decimal(row.get('leakage_component', row.get('leakage_score')))}",
            f"Value_component={format_decimal(row.get('value_component'))}",
            f"Urgency_component={format_decimal(row.get('urgency_component'))}",
            f"Confidence_component={format_decimal(row.get('confidence_component'))}",
            f"Priority_rank={row.get('priority_rank')}",
        ]
        source_row_key = build_source_row_key(variant, customer_id, product_id)
        records.append(
            ExplanationRecord(
                explanation_id=build_explanation_id(source_engine, variant, customer_id, product_id),
                source_engine=source_engine,
                alert_variant=variant,
                entity_id=build_entity_id(source_engine, variant, customer_id, product_id),
                customer_id=customer_id,
                product_id=product_id,
                severity_label=_string(row.get("priority_band")) or None,
                priority_label=_string(row.get("priority_band")) or None,
                headline=f"Capture opportunity for customer {customer_id} and product {product_id}",
                summary_text=(
                    f"Capture score {format_decimal(row.get('capture_score'))} and rank {row.get('priority_rank')} "
                    "come from the weighted queueing formula already produced by the commodity engine."
                ),
                why_triggered_text=why_text,
                confidence_text=confidence_text,
                temporal_summary_text=temporal_summary,
                contributing_factors=factors,
                supporting_metrics={
                    "capture_score": row.get("capture_score"),
                    "priority_rank": row.get("priority_rank"),
                    "priority_band": row.get("priority_band"),
                    "recommended_action": row.get("recommended_action"),
                    "leakage_component": row.get("leakage_component", row.get("leakage_score")),
                    "value_component": row.get("value_component"),
                    "urgency_component": row.get("urgency_component"),
                    "confidence_component": row.get("confidence_component"),
                },
                decision_trace=decision_trace,
                source_artifact=source_artifact,
                source_row_key=source_row_key,
            )
        )
    return records


def explain_next_purchase_frame(df: pd.DataFrame, *, source_artifact: str) -> list[ExplanationRecord]:
    records: list[ExplanationRecord] = []
    variant = COMMODITY_NEXT_PURCHASE
    source_engine = SOURCE_ENGINES[variant]
    for row in df.to_dict(orient="records"):
        customer_id = _string(row.get("customer_id"))
        product_id = canonical_product_id(row)
        factors = rank_factors(
            [
                ContributingFactor(
                    name="purchase_probability",
                    kind="timing_signal",
                    direction="increase",
                    raw_value=row.get("purchase_probability"),
                    display_value=format_percent(row.get("purchase_probability")),
                    threshold=None,
                    weight=1.0,
                    explanation_text="Higher purchase probability makes the replenishment timing signal stronger.",
                ),
                ContributingFactor(
                    name="days_until_expected_purchase",
                    kind="timing_signal",
                    direction="increase",
                    raw_value=row.get("days_until_expected_purchase"),
                    display_value=f"{int(row.get('days_until_expected_purchase', 0))} days",
                    threshold=None,
                    weight=0.8,
                    explanation_text="Shorter time to the expected purchase increases immediacy.",
                ),
                ContributingFactor(
                    name="estimated_interval_days",
                    kind="timing_signal",
                    direction="neutral",
                    raw_value=row.get("estimated_interval_days"),
                    display_value=f"{format_decimal(row.get('estimated_interval_days'))} days",
                    threshold=None,
                    weight=0.4,
                    explanation_text="The replenishment interval anchors the expected next purchase date.",
                ),
            ]
        )
        expected_date = _string(row.get("expected_next_purchase_date"))
        why_text = (
            f"This signal is explained by the expected replenishment timing: the next purchase is estimated around "
            f"{expected_date} with probability {format_percent(row.get('purchase_probability'))}."
        )
        confidence_text = (
            f"Purchase probability is {format_percent(row.get('purchase_probability'))}; "
            "interpret this as the strength of the timing signal rather than a new classification step."
        )
        temporal_summary = (
            f"Recommended contact window runs from {_string(row.get('contact_window_start'))} to "
            f"{_string(row.get('contact_window_end'))} ahead of the expected date {expected_date}."
        )
        decision_trace = [
            f"Estimated_interval_days={format_decimal(row.get('estimated_interval_days'))}",
            f"Days_until_expected_purchase={row.get('days_until_expected_purchase')}",
            f"Expected_next_purchase_date={expected_date}",
            f"Purchase_probability={format_percent(row.get('purchase_probability'))}",
        ]
        source_row_key = build_source_row_key(variant, customer_id, product_id)
        records.append(
            ExplanationRecord(
                explanation_id=build_explanation_id(source_engine, variant, customer_id, product_id),
                source_engine=source_engine,
                alert_variant=variant,
                entity_id=build_entity_id(source_engine, variant, customer_id, product_id),
                customer_id=customer_id,
                product_id=product_id,
                severity_label=_string(row.get("priority_band")) or None,
                priority_label=_string(row.get("priority_band")) or None,
                headline=f"Next purchase timing signal for customer {customer_id} and product {product_id}",
                summary_text=(
                    f"Expected next purchase date is {expected_date}; the current contact window is "
                    f"{_string(row.get('contact_window_start'))} to {_string(row.get('contact_window_end'))}."
                ),
                why_triggered_text=why_text,
                confidence_text=confidence_text,
                temporal_summary_text=temporal_summary,
                contributing_factors=factors,
                supporting_metrics={
                    "estimated_interval_days": row.get("estimated_interval_days"),
                    "days_until_expected_purchase": row.get("days_until_expected_purchase"),
                    "expected_next_purchase_date": row.get("expected_next_purchase_date"),
                    "purchase_probability": row.get("purchase_probability"),
                    "contact_window_start": row.get("contact_window_start"),
                    "contact_window_end": row.get("contact_window_end"),
                    "contact_recommendation": row.get("contact_recommendation"),
                },
                decision_trace=decision_trace,
                source_artifact=source_artifact,
                source_row_key=source_row_key,
            )
        )
    return records
