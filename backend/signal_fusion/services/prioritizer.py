from __future__ import annotations

from dataclasses import replace

from ..domain.scoring import clamp, score_to_priority, score_to_urgency
from ..domain.structures import Alert


def final_alert_score(
    *,
    impact_score: float,
    urgency_score: float,
    confidence: float,
    explainability_score: float,
) -> float:
    _ = explainability_score
    score_0_1 = (
        0.45 * clamp(impact_score)
        + 0.35 * clamp(urgency_score)
        + 0.20 * clamp(confidence)
    )
    return round(score_0_1 * 100.0, 2)


def prioritize(alert: Alert) -> Alert:
    score = final_alert_score(
        impact_score=alert.impact_score,
        urgency_score=alert.urgency_score,
        confidence=alert.confidence,
        explainability_score=alert.explainability_score,
    )
    return replace(
        alert,
        priority_score=score,
        priority_level=score_to_priority(score),
        urgency=score_to_urgency(alert.urgency_score),
    )
