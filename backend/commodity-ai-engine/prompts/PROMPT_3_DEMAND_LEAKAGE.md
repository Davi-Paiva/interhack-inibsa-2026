You are implementing Component 3/5 of the Commodity AI Engine: Demand Leakage Estimation.

Objective:
Estimate demand leakage by comparing expected demand vs observed demand using existing feature-engineering outputs and forecast outputs.

Critical context:
- Reuse outputs from Component 2 and data_processing feature tables.
- Do not create new feature-engineering logic here.
- Keep business logic simple and explicit.
- Read `backend/data_processing/inibsa_feature_tables.xlsx` before implementing score logic.
- Enforce Excel table/column contract as source of truth.

Input data contract:
- Feature path: backend/processed_data/<mode>/features/
- Commodity output path: backend/commodity-ai-engine/output/<mode>/
- Required files:
  - consumption_forecast.parquet
  - client_product_features.parquet
  - client_features.parquet

Schema contract:
- Source of truth: `backend/data_processing/inibsa_feature_tables.xlsx`
- Validate required columns from client and client-product tables against Excel definitions.

Key columns used:
- predicted_30d_sales
- rolling_sales_30d (observed baseline)
- sales_growth_30d
- campaign_lift_product
- coefficient_variation_30d
- client_product_return_rate

Leakage logic:
1. Base gap:
   - gap_units = predicted_30d_sales - rolling_sales_30d
   - gap_ratio = gap_units / predicted_30d_sales when predicted > 0
2. Volatility adjustment:
   - Use coefficient_variation_30d to reduce false positives for unstable customers.
3. Campaign-aware adjustment:
   - If campaign lift is high, soften leakage penalty.
4. Final leakage score:
   - bounded [0, 1]

Class requirements:
```python
class DemandLeakageDetector:
    def __init__(self, min_gap_units: float = 0.0, min_gap_ratio: float = 0.0): ...
    def load_inputs(self, features_dir: Path, commodity_output_dir: Path) -> pd.DataFrame: ...
    def validate_schema(self, df: pd.DataFrame) -> None: ...
    def compute_scores(self, df: pd.DataFrame) -> pd.DataFrame: ...
    def classify_risk(self, leakage_score: pd.Series) -> pd.Series: ...
    def filter_actionable(self, df: pd.DataFrame) -> pd.DataFrame: ...
    def save_outputs(self, output_dir: Path, df: pd.DataFrame) -> None: ...
```

Output contract:
- Write demand_leakage_signals.parquet to backend/commodity-ai-engine/output/<mode>/
- Minimum columns:
  - customer_id
  - product key column
  - predicted_30d_sales
  - observed_30d_sales
  - gap_units
  - gap_ratio
  - leakage_score
  - risk_level
  - is_actionable

Implementation rules:
- No outlier removal.
- Campaign period is context, not anomaly.
- Keep formulas transparent and logged.
- Handle divisions by zero safely.
- Fail fast with readable schema errors if required columns are missing.

Quality checks:
- leakage_score in [0, 1].
- No NaN in required output fields.
- Risk classes generated for all rows.

Deliverable:
A robust leakage layer ready for business prioritization.
