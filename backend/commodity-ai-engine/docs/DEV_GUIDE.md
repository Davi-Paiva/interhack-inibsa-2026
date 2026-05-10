# Commodity AI Engine - Development Guide

## Quick Start

**You are here**: Implementing the Commodity AI Engine component

**What it does**: Identifies customers who are likely buying from competitors by detecting "demand leakage" — the gap between what they should buy and what they actually buy.

---

## Why Commodity AI is Different

| Aspect | Commodity Products | Technical Products |
|--------|-------------------|-------------------|
| **Purchase pattern** | Regular, predictable | Irregular, sporadic |
| **Example** | Antibiotics (buy regularly) | Surgical kits (buy as needed) |
| **Detection logic** | Predict consumption → compare to actual | Detect sudden inactivity |
| **Signal** | Demand leakage = competitor capture | No purchase = churn risk |
| **Model** | Forecasting + clustering | Anomaly detection |

Your job: **Build the forecasting/clustering side**

---

## 📋 What You Need to Implement

### Class 1: `CommodityCustomerCluster` ✏️

**What**: Groups customers into 5 behavioral archetypes using KMeans.

**Features to compute** (from historical sales):
```
- avg_monthly_volume: Average monthly quantity
- order_frequency: Orders per month
- order_variance: How much quantities vary
- inactivity_ratio: Days without purchase / total period
- category_loyalty: % of purchases in primary category
- purchase_interval_stability: How regular are purchases
```

**Output**: Cluster ID (0-4) + profiles

**Implementation tips**:
- Normalize features before clustering
- Compute rolling statistics over last 90-180 days
- Exclude customers with <3 months history

---

### Class 2: `DemandForecaster` ✏️

**What**: Predicts monthly consumption using LightGBM.

**Input features**:
```
Recency features:
  - rolling_7d_volume
  - rolling_30d_volume
  - rolling_7d_frequency
  - rolling_30d_frequency
  - avg_purchase_interval

Trend features:
  - trend_slope (using linear regression)
  - seasonality_index

Context features:
  - customer_cluster (from clustering)
  - product_family
  - clinic_size (if available)
```

**Output**: Expected monthly consumption (continuous value)

**Implementation tips**:
- Create lagged features for time series
- Add seasonal dummies (month)
- Handle missing values (forward fill then drop)
- Test-train split on time (not random)
- Use last 60 days of actual data as target

---

### Class 3: `DemandLeakageDetector` ✏️

**What**: Computes the gap between predicted and observed consumption.

**Formula**:
```
base_gap = (predicted - observed) / predicted

leakage_score = base_gap × customer_volatility × model_confidence

# Clipped to 0-1 range
```

**Why volatility matters**:
- A customer who naturally varies ±30% shouldn't trigger alerts
- A customer with stable ordering (+5% variance) should trigger at small gaps

**Output**: Leakage scores + metrics

**Implementation tips**:
- Filter out leakage < 10 units (noise)
- Consider seasonal factors
- Exclude customers with inconsistent data

---

### Class 4: `CaptureScoringEngine` ✏️

**What**: Ranks opportunities by business impact.

**Scoring formula** (0-100):
```
score = (leakage_score × 0.40)
      + (customer_value_norm × 0.30)
      + (urgency_norm × 0.20)
      + (model_confidence × 0.10)
```

**Where**:
- **leakage_score**: Magnitude of demand gap (0-1)
- **customer_value**: Annual spend normalized to 0-1
- **urgency**: How fast is the gap growing? (0-1)
- **confidence**: Model confidence in prediction (0.85 default)

**Output**: Ranked list of opportunities + actions

**Implementation tips**:
- High-value customers get priority
- Increasing gaps are more urgent
- Top 20% of scores get "urgent" label

---

## 📊 Data Flow

```
Raw CSV Files (sales.csv, clients.csv, products.csv)
           ↓
Feature Engineering (rolling stats, seasonality)
           ↓
┌─────────────────────────────────────────┐
│ Clustering                              │
│ Input: behavior features                │
│ Output: customer cluster assignments    │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│ Forecasting                             │
│ Input: features + cluster + historicals │
│ Output: predicted consumption           │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│ Leakage Detection                       │
│ Input: predicted vs observed            │
│ Output: leakage scores                  │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│ Scoring & Ranking                       │
│ Input: leakage + business metrics       │
│ Output: prioritized opportunities       │
└─────────────────────────────────────────┘
           ↓
JSON output: commodity_signals.json
```

---

## 🚀 Implementation Steps

1. **Load data** — Read CSV files
2. **Feature engineering** — Compute rolling stats, seasonality
3. **Implement clustering** — KMeans on behavior features
4. **Implement forecasting** — LightGBM on time-series features
5. **Implement leakage** — Gap analysis + normalization
6. **Implement scoring** — Weighted multi-factor ranking
7. **Export signals** — JSON output

---

## 🔍 Testing Your Implementation

### Validation Checklist

- [ ] Clusters have **meaningful differences** (check cluster profiles)
- [ ] Forecasts are **non-negative** and **reasonable** (compare to mean)
- [ ] Leakage scores are **in 0-1 range**
- [ ] Top opportunities have **high business impact**
- [ ] No **NaN values** in output
- [ ] Output JSON is **valid and parseable**

### Quick Test Script

```python
from src import CommoditySignalGenerator
import pandas as pd

# Load data
sales = pd.read_csv('../raw_data/sales.csv')
clients = pd.read_csv('../raw_data/clients.csv')
products = pd.read_csv('../raw_data/products.csv')

# Run engine
generator = CommoditySignalGenerator(sales, clients, products)
signals = generator.generate_signals()

# Export
generator.export_signals(signals, 'output/commodity_signals.json')

print(f"✓ Generated {len(signals)} signals")
```

---

## ❓ Common Questions

**Q: Should I use the same data for train/test?**  
A: No. Use time-based split (e.g., first 80% for training, last 20% for testing).

**Q: What if a customer has no history?**  
A: Exclude them or use peer group averages.

**Q: How do I handle seasonal products?**  
A: Add seasonal dummies or use fourier features.

**Q: Is 0.85 confidence always correct?**  
A: No. Compute it from model RMSE / mean predictions.

---

## ✅ When You're Done

Your output should be:
- [ ] `commodity_engine.py` fully implemented
- [ ] `output/commodity_signals.json` generated
- [ ] Signals ranked by business impact
- [ ] Explanations are human-readable
- [ ] Code is production-ready

Then ping the team to integrate into the frontend!
