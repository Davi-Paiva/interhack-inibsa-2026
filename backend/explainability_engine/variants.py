"""Supported alert variants and output mappings for explainability."""

from __future__ import annotations


COMMODITY_DEMAND_LEAKAGE = "commodity.demand_leakage"
COMMODITY_CAPTURE_OPPORTUNITY = "commodity.capture_opportunity"
COMMODITY_NEXT_PURCHASE = "commodity.next_purchase"
TECHNICAL_RISK_ASSESSMENT = "technical.risk_assessment"

SUPPORTED_ALERT_VARIANTS = (
    COMMODITY_DEMAND_LEAKAGE,
    COMMODITY_CAPTURE_OPPORTUNITY,
    COMMODITY_NEXT_PURCHASE,
    TECHNICAL_RISK_ASSESSMENT,
)

LABEL_MAPPINGS = {
    COMMODITY_DEMAND_LEAKAGE: {
        "severity_label": "risk_level",
        "priority_label": None,
    },
    COMMODITY_CAPTURE_OPPORTUNITY: {
        "severity_label": "priority_band",
        "priority_label": "priority_band",
    },
    COMMODITY_NEXT_PURCHASE: {
        "severity_label": "priority_band",
        "priority_label": "priority_band",
    },
    TECHNICAL_RISK_ASSESSMENT: {
        "severity_label": "risk_level",
        "priority_label": "priority_level",
    },
}

SOURCE_ENGINES = {
    COMMODITY_DEMAND_LEAKAGE: "commodity_ai_engine",
    COMMODITY_CAPTURE_OPPORTUNITY: "commodity_ai_engine",
    COMMODITY_NEXT_PURCHASE: "commodity_ai_engine",
    TECHNICAL_RISK_ASSESSMENT: "technical_product_engine",
}
