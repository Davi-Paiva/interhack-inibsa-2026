"""
Tests for the technical product engine.

This module contains comprehensive tests for models, loaders, and services.
"""
import pytest
import tempfile
from pathlib import Path
from datetime import date
from io import StringIO
import csv

from ..domain.models import (
    Campaign,
    Client,
    ClientProductFeatures,
    ClientProductContext,
    Potential,
    Product,
    SalesEnriched,
)
from ..domain.loaders import (
    load_campaigns,
    load_clients,
    load_client_product_features,
    load_potential,
    load_products,
    load_sales_enriched,
)
from ..services import DataAggregator


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_campaigns_csv(temp_dir):
    """Create a sample campaigns CSV file."""
    csv_path = temp_dir / "campaigns.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'campaign_id', 'start_date', 'end_date', 'campaign_duration_days'
        ])
        writer.writeheader()
        writer.writerows([
            {'campaign_id': 'C001', 'start_date': '2026-01-01', 'end_date': '2026-01-31', 'campaign_duration_days': '30'},
            {'campaign_id': 'C002', 'start_date': '2026-02-01', 'end_date': '2026-02-28', 'campaign_duration_days': '27'},
        ])
    return csv_path


@pytest.fixture
def sample_clients_csv(temp_dir):
    """Create a sample clients CSV file."""
    csv_path = temp_dir / "clients.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'client_id', 'postal_code', 'province', 'customer_total_revenue',
            'customer_total_orders', 'customer_avg_ticket', 'customer_frequency',
            'customer_frequency_log1p', 'days_since_last_order', 'is_active_customer',
            'return_rate_30d', 'campaign_lift', 'coefficient_variation_30d'
        ])
        writer.writeheader()
        writer.writerows([
            {
                'client_id': 'CL001', 'postal_code': '28001', 'province': 'Madrid',
                'customer_total_revenue': '10000.50', 'customer_total_orders': '25',
                'customer_avg_ticket': '400.02', 'customer_frequency': '2.5',
                'customer_frequency_log1p': '1.25', 'days_since_last_order': '10',
                'is_active_customer': 'True', 'return_rate_30d': '0.05',
                'campaign_lift': '1.2', 'coefficient_variation_30d': '0.15'
            },
            {
                'client_id': 'CL002', 'postal_code': '08001', 'province': 'Barcelona',
                'customer_total_revenue': '5000.00', 'customer_total_orders': '10',
                'customer_avg_ticket': '500.00', 'customer_frequency': '1.5',
                'customer_frequency_log1p': '0.92', 'days_since_last_order': '20',
                'is_active_customer': 'True', 'return_rate_30d': '0.10',
                'campaign_lift': '1.1', 'coefficient_variation_30d': '0.20'
            },
        ])
    return csv_path


@pytest.fixture
def sample_products_csv(temp_dir):
    """Create a sample products CSV file."""
    csv_path = temp_dir / "products.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'product_id', 'analytic_block', 'category', 'family',
            'product_total_revenue', 'product_total_units', 'product_frequency',
            'rolling_sales_30d', 'product_growth_30d', 'product_return_rate',
            'product_customer_count'
        ])
        writer.writeheader()
        writer.writerows([
            {
                'product_id': 'P001', 'analytic_block': 'Technical', 'category': 'Cat1',
                'family': 'Fam1', 'product_total_revenue': '50000.00',
                'product_total_units': '500', 'product_frequency': '5.0',
                'rolling_sales_30d': '3000.00', 'product_growth_30d': '0.10',
                'product_return_rate': '0.02', 'product_customer_count': '100'
            },
            {
                'product_id': 'P002', 'analytic_block': 'Non-Technical', 'category': 'Cat2',
                'family': 'Fam2', 'product_total_revenue': '30000.00',
                'product_total_units': '300', 'product_frequency': '3.0',
                'rolling_sales_30d': '2000.00', 'product_growth_30d': '0.05',
                'product_return_rate': '0.03', 'product_customer_count': '80'
            },
        ])
    return csv_path


