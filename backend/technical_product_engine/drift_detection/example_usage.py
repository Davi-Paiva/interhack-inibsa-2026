"""
Example usage of the drift detection module.

This demonstrates how to use the drift detection components
to analyze customer-product relationships.
"""
from backend.technical_product_engine.domain import (
    Client,
    Product,
    ClientProductFeatures,
    ClientProductContext,
    SignalType,
)
from backend.technical_product_engine.drift_detection import (
    DriftDetector,
    PeerMetrics,
)


def example_drift_detection():
    """Example demonstrating drift detection usage."""
    
    # Create example client
    client = Client(
        client_id="CLI001",
        postal_code="28001",
        province="Madrid",
        customer_total_revenue=50000.0,
        customer_total_orders=100,
        customer_avg_ticket=500.0,
        customer_frequency=0.1,  # ~10 orders per 100 days
        days_since_last_order=45,
        return_rate_30d=0.02,
        campaign_lift=0.15,
        coefficient_variation_30d=0.3,
    )
    
    # Create example product
    product = Product(
        product_id="PROD123",
        analytic_block="Technical",
        category="Implants",
        family="Dental Implants",
        product_total_revenue=100000.0,
        product_total_units=500,
        product_frequency=0.05,
        rolling_sales_30d=8000.0,
        product_growth_30d=0.05,
        product_return_rate=0.01,
        product_customer_count=50,
    )
    
    # Create example client-product features
    features = ClientProductFeatures(
        client_id="CLI001",
        product_id="PROD123",
        rolling_sales_30d=2500.0,
        sales_growth_30d=-0.35,  # -35% decline
        days_since_last_product_order=180,  # 6 months inactive
        client_product_frequency=0.02,  # ~1 order per 50 days
        client_product_avg_ticket=450.0,
        client_product_return_rate=0.01,
        campaign_lift_product=0.10,
        client_product_total_revenue=15000.0,
        client_product_total_orders=30,
    )
    
    # Create context
    context = ClientProductContext(
        client_id="CLI001",
        product_id="PROD123",
        client=client,
        product=product,
        features=features,
        potential=None,
        sales_history=[],
    )
    
    # Create peer metrics for comparison
    peer_metrics = PeerMetrics(
        peer_avg_growth=0.08,  # Peers growing at 8%
        peer_std_growth=0.12,
        peer_count=25,
    )
    
    # Initialize detector
    detector = DriftDetector()
    
    # Detect drift
    signals = detector.detect(context, peer_metrics)
    
    # Display results
    print(f"\n=== Drift Detection Results ===")
    print(f"Client: {context.client_id}")
    print(f"Product: {context.product_id}")
    print(f"\nDetected {len(signals)} drift signals:\n")
    
    for signal in signals:
        print(f"Signal Type: {signal.signal_type.value}")
        print(f"  Severity: {signal.severity:.2f}")
        print(f"  Metric Value: {signal.metric_value:.2f}")
        print(f"  Threshold: {signal.threshold:.2f}")
        print()
    
    # Categorize by type
    by_type = {}
    for signal in signals:
        signal_type = signal.signal_type
        if signal_type not in by_type:
            by_type[signal_type] = []
        by_type[signal_type].append(signal)
    
    print("\n=== Summary by Signal Type ===")
    for signal_type in SignalType:
        if signal_type in by_type:
            signals_of_type = by_type[signal_type]
            max_severity = max(s.severity for s in signals_of_type)
            print(f"{signal_type.value}: {len(signals_of_type)} signal(s), "
                  f"max severity: {max_severity:.2f}")
        else:
            print(f"{signal_type.value}: No signals")


if __name__ == "__main__":
    example_drift_detection()
