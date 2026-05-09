You are implementing Component 4/5 of the Commodity AI Engine: Capture Opportunity Scoring.

Objective:
Convert leakage signals into a prioritized action queue for sales, using explicit business-weighted scoring.

Critical context:
- Inputs come from existing feature tables + Component 3 leakage outputs.
- Do not add new feature engineering from raw data.
- Keep the scoring auditable and easy to explain.
- Read `backend/data_processing/inibsa_feature_tables.xlsx` before implementing joins/scoring.
- Treat Excel definitions as the final schema contract.

Input data contract:
- Feature path: backend/processed_data/<mode>/features/
- Commodity output path: backend/commodity-ai-engine/output/<mode>/
- Required files:
  - demand_leakage_signals.parquet
  - client_features.parquet
  - product_features.parquet
  - cluster_assignments.parquet (if available)

Schema contract:
- Source of truth: `backend/data_processing/inibsa_feature_tables.xlsx`
- Validate required columns from client/product/client-product tables before scoring.

Scoring components:
1. Leakage component (weight 0.40)
   - from leakage_score
2. Customer value component (weight 0.30)
   - based on customer_total_revenue, customer_avg_ticket, customer_frequency
3. Urgency component (weight 0.20)
   - based on days_since_last_order, negative sales_growth_30d, and large current gap
4. Confidence component (weight 0.10)
   - from forecast/leakage confidence proxies

Score formula:
- capture_score_0_1 = 0.40*leakage + 0.30*value + 0.20*urgency + 0.10*confidence
- capture_score = 100 * capture_score_0_1

Class requirements:
```python
class CaptureScoringEngine:
    def __init__(self, weights: dict | None = None): ...
    def load_inputs(self, features_dir: Path, commodity_output_dir: Path) -> pd.DataFrame: ...
    def validate_schema(self, df: pd.DataFrame) -> None: ...
    def compute_value_component(self, df: pd.DataFrame) -> pd.Series: ...
    def compute_urgency_component(self, df: pd.DataFrame) -> pd.Series: ...
    def compute_confidence_component(self, df: pd.DataFrame) -> pd.Series: ...
    def score(self, df: pd.DataFrame) -> pd.DataFrame: ...
    def build_recommendations(self, df: pd.DataFrame) -> pd.Series: ...
    def save_outputs(self, output_dir: Path, df: pd.DataFrame) -> None: ...
```

Output contract:
- Write capture_opportunities.parquet to backend/commodity-ai-engine/output/<mode>/
- Minimum columns:
  - customer_id
  - product key column
  - capture_score
  - priority_rank
  - priority_band (critical/high/medium/low)
  - recommended_action

Implementation rules:
- Keep normalization explicit and deterministic.
- No hidden heuristics; every component must be traceable.
- Preserve campaign context in explanations.
- Add a pre-score schema validation checkpoint with clear missing-column errors.

Quality checks:
- capture_score in [0, 100].
- Unique and monotonic priority rank.
- No empty recommendations.

Deliverable:
An auditable opportunity ranking layer directly usable by sales workflows.
