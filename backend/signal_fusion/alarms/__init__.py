"""Alarm generators exposed by signal fusion."""

from .account_deterioration import AccountDeteriorationAlarm
from .churn_risk import ChurnRiskAlarm
from .commercial_opportunity_score import CommercialOpportunityScoreAlarm
from .cross_sell_opportunity import CrossSellOpportunityAlarm
from .demand_leakage import DemandLeakageAlarm
from .demand_spike_opportunity import DemandSpikeOpportunityAlarm
from .emerging_strategic_account import EmergingStrategicAccountAlarm
from .high_purchase_probability import HighPurchaseProbabilityAlarm
from .product_mix_drift import ProductMixDriftAlarm
from .purchase_anomaly import PurchaseAnomalyAlarm

DEFAULT_ALARMS = (
    HighPurchaseProbabilityAlarm(),
    DemandSpikeOpportunityAlarm(),
    CrossSellOpportunityAlarm(),
    ChurnRiskAlarm(),
    DemandLeakageAlarm(),
    PurchaseAnomalyAlarm(),
    ProductMixDriftAlarm(),
    CommercialOpportunityScoreAlarm(),
    AccountDeteriorationAlarm(),
    EmergingStrategicAccountAlarm(),
)

__all__ = [
    "DEFAULT_ALARMS",
    "AccountDeteriorationAlarm",
    "ChurnRiskAlarm",
    "CommercialOpportunityScoreAlarm",
    "CrossSellOpportunityAlarm",
    "DemandLeakageAlarm",
    "DemandSpikeOpportunityAlarm",
    "EmergingStrategicAccountAlarm",
    "HighPurchaseProbabilityAlarm",
    "ProductMixDriftAlarm",
    "PurchaseAnomalyAlarm",
]