@pytest.fixture
def sample_potential_csv(temp_dir):
    """Create a sample potential CSV file."""
    csv_path = temp_dir / "potential.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'client_id', 'family', 'product_category', 'potential_h',
            'current_sales', 'potential_gap', 'capture_ratio'
        ])
        writer.writeheader()
        writer.writerows([
            {
                'client_id': 'CL001', 'family': 'Fam1', 'product_category': 'Cat1',
                'potential_h': '15000.00', 'current_sales': '10000.00',
                'potential_gap': '5000.00', 'capture_ratio': '0.67'
            },
            {
                'client_id': 'CL002', 'family': 'Fam2', 'product_category': 'Cat2',
                'potential_h': '8000.00', 'current_sales': '5000.00',
                'potential_gap': '3000.00', 'capture_ratio': '0.62'
            },
        ])
    return csv_path


@pytest.fixture
def sample_sales_enriched_csv(temp_dir):
    """Create a sample sales enriched CSV file."""
    csv_path = temp_dir / "sales_enriched.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'invoice_id', 'date', 'client_id', 'product_id', 'units', 'sales_value',
            'is_return', 'is_campaign_period', 'campaign_id', 'month', 'quarter',
            'weekday', 'is_month_end', 'is_quarter_end', 'rolling_sales_7d',
            'sales_delta_vs_7d'
        ])
        writer.writeheader()
        writer.writerows([
            {
                'invoice_id': 'INV001', 'date': '2026-01-15', 'client_id': 'CL001',
                'product_id': 'P001', 'units': '5', 'sales_value': '500.00',
                'is_return': 'false', 'is_campaign_period': 'true', 'campaign_id': 'C001',
                'month': '1', 'quarter': '1', 'weekday': '3', 'is_month_end': 'false',
                'is_quarter_end': 'false', 'rolling_sales_7d': '3500.00',
                'sales_delta_vs_7d': '100.00'
            },
            {
                'invoice_id': 'INV002', 'date': '2026-01-20', 'client_id': 'CL002',
                'product_id': 'P002', 'units': '3', 'sales_value': '300.00',
                'is_return': 'false', 'is_campaign_period': 'false', 'campaign_id': '',
                'month': '1', 'quarter': '1', 'weekday': '1', 'is_month_end': 'false',
                'is_quarter_end': 'false', 'rolling_sales_7d': '2000.00',
                'sales_delta_vs_7d': '50.00'
            },
        ])
    return csv_path


@pytest.fixture
def sample_client_product_features_csv(temp_dir):
    """Create a sample client product features CSV file."""
    csv_path = temp_dir / "client_product_features.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'client_id', 'product_id', 'rolling_sales_30d', 'sales_growth_30d',
            'days_since_last_product_order', 'client_product_frequency',
            'client_product_avg_ticket', 'client_product_return_rate',
            'campaign_lift_product', 'client_product_total_revenue',
            'client_product_total_orders'
        ])
        writer.writeheader()
        writer.writerows([
            {
                'client_id': 'CL001', 'product_id': 'P001', 'rolling_sales_30d': '3000.00',
                'sales_growth_30d': '0.15', 'days_since_last_product_order': '5',
                'client_product_frequency': '2.0', 'client_product_avg_ticket': '100.00',
                'client_product_return_rate': '0.01', 'campaign_lift_product': '1.3',
                'client_product_total_revenue': '5000.00', 'client_product_total_orders': '10'
            },
            {
                'client_id': 'CL002', 'product_id': 'P002', 'rolling_sales_30d': '1500.00',
                'sales_growth_30d': '0.08', 'days_since_last_product_order': '15',
                'client_product_frequency': '1.0', 'client_product_avg_ticket': '150.00',
                'client_product_return_rate': '0.02', 'campaign_lift_product': '1.1',
                'client_product_total_revenue': '3000.00', 'client_product_total_orders': '5'
            },
        ])
    return csv_path


# ============================================================================
# MODEL TESTS
# ============================================================================

