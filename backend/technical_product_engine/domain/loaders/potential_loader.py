from __future__ import annotations

"""Potential data loader."""
import csv
from pathlib import Path
from typing import List

from ..models import Potential


def load_potential(file_path: str | Path) -> List[Potential]:
    """Load potential data from CSV file.
    
    Args:
        file_path: Path to the potential CSV file
        
    Returns:
        List of Potential objects
    """
    potentials = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            potential = Potential(
                client_id=row['client_id'],
                family=row['family'],
                product_category=row['product_category'],
                potential_h=float(row['potential_h']),
                current_sales=float(row['current_sales']),
                potential_gap=float(row['potential_gap']),
                capture_ratio=float(row['capture_ratio'])
            )
            potentials.append(potential)
    
    return potentials
