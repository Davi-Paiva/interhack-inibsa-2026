from __future__ import annotations

"""Client data loader."""
import csv
from pathlib import Path
from typing import List

from ..models import Client


def _float_or_zero(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    return float(value) if value not in ("", None) else 0.0


def load_clients(file_path: str | Path) -> List[Client]:
    """Load clients from CSV file.
    
    Args:
        file_path: Path to the clients CSV file
        
    Returns:
        List of Client objects
    """
    clients = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            client = Client(
                client_id=row['client_id'],
                postal_code=row['postal_code'],
                province=row['province'],
                customer_total_revenue=float(row['customer_total_revenue']),
                customer_total_orders=int(row['customer_total_orders']),
                customer_avg_ticket=float(row['customer_avg_ticket']),
                customer_frequency=float(row['customer_frequency']),
                customer_frequency_log1p=float(row['customer_frequency_log1p']),
                days_since_last_order=int(row['days_since_last_order']),
                is_active_customer=row['is_active_customer'].lower() in ('true', '1', 'yes'),
                return_rate_30d=float(row['return_rate_30d']),
                campaign_lift=float(row['campaign_lift']),
                coefficient_variation_30d=float(row['coefficient_variation_30d']),
                client_embedding_0=_float_or_zero(row, 'client_embedding_0'),
                client_embedding_1=_float_or_zero(row, 'client_embedding_1'),
                client_embedding_2=_float_or_zero(row, 'client_embedding_2'),
                client_embedding_3=_float_or_zero(row, 'client_embedding_3'),
            )
            clients.append(client)
    
    return clients
