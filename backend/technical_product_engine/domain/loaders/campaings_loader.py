"""Campaign data loader."""
import csv
from datetime import datetime
from pathlib import Path
from typing import List

from ..models import Campaign


def load_campaigns(file_path: str | Path) -> List[Campaign]:
    """Load campaigns from CSV file.
    
    Args:
        file_path: Path to the campaigns CSV file
        
    Returns:
        List of Campaign objects
    """
    campaigns = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            campaign = Campaign(
                campaign_id=row['campaign_id'],
                start_date=datetime.strptime(row['start_date'], '%Y-%m-%d').date(),
                end_date=datetime.strptime(row['end_date'], '%Y-%m-%d').date(),
                campaign_duration_days=int(row['campaign_duration_days'])
            )
            campaigns.append(campaign)
    
    return campaigns
