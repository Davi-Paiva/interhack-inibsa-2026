# Commodity AI Engine - Full Architecture

## Overview

The Commodity AI Engine identifies **demand leakage opportunities** — gaps between what customers should buy and what they actually buy, indicating potential competitor capture.

---

## Key Difference: Commodity vs Technical Products

| Aspect | Commodity | Technical |
|--------|-----------|-----------|
| **Purchase Pattern** | Regular, predictable | Irregular, sporadic |
| **Logic** | Forecast consumption → detect gaps | Detect inactivity |
| **Signal** | Demand leakage | Churn risk |
| **Model** | Forecasting + clustering | Anomaly detection |

---

## 4-Layer Architecture

### Layer 1: Customer Clustering (KMeans)

**Purpose**: Segment customers by behavioral archetype.

**Features**:
- `avg_monthly_volume` — Average monthly quantity
- `order_frequency` — Orders per month
- `order_variance` — Variability in order sizes
- `inactivity_ratio` — Days without purchase / total period
- `category_loyalty` — % of purchases in primary category
- `purchase_interval_stability` — Regularity of ordering

**Output Clusters**:
- **Cluster 0**: Loyal high-volume customers
- **Cluster 1**: Promiscuous buyers (split demand with competitors) ⭐ TARGET
- **Cluster 2**: Low engagement
- **Cluster 3**: Growing accounts
- **Cluster 4**: Unstable/erratic behavior

---

### Layer 2: Demand Forecasting (LightGBM)

**Purpose**: Predict what customers SHOULD buy.

**Features**:
- Rolling statistics (7d, 30d volume & frequency)
- Seasonality index
- Trend slope
- Customer cluster
- Product family
- Clinic size (metadata)

**Output**: Expected monthly consumption

---

### Layer 3: Leakage Detection

**Purpose**: Quantify the gap between expected and observed consumption.

**Formula**:
```
base_gap = (predicted - observed) / predicted
leakage_score = base_gap × volatility_factor × confidence
```

**Output**: Leakage score (0-1)

---

### Layer 4: Capture Scoring

**Purpose**: Rank opportunities by business impact.

**Formula**:
```
score = (leakage_score × 0.40)
      + (customer_value × 0.30)
      + (urgency_score × 0.20)
      + (model_confidence × 0.10)
```

**Output**: Ranked opportunities (0-100)

---

## Data Flow

```
Sales CSV → Feature Engineering → Clustering
                                     ↓
                            Forecasting
                                     ↓
                            Leakage Detection
                                     ↓
                            Scoring & Ranking
                                     ↓
                            JSON Signals
```

---

## Expected Output

**File**: `output/commodity_signals.json`

```json
{
  "customer_id": "CLI_0042",
  "product_family": "Antibiotics",
  "signal_type": "demand_leakage",
  "leakage_score": 0.68,
  "predicted_monthly_consumption": 450,
  "observed_monthly_consumption": 280,
  "gap_units": 170,
  "estimated_lost_revenue": 1360,
  "customer_cluster": "promiscuous_buyers",
  "urgency": 0.82,
  "confidence": 0.87,
  "recommended_action": "URGENT: High-value competitor capture - sales call within 24h",
  "timeline": [
    "Jan: 420 units (stable)",
    "Feb: 385 units (slight decline)",
    "Mar: 280 units (sharp drop)",
    "Apr: 280 units (sustained gap)"
  ]
}
```

---

## Files Structure

```
commodity-ai-engine/
├── src/
│   ├── commodity_engine.py      (Main implementation)
│   └── __init__.py
├── output/
│   └── commodity_signals.json   (Generated output)
├── docs/
│   ├── ARCHITECTURE.md          (This file)
│   ├── COPILOT_PROMPT.md        (For Copilot Chat)
│   └── DEV_GUIDE.md
├── requirements.txt
└── README.md
```
