You are implementing Component 2/5 of the Commodity AI Engine: Consumption Forecast.

Objective:
Forecast short-term commodity demand using existing engineered features and cluster assignments.

Critical context:
- Feature engineering tables already exist and must be reused.
- Do not engineer features from raw CSV in this component.
- This module must be modular and compatible with both historical and daily mode.
- Read `backend/data_processing/inibsa_feature_tables.xlsx` first and validate table schemas before training.
- If there is any column mismatch, Excel schema prevails.

Input data contract:
- Feature path pattern: backend/processed_data/<mode>/features/
- Component 1 output path: backend/commodity-ai-engine/output/<mode>/
- Required files:
  - client_product_features.parquet
  - product_features.parquet
  - client_features.parquet
  - cluster_assignments.parquet

Schema contract:
- Source of truth: `backend/data_processing/inibsa_feature_tables.xlsx`
- Validate client/product/client-product columns against Excel before merging.

Priority columns expected:
- Client-product:
  - rolling_sales_30d
  - sales_growth_30d
  - days_since_last_product_order
  - client_product_frequency
  - client_product_avg_ticket
  - client_product_return_rate
  - campaign_lift_product
  - client_product_total_revenue
  - client_product_total_orders
- Product:
  - product_growth_30d
  - product_frequency
  - product_return_rate
- Client:
  - customer_frequency
  - campaign_lift

Model scope:
- Use LightGBM regressor (or sklearn fallback if unavailable).
- Predict next 30-day expected sales per customer_id + product_id (or product_family if only that key exists).
- Include simple confidence estimation.

Class requirements:
```python
class DemandForecaster:
    def __init__(self, model_params: dict | None = None): ...
    def load_inputs(self, features_dir: Path, commodity_output_dir: Path) -> pd.DataFrame: ...
    def validate_schema(self, df: pd.DataFrame) -> None: ...
    def build_training_frame(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]: ...
    def train(self, X: pd.DataFrame, y: pd.Series) -> None: ...
    def predict(self, X: pd.DataFrame) -> np.ndarray: ...
    def estimate_confidence(self, X: pd.DataFrame, y_pred: np.ndarray) -> np.ndarray: ...
    def save_outputs(self, output_dir: Path, base_df: pd.DataFrame, y_pred: np.ndarray, confidence: np.ndarray) -> None: ...
```

Output contract:
- Write consumption_forecast.parquet to backend/commodity-ai-engine/output/<mode>/
- Minimum columns:
  - customer_id
  - key product column (product_id or product_family)
  - predicted_30d_sales
  - forecast_confidence
  - forecast_date

Implementation rules:
- Time-aware split for historical training (avoid random leakage).
- No outlier removal.
- Campaign context is valid signal, not anomaly.
- Keep preprocessing explicit and lightweight.
- Use logging and clear validation errors.
- Add a schema validation checkpoint at pipeline start, with explicit error messages per missing column.

Quality checks:
- Non-negative predictions.
- No NaN in outputs.
- Confidence bounded in [0, 1].

Deliverable:
Modular forecast component that directly consumes feature tables and cluster outputs.
