"""Client data loader."""
import csv
from pathlib import Path
from typing import List

from ..models import Client


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
                days_since_last_order=int(row['days_since_last_order']),
                return_rate_30d=float(row['return_rate_30d']),
                campaign_lift=float(row['campaign_lift']),
                coefficient_variation_30d=float(row['coefficient_variation_30d'])
            )
            clients.append(client)
    
    return clients
