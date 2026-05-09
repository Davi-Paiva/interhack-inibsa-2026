# Drift Detection Module

## Overview

The `drift_detection` module provides behavioral commercial drift detection capabilities for analyzing customer-product purchasing relationships. It identifies early signs of abandonment or commercial deterioration in technical dental product sales.

## Purpose

This is **not** generic ML anomaly detection. Instead, it focuses on:

- **Abnormal inactivity** - When customers stop purchasing products
- **Deterioration in purchase behavior** - Declining sales volumes
- **Divergence from peers** - Underperformance compared to similar customers
- **Volume decline** - Negative growth trends

## Architecture

The module follows clean architecture principles with strong separation of concerns:

```text
drift_detection/
├── detector.py           # Central orchestrator
├── interval_drift.py     # Inactivity detection
├── volume_drift.py       # Sales decline detection
├── peer_drift.py         # Peer divergence detection
└── example_usage.py      # Usage examples
```

## Core Components

### 1. DriftDetector (Orchestrator)

Central coordination layer that invokes all specialized detectors.

```python
from backend.technical_product_engine.drift_detection import DriftDetector

detector = DriftDetector()
signals = detector.detect(context, peer_metrics)
```

**Methods:**
- `detect(context, peer_metrics)` - Detect drift for a single relationship
- `detect_batch(contexts, peer_metrics_map)` - Batch processing for multiple relationships

### 2. Interval Drift Detection

Detects inactivity deterioration by comparing time since last purchase against expected cycle.

**Core Logic:**
```python
inactivity_ratio = days_since_last_product_order / expected_purchase_interval
```

**Thresholds:**
- `ratio > 1.5` → Medium drift (severity 0.3-0.7)
- `ratio > 2.0` → High drift (severity 0.7-1.0)

**Configuration:**
- `INTERVAL_DRIFT_MEDIUM_THRESHOLD = 1.5`
- `INTERVAL_DRIFT_HIGH_THRESHOLD = 2.0`
- `MIN_FREQUENCY_THRESHOLD = 0.01`
- `DEFAULT_EXPECTED_INTERVAL_DAYS = 365`

### 3. Volume Drift Detection

Detects deterioration in purchase volume through negative growth trends.

**Core Logic:**
```python
if sales_growth_30d < threshold:
    emit_signal()
```

**Thresholds:**
- `growth < -0.2` → Warning (severity 0.3-0.7)
- `growth < -0.4` → Strong deterioration (severity 0.7-1.0)

**Configuration:**
- `VOLUME_DRIFT_WARNING_THRESHOLD = -0.2`
- `VOLUME_DRIFT_STRONG_THRESHOLD = -0.4`
- `NEGLIGIBLE_GROWTH_THRESHOLD = 0.05`

### 4. Peer Drift Detection

Detects divergence from peer behavior patterns.

**Core Logic:**
```python
peer_deviation = abs(customer_growth - peer_avg_growth)
```

**Thresholds:**
- `deviation > 0.3` → Moderate drift (severity 0.3-0.7)
- `deviation > 0.5` → Strong drift (severity 0.7-1.0)

**Requirements:**
- Minimum 5 peers for valid comparison
- Only flags drift when customer declines below peers

**Configuration:**
- `PEER_DRIFT_MODERATE_THRESHOLD = 0.3`
- `PEER_DRIFT_STRONG_THRESHOLD = 0.5`
- `MIN_PEER_SAMPLE_SIZE = 5`

## Data Models

### DriftSignal

Structured analytical signal output:

```python
@dataclass
class DriftSignal:
    signal_type: SignalType      # Type of drift detected
    severity: float               # Normalized score (0.0-1.0)
    metric_value: float           # Actual measured value
    threshold: float              # Threshold that was exceeded
```

### SignalType

Enumeration of drift categories:

```python
class SignalType(Enum):
    INTERVAL_DRIFT = "interval_drift"
    VOLUME_DRIFT = "volume_drift"
    PEER_DRIFT = "peer_drift"
```

### PeerMetrics

Peer comparison data:

```python
@dataclass
class PeerMetrics:
    peer_avg_growth: float       # Average growth among peers
    peer_std_growth: float        # Standard deviation
    peer_count: int               # Number of peers
```

## Usage

### Basic Detection

```python
from backend.technical_product_engine.drift_detection import DriftDetector
from backend.technical_product_engine.domain import ClientProductContext

# Create context (typically from upstream pipeline)
context = ClientProductContext(
    client_id="CLI001",
    product_id="PROD123",
    client=client_obj,
    product=product_obj,
    features=features_obj,
)

# Initialize detector
detector = DriftDetector()

# Detect drift
signals = detector.detect(context)

# Process results
for signal in signals:
    print(f"{signal.signal_type.value}: severity={signal.severity:.2f}")
```

### With Peer Comparison

