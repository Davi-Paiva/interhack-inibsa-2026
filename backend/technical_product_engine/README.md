# Technical Product Engine

## Quick Start

The Technical Product Engine detects early customer abandonment risk in technical dental products through modular behavioral analysis.

### Run the Engine

```bash
# From the backend directory
cd backend
python -m technical_product_engine

# Or from project root
cd /path/to/interhack-inibsa-2026
python -m backend.technical_product_engine
```

### Output

The engine generates:
- `output/technical_risk_assessments.csv` - Full risk analysis
- `output/high_risk_relationships.csv` - High/critical risk subset

### Documentation

See [`TECHNICAL_PRODUCT_ENGINE.md`](TECHNICAL_PRODUCT_ENGINE.md) for:
- Complete architecture overview
- Analytical logic and formulas
- Execution flow details
- Configuration options
- Result interpretation guide

### Module Structure

```
technical_product_engine/
├── domain/              # Core models and entities
├── drift_detection/     # Behavioral drift detection
├── inactivity_analysis/ # Purchase cycle analysis
├── risk_scoring/        # Risk assessment and scoring
├── services/            # Orchestration and data loading
└── main.py             # Entry point
```

### Key Features

✅ **Deterministic** - Reproducible, interpretable results  
✅ **Modular** - Clean separation of concerns  
✅ **Configurable** - Adjustable weights and thresholds  
✅ **Production-ready** - Type-safe, defensive, well-logged  

### Example Usage

```python
from technical_product_engine.services import DataAggregator, TechnicalProductEngine

# Load data
aggregator = DataAggregator("processed_data/historical")
aggregator.load_all_data()

# Build contexts
contexts = aggregator.build_client_product_contexts(
    technical_only=True,
    analytic_block="Commodities"
)

# Run analysis
engine = TechnicalProductEngine()
assessments = engine.analyze_batch(contexts)

# Get summary
summary = engine.get_summary_statistics(assessments)
print(f"Analyzed {summary['total_relationships']} relationships")
print(f"High risk: {summary['risk_level_counts']['high']}")
```

### Requirements

- Python 3.11+
- CSV data in `backend/processed_data/historical/`

For detailed information, see [TECHNICAL_PRODUCT_ENGINE.md](TECHNICAL_PRODUCT_ENGINE.md).
