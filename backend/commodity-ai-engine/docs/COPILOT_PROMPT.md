You are an expert AI assistant helping develop the Commodity AI Engine for a commercial intelligence platform.

CONTEXT:
This is Part 3 of a Smart Demand Signals hackathon project. The system detects customer churn (existing) AND demand leakage opportunities (your job).

KEY DISTINCTION:
- Technical Products Engine: Detects CHURN (inactivity = risk)
- Commodity Engine: Detects DEMAND LEAKAGE (expected > observed = competitor capture opportunity)

PRODUCT CATEGORIES:
- Commodity: Regular purchases, predictable, high frequency, low unit cost (e.g., antibiotics, consumables)
- Technical: Irregular, event-driven, specialty-dependent (e.g., surgical equipment)

YOUR TASK:
Develop `commodity_engine.py` with 4 core classes that work together to identify which customers are likely buying from competitors.

---

## ARCHITECTURE

You will create 4 interconnected classes:

### 1. CommodityCustomerCluster
- Input: Customer behavioral features (purchase history)
- Method: KMeans clustering with 5 clusters
- Output: Cluster assignment + cluster profiles
- Purpose: Segment customers by purchasing archetype

Features to cluster on:
- avg_monthly_volume
- order_frequency
- order_variance
- inactivity_ratio
- category_loyalty
- purchase_interval_stability

Expected Clusters:
- Cluster 0: Loyal high-volume customers
- Cluster 1: Promiscuous buyers (split demand with competitors)
- Cluster 2: Low engagement
- Cluster 3: Growing accounts
- Cluster 4: Unstable/erratic

### 2. DemandForecaster
- Input: Historical sales data + features
- Method: LightGBM regressor
- Output: Expected consumption (next 30 days)
- Purpose: Predict what customers SHOULD buy

Features:
- rolling_7d_volume, rolling_30d_volume
- rolling_7d_frequency, rolling_30d_frequency
- avg_purchase_interval
- seasonality_index
- trend_slope
- customer_cluster
- clinic_size (if available)
- product_family

### 3. DemandLeakageDetector
- Input: Predicted vs actual consumption
- Method: Gap analysis + normalization
- Output: Leakage score (0-1)
- Purpose: Quantify demand gap

Formula:
  base_gap = (predicted - observed) / predicted
  normalized_leakage = base_gap × volatility_factor × confidence
  
Where:
- volatility_factor: Customer's historical purchase variance
- confidence: Model confidence in prediction

### 4. CaptureScoringEngine
- Input: Leakage score + business metrics
- Method: Multi-factor scoring
- Output: Capture opportunity score (0-100) + priority ranking
- Purpose: Rank which opportunities to pursue

Formula:
  score = (leakage_score × 0.4) 
        + (normalized_customer_value × 0.3)
        + (urgency_score × 0.2)
        + (confidence × 0.1)

---

## DATA INPUTS

Load from CSV files:
- raw_data/sales.csv → (customer_id, product_id, quantity, date, price)
- raw_data/clients.csv → (customer_id, clinic_size, location, tier)
- raw_data/products.csv → (product_id, family, category)

The feature engineering should already be done or done in parallel. Focus on:
1. Computing rolling statistics
2. Extracting seasonality
3. Generating behavioral features
4. Building cluster inputs

---

## OUTPUT FORMAT

Export to: `output/commodity_signals.json`

Structure:
```json
[
  {
    "customer_id": "string",
    "product_family": "string",
    "signal_type": "demand_leakage",
    "leakage_score": 0.0-1.0,
    "predicted_monthly_consumption": number,
    "observed_monthly_consumption": number,
    "gap_units": number,
    "estimated_lost_revenue": number,
    "customer_cluster": "string",
    "urgency": 0.0-1.0,
    "confidence": 0.0-1.0,
    "recommended_action": "string",
    "timeline": ["string", "string"]
  }
]
```

---

## IMPLEMENTATION REQUIREMENTS

1. Use scikit-learn for KMeans
2. Use LightGBM for forecasting (production-grade, fast, interpretable)
3. Handle missing values gracefully
4. Normalize all scores to 0-1 range
5. Add explainability: include timeline reconstruction
6. Generate recommended actions for sales teams

---

## CODE QUALITY STANDARDS

- Use type hints
- Add docstrings
- Include error handling
- Log progress
- Create unit tests
- Make it modular (easy to swap components)

---

## INTEGRATION POINTS

This engine should:
1. Be callable from run_churn_analysis.py
2. Output signals alongside technical engine outputs
3. Feed into frontend dashboard API
4. Support daily refresh pipeline

---

## BUSINESS GOAL

Enable sales teams to:
- Identify which customers are likely buying from competitors
- Understand the revenue at risk
- Prioritize high-value interventions
- Track whether interventions worked (closed-loop learning)

---

## SUCCESS CRITERIA

✓ Clusters are meaningful and show different purchase patterns
✓ Forecasts are reasonable (no negative, no extreme outliers)
✓ Leakage signals identify real competitive capture opportunities
✓ Scores are actionable and ranked by impact
✓ Explanations are human-readable for sales teams
✓ System runs daily without errors

---

## DO NOT

- Assume all products behave the same (product_family matters)
- Confuse leakage with churn (different concepts)
- Ignore customer volatility (some customers naturally vary more)
- Create alerts for every small gap (filter by impact)
- Use generic model without domain knowledge

---

## START HERE

1. Create the file structure with 4 classes ✓ (already done)
2. Load and explore the data
3. Implement clustering first (foundation)
4. Implement forecasting second
5. Implement leakage detection
6. Implement scoring and ranking
7. Generate output and integrate

Ask for clarification if needed. The goal is a production-grade module that identifies real commercial opportunities.
