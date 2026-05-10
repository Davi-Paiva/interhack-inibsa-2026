from __future__ import annotations

"""Client-product features data loader."""
import csv
from pathlib import Path
from typing import List

from ..models import ClientProductFeatures


def _float_or_zero(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    return float(value) if value not in ("", None) else 0.0


def load_client_product_features(file_path: str | Path) -> List[ClientProductFeatures]:
    """Load client-product features from CSV file.
    
    Args:
        file_path: Path to the client product features CSV file
        
    Returns:
        List of ClientProductFeatures objects
    """
    features = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            feature = ClientProductFeatures(
                client_id=row['client_id'],
                product_id=row['product_id'],
                rolling_sales_30d=float(row['rolling_sales_30d']),
                sales_growth_30d=float(row['sales_growth_30d']),
                days_since_last_product_order=int(row['days_since_last_product_order']),
                client_product_frequency=float(row['client_product_frequency']),
                client_product_avg_ticket=float(row['client_product_avg_ticket']),
                client_product_return_rate=float(row['client_product_return_rate']),
                campaign_lift_product=float(row['campaign_lift_product']),
                client_product_total_revenue=float(row['client_product_total_revenue']),
                client_product_total_orders=int(row['client_product_total_orders']),
                client_product_embedding_score=_float_or_zero(row, 'client_product_embedding_score'),
                client_product_embedding_cosine=_float_or_zero(row, 'client_product_embedding_cosine'),
                client_product_preference_gap=_float_or_zero(row, 'client_product_preference_gap'),
            )
            features.append(feature)
    
    return features
