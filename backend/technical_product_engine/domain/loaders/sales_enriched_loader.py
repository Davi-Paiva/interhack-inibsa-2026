from __future__ import annotations

"""Sales enriched data loader."""
import csv
from datetime import datetime
from pathlib import Path
from typing import List

from ..models import SalesEnriched


def load_sales_enriched(file_path: str | Path) -> List[SalesEnriched]:
    """Load sales enriched data from CSV file.
    
    Args:
        file_path: Path to the sales enriched CSV file
        
    Returns:
        List of SalesEnriched objects
    """
    sales = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Handle optional campaign_id
            campaign_id = row['campaign_id'] if row['campaign_id'] else None
            
            sale = SalesEnriched(
                invoice_id=row['invoice_id'],
                date=datetime.strptime(row['date'], '%Y-%m-%d').date(),
                client_id=row['client_id'],
                product_id=row['product_id'],
                units=int(row['units']),
                sales_value=float(row['sales_value']),
                is_return=row['is_return'].lower() in ('true', '1', 'yes'),
                is_campaign_period=row['is_campaign_period'].lower() in ('true', '1', 'yes'),
                campaign_id=campaign_id,
                month=int(row['month']),
                quarter=int(row['quarter']),
                weekday=int(row['weekday']),
                is_month_end=row['is_month_end'].lower() in ('true', '1', 'yes'),
                is_quarter_end=row['is_quarter_end'].lower() in ('true', '1', 'yes'),
                rolling_sales_7d=float(row['rolling_sales_7d']),
                sales_delta_vs_7d=float(row['sales_delta_vs_7d'])
            )
            sales.append(sale)
    
    return sales
