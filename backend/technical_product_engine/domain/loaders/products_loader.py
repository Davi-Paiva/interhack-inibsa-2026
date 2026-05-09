"""Product data loader."""
import csv
from pathlib import Path
from typing import List

from ..models import Product


def load_products(file_path: str | Path) -> List[Product]:
    """Load products from CSV file.
    
    Args:
        file_path: Path to the products CSV file
        
    Returns:
        List of Product objects
    """
    products = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            product = Product(
                product_id=row['product_id'],
                analytic_block=row['analytic_block'],
                category=row['category'],
                family=row['family'],
                product_total_revenue=float(row['product_total_revenue']),
                product_total_units=int(row['product_total_units']),
                product_frequency=float(row['product_frequency']),
                rolling_sales_30d=float(row['rolling_sales_30d']),
                product_growth_30d=float(row['product_growth_30d']),
                product_return_rate=float(row['product_return_rate']),
                product_customer_count=int(row['product_customer_count'])
            )
            products.append(product)
    
    return products
