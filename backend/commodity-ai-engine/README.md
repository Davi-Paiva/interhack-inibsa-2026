# Commodity AI Engine

**Smart Demand Signals** — Detect demand leakage and identify competitor capture opportunities.

Part 3 of the INIBSA hackathon platform.

---

## What It Does

Identifies customers who are likely buying from competitors by analyzing the gap between:
- **Expected consumption** (what they should buy based on history)
- **Observed consumption** (what they actually bought)

This gap = **demand leakage** = opportunity for sales intervention.

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Prepare Data

Place CSV files in `../raw_data/`:
- `sales.csv` — Transaction history
- `clients.csv` — Customer metadata
- `products.csv` — Product catalog

### 3. Run Engine

```python
from src import CommoditySignalGenerator
import pandas as pd

sales = pd.read_csv('../raw_data/sales.csv')
clients = pd.read_csv('../raw_data/clients.csv')
products = pd.read_csv('../raw_data/products.csv')

generator = CommoditySignalGenerator(sales, clients, products)
signals = generator.generate_signals()
generator.export_signals(signals, 'output/commodity_signals.json')
```

---

## Architecture

### 4 Components

| Component | Purpose | Input | Output |
|-----------|---------|-------|--------|
| **CommodityCustomerCluster** | Segment customers | Sales history | Cluster assignments |
| **DemandForecaster** | Predict consumption | Features + history | Expected quantity |
| **DemandLeakageDetector** | Find gaps | Predicted vs actual | Leakage scores |
| **CaptureScoringEngine** | Rank opportunities | Leakage + business metrics | Prioritized signals |

---

## Output

**File**: `output/commodity_signals.json`

```json
{
  "customer_id": "CLI_0042",
  "product_family": "Antibiotics",
  "leakage_score": 0.68,
  "predicted_monthly_consumption": 450,
  "observed_monthly_consumption": 280,
  "gap_units": 170,
  "estimated_lost_revenue": 1360,
  "customer_cluster": "promiscuous_buyers",
  "urgency": 0.82,
  "confidence": 0.87,
  "recommended_action": "URGENT: High-value competitor capture - sales call within 24h",
  "timeline": ["Jan: stable", "Feb: declining", "Mar: gap detected"]
}
```

---

## Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — Full system design
- [DEV_GUIDE.md](docs/DEV_GUIDE.md) — Step-by-step implementation
- [COPILOT_PROMPT.md](docs/COPILOT_PROMPT.md) — For Copilot Chat

---

## Implementation Status

- [x] Structure created
- [ ] CommodityCustomerCluster — implement
- [ ] DemandForecaster — implement
- [ ] DemandLeakageDetector — implement
- [ ] CaptureScoringEngine — implement
- [ ] Integration with main pipeline

---

## Integration

This module integrates with:
1. `run_churn_analysis.py` — Call it from here
2. Frontend API — Expose signals via FastAPI
3. Technical churn detector — Combine signals

---

## Development

Use Copilot to implement the `TODO` methods:

1. Copy `docs/COPILOT_PROMPT.md`
2. Paste in Copilot Chat
3. Ask: "Build the commodity engine"

Or click on any `TODO` and use inline Copilot generation.

---

## Author

Developed for InterhackBCN 2026 — INIBSA Smart Demand Signals Challenge
