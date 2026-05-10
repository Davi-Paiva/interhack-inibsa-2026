"""
Domain models for the technical product engine.

This module contains the core data models and entities used throughout
the technical product engine system.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional, List


@dataclass
class Campaign:
    """Campaign data model."""
    campaign_id: str
    start_date: date
    end_date: date
    campaign_duration_days: int


@dataclass
class Client:
    """Client data model."""
    client_id: str
    postal_code: str
    province: str
    customer_total_revenue: float
    customer_total_orders: int
    customer_avg_ticket: float
    customer_frequency: float
    customer_frequency_log1p: float
    days_since_last_order: int
    is_active_customer: bool
    return_rate_30d: float
    campaign_lift: float
    coefficient_variation_30d: float


@dataclass
class Potential:
    """Potential data model."""
    client_id: str
    family: str
    product_category: str
    potential_h: float
    current_sales: float
    potential_gap: float
    capture_ratio: float


@dataclass
class Product:
    """Product data model."""
    product_id: str
    analytic_block: str
    category: str
    family: str
    product_total_revenue: float
    product_total_units: int
    product_frequency: float
    rolling_sales_30d: float
    product_growth_30d: float
    product_return_rate: float
    product_customer_count: int


@dataclass
class SalesEnriched:
    """Sales enriched data model."""
    invoice_id: str
    date: date
    client_id: str
    product_id: str
    units: int
    sales_value: float
    is_return: bool
    is_campaign_period: bool
    campaign_id: Optional[str]
    month: int
    quarter: int
    weekday: int
    is_month_end: bool
    is_quarter_end: bool
    rolling_sales_7d: float
    sales_delta_vs_7d: float


@dataclass
class ClientProductFeatures:
    """Client-product features data model."""
    client_id: str
    product_id: str
    rolling_sales_30d: float
    sales_growth_30d: float
    days_since_last_product_order: int
    client_product_frequency: float
    client_product_avg_ticket: float
    client_product_return_rate: float
    campaign_lift_product: float
    client_product_total_revenue: float
    client_product_total_orders: int


@dataclass
class ClientProductContext:
    """Unified context containing all relevant data for a client-product relationship.
    
    This aggregates data from multiple sources into a single object to avoid
    repeated lookups across different datasets.
    """
    # Core identifiers
    client_id: str
    product_id: str
    
    # Related entities
    client: Client
    product: Product
    features: ClientProductFeatures
    
    # Optional related data
    potential: Optional[Potential] = None
    sales_history: List[SalesEnriched] = None
    
    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.sales_history is None:
            self.sales_history = []


