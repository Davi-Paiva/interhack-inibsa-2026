You are implementing Component 5/5 of the Commodity AI Engine: Next Purchase Prediction.

Objective:
Predict the next purchase timing and intervention window using existing feature-engineering outputs and prior component outputs.

Critical context:
- Reuse feature tables and outputs from Components 1-4.
- Do not run a new heavy modeling track.
- Keep approach simple, transparent, and hackathon-friendly.
- Read `backend/data_processing/inibsa_feature_tables.xlsx` before building prediction logic.
- Apply Excel ownership/naming rules as source of truth.

Input data contract:
- Feature path: backend/processed_data/<mode>/features/
- Commodity output path: backend/commodity-ai-engine/output/<mode>/
- Required files:
  - client_product_features.parquet
  - client_features.parquet
  - capture_opportunities.parquet
  - cluster_assignments.parquet (optional but recommended)

Schema contract:
- Source of truth: `backend/data_processing/inibsa_feature_tables.xlsx`
- Validate key columns against Excel before date/probability calculations.

Key columns:
- days_since_last_product_order
- client_product_frequency
- sales_growth_30d
- campaign_lift_product
- coefficient_variation_30d
- capture_score

Prediction logic (first iteration):
1. Estimate interval days with a deterministic rule:
   - estimated_interval_days = 30 / max(client_product_frequency, eps)
   - adjust with variability (coefficient_variation_30d) and growth sign.
2. Estimate next purchase date:
   - next_purchase_date = reference_date + estimated_interval_days - days_since_last_product_order
   - clip to at least reference_date + 1 day.
3. Estimate purchase probability in [0, 1] using:
   - recency fit
   - capture priority
   - volatility penalty
4. Build contact window:
   - high priority: 1-2 days before expected date
   - medium: 3-5 days before
   - low: 5-7 days before

Class requirements:
```python
class NextPurchasePredictor:
    def __init__(self, min_probability: float = 0.0): ...
    def load_inputs(self, features_dir: Path, commodity_output_dir: Path) -> pd.DataFrame: ...
    def validate_schema(self, df: pd.DataFrame) -> None: ...
    def estimate_interval_days(self, df: pd.DataFrame) -> pd.Series: ...
    def estimate_probability(self, df: pd.DataFrame) -> pd.Series: ...
    def build_predictions(self, df: pd.DataFrame, reference_date: pd.Timestamp) -> pd.DataFrame: ...
    def build_contact_recommendation(self, df: pd.DataFrame) -> pd.Series: ...
    def save_outputs(self, output_dir: Path, df: pd.DataFrame) -> None: ...
```

Output contract:
- Write next_purchase_predictions.parquet to backend/commodity-ai-engine/output/<mode>/
- Minimum columns:
  - customer_id
  - product key column
  - expected_next_purchase_date
  - purchase_probability
  - contact_window_start
  - contact_window_end
  - contact_recommendation

Implementation rules:
- Keep date arithmetic explicit and tested.
- Probability and scores must be clipped to valid ranges.
- Preserve campaign context where available.
- Fail fast on schema mismatches with explicit messages.

Quality checks:
- All predicted dates valid and non-null.
- Probabilities in [0, 1].
- Contact windows coherent (start <= end < expected date).

Deliverable:
Final timing layer that closes the loop from leakage detection to actionable next-step planning.