class TestModels:
    """Test domain models."""
    
    def test_campaign_creation(self):
        """Test Campaign model creation."""
        campaign = Campaign(
            campaign_id='C001',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            campaign_duration_days=30
        )
        assert campaign.campaign_id == 'C001'
        assert campaign.campaign_duration_days == 30
    
    def test_client_creation(self):
        """Test Client model creation."""
        client = Client(
            client_id='CL001',
            postal_code='28001',
            province='Madrid',
            customer_total_revenue=10000.50,
            customer_total_orders=25,
            customer_avg_ticket=400.02,
            customer_frequency=2.5,
            customer_frequency_log1p=1.25,
            days_since_last_order=10,
            is_active_customer=True,
            return_rate_30d=0.05,
            campaign_lift=1.2,
            coefficient_variation_30d=0.15
        )
        assert client.client_id == 'CL001'
        assert client.province == 'Madrid'
        assert client.customer_total_revenue == 10000.50
    
    def test_product_creation(self):
        """Test Product model creation."""
        product = Product(
            product_id='P001',
            analytic_block='Technical',
            category='Cat1',
            family='Fam1',
            product_total_revenue=50000.00,
            product_total_units=500,
            product_frequency=5.0,
            rolling_sales_30d=3000.00,
            product_growth_30d=0.10,
            product_return_rate=0.02,
            product_customer_count=100
        )
        assert product.product_id == 'P001'
        assert product.analytic_block == 'Technical'
        assert product.product_total_units == 500
    
    def test_client_product_context_creation(self):
        """Test ClientProductContext model creation."""
        client = Client(
            client_id='CL001', postal_code='28001', province='Madrid',
            customer_total_revenue=10000.50, customer_total_orders=25,
            customer_avg_ticket=400.02, customer_frequency=2.5,
            customer_frequency_log1p=1.25, days_since_last_order=10,
            is_active_customer=True, return_rate_30d=0.05,
            campaign_lift=1.2, coefficient_variation_30d=0.15
        )
        product = Product(
            product_id='P001', analytic_block='Technical', category='Cat1',
            family='Fam1', product_total_revenue=50000.00, product_total_units=500,
            product_frequency=5.0, rolling_sales_30d=3000.00, product_growth_30d=0.10,
            product_return_rate=0.02, product_customer_count=100
        )
        features = ClientProductFeatures(
            client_id='CL001', product_id='P001', rolling_sales_30d=3000.00,
            sales_growth_30d=0.15, days_since_last_product_order=5,
            client_product_frequency=2.0, client_product_avg_ticket=100.00,
            client_product_return_rate=0.01, campaign_lift_product=1.3,
            client_product_total_revenue=5000.00, client_product_total_orders=10
        )
        
        context = ClientProductContext(
            client_id='CL001',
            product_id='P001',
            client=client,
            product=product,
            features=features
        )
        
        assert context.client_id == 'CL001'
        assert context.product_id == 'P001'
        assert context.client.province == 'Madrid'
        assert context.product.analytic_block == 'Technical'
        assert context.features.rolling_sales_30d == 3000.00
        assert context.sales_history == []


# ============================================================================
# LOADER TESTS
# ============================================================================

class TestLoaders:
    """Test CSV loaders."""
    
    def test_load_campaigns(self, sample_campaigns_csv):
        """Test loading campaigns from CSV."""
        campaigns = load_campaigns(sample_campaigns_csv)
        
        assert len(campaigns) == 2
        assert campaigns[0].campaign_id == 'C001'
        assert campaigns[0].start_date == date(2026, 1, 1)
        assert campaigns[0].end_date == date(2026, 1, 31)
        assert campaigns[0].campaign_duration_days == 30
    
    def test_load_clients(self, sample_clients_csv):
        """Test loading clients from CSV."""
        clients = load_clients(sample_clients_csv)
        
        assert len(clients) == 2
        assert clients[0].client_id == 'CL001'
        assert clients[0].province == 'Madrid'
        assert clients[0].customer_total_revenue == 10000.50
        assert clients[1].client_id == 'CL002'
    
    def test_load_products(self, sample_products_csv):
        """Test loading products from CSV."""
        products = load_products(sample_products_csv)
        
        assert len(products) == 2
        assert products[0].product_id == 'P001'
        assert products[0].analytic_block == 'Technical'
        assert products[1].analytic_block == 'Non-Technical'
    
    def test_load_potential(self, sample_potential_csv):
        """Test loading potential from CSV."""
        potentials = load_potential(sample_potential_csv)
        
        assert len(potentials) == 2
        assert potentials[0].client_id == 'CL001'
        assert potentials[0].potential_h == 15000.00
        assert potentials[0].capture_ratio == 0.67
    
    def test_load_sales_enriched(self, sample_sales_enriched_csv):
        """Test loading sales enriched from CSV."""
        sales = load_sales_enriched(sample_sales_enriched_csv)
        
        assert len(sales) == 2
        assert sales[0].invoice_id == 'INV001'
        assert sales[0].date == date(2026, 1, 15)
        assert sales[0].is_return is False
        assert sales[0].is_campaign_period is True
        assert sales[0].campaign_id == 'C001'
        assert sales[1].campaign_id is None
    
    def test_load_client_product_features(self, sample_client_product_features_csv):
        """Test loading client product features from CSV."""
        features = load_client_product_features(sample_client_product_features_csv)
        
        assert len(features) == 2
        assert features[0].client_id == 'CL001'
        assert features[0].product_id == 'P001'
        assert features[0].rolling_sales_30d == 3000.00


