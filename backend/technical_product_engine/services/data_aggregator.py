"""Data aggregation service for loading and organizing product data."""
import logging
from pathlib import Path
from typing import Dict, List, Any

from ..domain.loaders import (
    load_campaigns,
    load_clients,
    load_client_product_features,
    load_potential,
    load_products,
    load_sales_enriched,
)
from ..domain.models import (
    Campaign,
    Client,
    ClientProductFeatures,
    ClientProductContext,
    Potential,
    Product,
    SalesEnriched,
)

logger = logging.getLogger(__name__)


class DataAggregator:
    """Service for loading and aggregating product data from CSV files."""
    
    def __init__(self, data_dir: str | Path):
        """Initialize the aggregator with data directory path.
        
        Args:
            data_dir: Path to the directory containing CSV files
        """
        self.data_dir = Path(data_dir)
        
        # Data containers
        self.campaigns: List[Campaign] = []
        self.clients: List[Client] = []
        self.client_product_features: List[ClientProductFeatures] = []
        self.potentials: List[Potential] = []
        self.products: List[Product] = []
        self.sales_enriched: List[SalesEnriched] = []
        
    def load_all_data(self) -> None:
        """Load all data from CSV files."""
        logger.info("Starting data loading process...")
        
        # Load campaigns
        campaigns_path = self.data_dir / "campaigns.csv"
        if campaigns_path.exists():
            logger.info(f"Loading campaigns from {campaigns_path}")
            self.campaigns = load_campaigns(campaigns_path)
            logger.info(f"Loaded {len(self.campaigns)} campaigns")
        else:
            logger.warning(f"Campaigns file not found: {campaigns_path}")
        
        # Load clients
        clients_path = self.data_dir / "clients.csv"
        if clients_path.exists():
            logger.info(f"Loading clients from {clients_path}")
            self.clients = load_clients(clients_path)
            logger.info(f"Loaded {len(self.clients)} clients")
        else:
            logger.warning(f"Clients file not found: {clients_path}")
        
        # Load potential
        potential_path = self.data_dir / "potential.csv"
        if potential_path.exists():
            logger.info(f"Loading potential from {potential_path}")
            self.potentials = load_potential(potential_path)
            logger.info(f"Loaded {len(self.potentials)} potential records")
        else:
            logger.warning(f"Potential file not found: {potential_path}")
        
        # Load products
        products_path = self.data_dir / "products.csv"
        if products_path.exists():
            logger.info(f"Loading products from {products_path}")
            self.products = load_products(products_path)
            logger.info(f"Loaded {len(self.products)} products")
        else:
            logger.warning(f"Products file not found: {products_path}")
        
        # Load sales enriched
        sales_enriched_path = self.data_dir / "sales_enriched.csv"
        if sales_enriched_path.exists():
            logger.info(f"Loading sales enriched from {sales_enriched_path}")
            self.sales_enriched = load_sales_enriched(sales_enriched_path)
            logger.info(f"Loaded {len(self.sales_enriched)} sales records")
        else:
            logger.warning(f"Sales enriched file not found: {sales_enriched_path}")
        
        # Load client product features
        client_product_features_path = self.data_dir / "client_product_features.csv"
        if client_product_features_path.exists():
            logger.info(f"Loading client product features from {client_product_features_path}")
            self.client_product_features = load_client_product_features(client_product_features_path)
            logger.info(f"Loaded {len(self.client_product_features)} client-product feature records")
        else:
            logger.warning(f"Client product features file not found: {client_product_features_path}")
        
        logger.info("Data loading complete!")
        self._print_summary()
    
    def _print_summary(self) -> None:
        """Print a summary of loaded data."""
        logger.info("=" * 50)
        logger.info("DATA LOADING SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Campaigns:                {len(self.campaigns):,}")
        logger.info(f"Clients:                  {len(self.clients):,}")
        logger.info(f"Potential Records:        {len(self.potentials):,}")
        logger.info(f"Products:                 {len(self.products):,}")
        logger.info(f"Sales Records:            {len(self.sales_enriched):,}")
        logger.info(f"Client-Product Features:  {len(self.client_product_features):,}")
        logger.info("=" * 50)
    
    def get_data_summary(self) -> Dict[str, int]:
        """Get a summary of loaded data counts.
        
        Returns:
            Dictionary with data counts
        """
        return {
            'campaigns': len(self.campaigns),
            'clients': len(self.clients),
            'potentials': len(self.potentials),
            'products': len(self.products),
            'sales_enriched': len(self.sales_enriched),
            'client_product_features': len(self.client_product_features),
        }
    
    def get_technical_products(self, analytic_block: str = "Productos Técnicos") -> List[Product]:
        """Filter products by analytic block.
        
        Args:
            analytic_block: The analytic block to filter by (default: "Productos Técnicos")
            
        Returns:
            List of products in the specified analytic block
        """
        logger.info(f"Filtering products by analytic_block: '{analytic_block}'")
        filtered = [p for p in self.products if p.analytic_block == analytic_block]
        logger.info(f"Found {len(filtered)} products in '{analytic_block}' block")
        return filtered
    
    def filter_by_technical_products(self, analytic_block: str = "Productos Técnicos") -> Dict[str, List[Any]]:
        """Filter all datasets to include only products from specified analytic block.
        
        Args:
            analytic_block: The analytic block to filter by (default: "Productos Técnicos")
            
        Returns:
            Dictionary with filtered datasets
        """
        technical_products = self.get_technical_products(analytic_block=analytic_block)
        technical_product_ids = {p.product_id for p in technical_products}
        
        logger.info(f"Filtering data for {len(technical_product_ids)} technical products")
        
        filtered_data = {
            'products': technical_products,
            'sales_enriched': [s for s in self.sales_enriched if s.product_id in technical_product_ids],
            'client_product_features': [f for f in self.client_product_features if f.product_id in technical_product_ids],
        }
        
        # Get unique clients from filtered sales
        client_ids = {s.client_id for s in filtered_data['sales_enriched']}
        filtered_data['clients'] = [c for c in self.clients if c.client_id in client_ids]
        
        # Get potentials for those clients
        filtered_data['potentials'] = [p for p in self.potentials if p.client_id in client_ids]
        
        # Keep all campaigns (they're not product-specific)
        filtered_data['campaigns'] = self.campaigns
        
        logger.info(f"Filtered results: {len(filtered_data['products'])} products, "
                   f"{len(filtered_data['sales_enriched'])} sales, "
                   f"{len(filtered_data['clients'])} clients")
        
        return filtered_data
    
    def build_client_product_contexts(
        self, 
        technical_only: bool = True,
        analytic_block: str = "Productos Técnicos"
    ) -> List[ClientProductContext]:
        """Build unified contexts for all client-product relationships.
        
        Args:
            technical_only: If True, only build contexts for specified analytic block
            analytic_block: The analytic block to filter by when technical_only is True
            
        Returns:
            List of ClientProductContext objects
        """
        logger.info(f"Building client-product contexts (technical_only={technical_only}, block='{analytic_block}')")
        
        # Build lookup dictionaries for O(1) access
        clients_map = {c.client_id: c for c in self.clients}
        products_map = {p.product_id: p for p in self.products}
        
        # Build potential lookup by (client_id, product_category)
        # Match potential.product_category to product.category
        potential_map = {}
        for p in self.potentials:
            key = (p.client_id, p.product_category)
            potential_map[key] = p
        
        # Group sales by (client_id, product_id)
        sales_map = {}
        for sale in self.sales_enriched:
            key = (sale.client_id, sale.product_id)
            if key not in sales_map:
                sales_map[key] = []
            sales_map[key].append(sale)
        
        # Filter features if technical only
        features_to_process = self.client_product_features
        if technical_only:
            technical_product_ids = {
                p.product_id for p in self.products 
                if p.analytic_block == analytic_block
            }
            logger.info(f"Filtering for {len(technical_product_ids)} products in '{analytic_block}' block")
            features_to_process = [f for f in features_to_process if f.product_id in technical_product_ids]
            logger.info(f"Filtered to {len(features_to_process)} client-product features")
        
        # Build contexts
        contexts = []
        for features in features_to_process:
            client = clients_map.get(features.client_id)
            product = products_map.get(features.product_id)
            
            if not client or not product:
                logger.warning(f"Missing data for {features.client_id}-{features.product_id}")
                continue
            
            # Find matching potential by product category
            potential = potential_map.get((features.client_id, product.category))
            
            # Get sales history
            sales_history = sales_map.get((features.client_id, features.product_id), [])
            
            context = ClientProductContext(
                client_id=features.client_id,
                product_id=features.product_id,
                client=client,
                product=product,
                features=features,
                potential=potential,
                sales_history=sales_history
            )
            contexts.append(context)
        
        logger.info(f"Built {len(contexts)} client-product contexts")
        return contexts
    
    def compute_peer_metrics(self, contexts: List[ClientProductContext]) -> Dict[str, Any]:
        """Compute peer metrics for drift detection.
        
        Calculates average growth rates per product across all clients
        to enable peer-based drift detection.
        
        Args:
            contexts: List of client-product contexts
            
        Returns:
            Dictionary with peer metrics by product_id
        """
        from collections import defaultdict
        from ..drift_detection.peer_drift import PeerMetrics
        
        logger.info(f"Computing peer metrics for {len(contexts)} contexts")
        
        # Group contexts by product_id
        product_contexts = defaultdict(list)
        for ctx in contexts:
            product_contexts[ctx.product_id].append(ctx)
        
        # Calculate peer metrics for each product
        peer_metrics = {}
        for product_id, product_ctxs in product_contexts.items():
            # Extract growth rates from contexts
            growth_rates = []
            for ctx in product_ctxs:
                if ctx.features and ctx.features.sales_growth_30d is not None:
                    growth_rates.append(ctx.features.sales_growth_30d)
            
            if len(growth_rates) < 5:  # Minimum sample size
                continue
            
            # Calculate statistics
            import statistics
            avg_growth = statistics.mean(growth_rates)
            std_growth = statistics.stdev(growth_rates) if len(growth_rates) > 1 else 0.0
            
            peer_metrics[product_id] = PeerMetrics(
                peer_avg_growth=avg_growth,
                peer_std_growth=std_growth,
                peer_count=len(growth_rates)
            )
        
        logger.info(f"Computed peer metrics for {len(peer_metrics)} products")
        return peer_metrics