```python
from backend.technical_product_engine.drift_detection import (
    DriftDetector,
    PeerMetrics,
)

# Create peer metrics
peer_metrics = PeerMetrics(
    peer_avg_growth=0.05,
    peer_std_growth=0.12,
    peer_count=20,
)

# Detect with peer comparison
signals = detector.detect(context, peer_metrics)
```

### Batch Processing

```python
# Process multiple relationships
contexts = [context1, context2, context3]
peer_metrics_map = {
    ("CLI001", "PROD123"): peer_metrics1,
    ("CLI002", "PROD456"): peer_metrics2,
}

results = detector.detect_batch(contexts, peer_metrics_map)

# Results is dict: (client_id, product_id) -> List[DriftSignal]
for (client_id, product_id), signals in results.items():
    print(f"{client_id} - {product_id}: {len(signals)} signals")
```

## Design Principles

### 1. Pure Functions
Most detection logic uses pure functions for predictability and testability:

```python
def _compute_inactivity_ratio(days: int, expected: float) -> float:
    # Pure function: same inputs always produce same output
    return days / expected if expected > 0 else 0.0
```

### 2. Defensive Programming

All detectors handle edge cases gracefully:

- Division by zero
- Missing values
- Insufficient data
- Invalid ranges

### 3. Configurable Thresholds

All thresholds are centralized as module-level constants for easy tuning:

```python
# interval_drift.py
INTERVAL_DRIFT_MEDIUM_THRESHOLD = 1.5
INTERVAL_DRIFT_HIGH_THRESHOLD = 2.0
```

### 4. Type Safety

Full type hints throughout:

```python
def detect_interval_drift(
    context: ClientProductContext
) -> List[DriftSignal]:
    ...
```

### 5. Separation of Concerns

- **Detectors** contain analytical logic
- **Orchestrator** handles coordination
- **Domain models** define data structures
- No cross-cutting concerns

## Performance Considerations

- **Stateless detectors** - Can be parallelized
- **Precomputed features** - No on-the-fly calculations
- **Batch processing** - Efficient for large datasets
- **No DataFrame operations** - Works with typed objects

## Testing Strategy

Each detector is independently testable:

```python
def test_interval_drift():
    context = create_test_context(
        days_since_last_order=100,
        frequency=0.02  # Expected interval: 50 days
    )
    signals = detect_interval_drift(context)
    assert len(signals) == 1
    assert signals[0].signal_type == SignalType.INTERVAL_DRIFT
    assert signals[0].metric_value == 2.0  # 100/50
```

## Integration

The drift detection module integrates with:

1. **Upstream:** Receives `ClientProductContext` from data aggregation layer
2. **Downstream:** Provides signals to risk scoring layer
3. **Peer Analysis:** Optional integration with peer comparison service

## Extensibility

To add new drift types:

1. Add signal type to `SignalType` enum
2. Create new detector module (e.g., `seasonality_drift.py`)
3. Add detector call to `DriftDetector.detect()`
4. Export from `__init__.py`

## Error Handling

The module follows fail-safe principles:

- Returns empty list on invalid input
- Handles missing peer metrics gracefully
- Validates signal attributes on construction
- Never crashes the analytical pipeline

## Configuration Reference

### Interval Drift
```python
INTERVAL_DRIFT_MEDIUM_THRESHOLD = 1.5        # 150% of expected cycle
INTERVAL_DRIFT_HIGH_THRESHOLD = 2.0          # 200% of expected cycle
MIN_FREQUENCY_THRESHOLD = 0.01               # Minimum valid frequency
DEFAULT_EXPECTED_INTERVAL_DAYS = 365         # Fallback cycle length
```

### Volume Drift
```python
VOLUME_DRIFT_WARNING_THRESHOLD = -0.2        # -20% growth
VOLUME_DRIFT_STRONG_THRESHOLD = -0.4         # -40% growth
NEGLIGIBLE_GROWTH_THRESHOLD = 0.05           # ±5% noise tolerance
```

### Peer Drift
```python
PEER_DRIFT_MODERATE_THRESHOLD = 0.3          # 30% deviation
PEER_DRIFT_STRONG_THRESHOLD = 0.5            # 50% deviation
MIN_PEER_SAMPLE_SIZE = 5                     # Minimum peers required
```

## Example Output

```python
DriftSignal(
    signal_type=SignalType.INTERVAL_DRIFT,
    severity=0.82,
    metric_value=2.4,
    threshold=1.5
)

DriftSignal(
    signal_type=SignalType.VOLUME_DRIFT,
    severity=0.65,
    metric_value=0.35,
    threshold=0.2
)

DriftSignal(
    signal_type=SignalType.PEER_DRIFT,
    severity=0.74,
    metric_value=0.43,
    threshold=0.3
)
```

## Dependencies

- Python 3.11+
- `dataclasses` (standard library)
- `typing` (standard library)
- `enum` (standard library)

No external dependencies required.

## See Also

- [Module Guide](../README.md) - Overall system architecture
- [Domain Models](../domain/models.py) - Data structures
- [Example Usage](example_usage.py) - Working examples
- [Tests](../tests/test_engine.py) - Test suite