# ============================================================================
# DATA AGGREGATOR TESTS
# ============================================================================

class TestDataAggregator:
    """Test DataAggregator service."""
    
    @pytest.fixture
    def complete_dataset(self, temp_dir, sample_campaigns_csv, sample_clients_csv,
                        sample_products_csv, sample_potential_csv, 
                        sample_sales_enriched_csv, sample_client_product_features_csv):
        """Setup complete dataset for testing."""
        return temp_dir
    
    def test_aggregator_initialization(self, complete_dataset):
        """Test DataAggregator initialization."""
        aggregator = DataAggregator(complete_dataset)
        
        assert aggregator.data_dir == complete_dataset
        assert len(aggregator.campaigns) == 0
        assert len(aggregator.clients) == 0
    
    def test_load_all_data(self, complete_dataset):
        """Test loading all data."""
        aggregator = DataAggregator(complete_dataset)
        aggregator.load_all_data()
        
        assert len(aggregator.campaigns) == 2
        assert len(aggregator.clients) == 2
        assert len(aggregator.products) == 2
        assert len(aggregator.potentials) == 2
        assert len(aggregator.sales_enriched) == 2
        assert len(aggregator.client_product_features) == 2
    
    def test_get_data_summary(self, complete_dataset):
        """Test getting data summary."""
        aggregator = DataAggregator(complete_dataset)
        aggregator.load_all_data()
        
        summary = aggregator.get_data_summary()
        
        assert summary['campaigns'] == 2
        assert summary['clients'] == 2
        assert summary['products'] == 2
        assert summary['potentials'] == 2
        assert summary['sales_enriched'] == 2
        assert summary['client_product_features'] == 2
    
    def test_get_technical_products(self, complete_dataset):
        """Test filtering technical products."""
        aggregator = DataAggregator(complete_dataset)
        aggregator.load_all_data()
        
        technical_products = aggregator.get_technical_products()
        
        assert len(technical_products) == 1
        assert technical_products[0].product_id == 'P001'
        assert technical_products[0].analytic_block == 'Technical'
    
    def test_filter_by_technical_products(self, complete_dataset):
        """Test filtering all datasets by technical products."""
        aggregator = DataAggregator(complete_dataset)
        aggregator.load_all_data()
        
        filtered = aggregator.filter_by_technical_products()
        
        assert len(filtered['products']) == 1
        assert filtered['products'][0].analytic_block == 'Technical'
        # Sales filtered by technical products
        assert len(filtered['sales_enriched']) == 1
        assert filtered['sales_enriched'][0].product_id == 'P001'
    
    def test_build_client_product_contexts(self, complete_dataset):
        """Test building client-product contexts."""
        aggregator = DataAggregator(complete_dataset)
        aggregator.load_all_data()
        
        contexts = aggregator.build_client_product_contexts(technical_only=True)
        
        assert len(contexts) == 1
        assert contexts[0].client_id == 'CL001'
        assert contexts[0].product_id == 'P001'
        assert contexts[0].client.province == 'Madrid'
        assert contexts[0].product.analytic_block == 'Technical'
        assert contexts[0].features.rolling_sales_30d == 3000.00
        assert contexts[0].potential is not None
        assert contexts[0].potential.family == 'Fam1'
    
    def test_build_all_contexts(self, complete_dataset):
        """Test building contexts for all products."""
        aggregator = DataAggregator(complete_dataset)
        aggregator.load_all_data()
        
        contexts = aggregator.build_client_product_contexts(technical_only=False)
        
        assert len(contexts) == 2
        assert contexts[0].product_id == 'P001'
        assert contexts[1].product_id == 'P002'
    
    def test_context_sales_history(self, complete_dataset):
        """Test that contexts include sales history."""
        aggregator = DataAggregator(complete_dataset)
        aggregator.load_all_data()
        
        contexts = aggregator.build_client_product_contexts(technical_only=True)
        
        assert len(contexts) == 1
        context = contexts[0]
        assert len(context.sales_history) == 1
        assert context.sales_history[0].invoice_id == 'INV001'


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
