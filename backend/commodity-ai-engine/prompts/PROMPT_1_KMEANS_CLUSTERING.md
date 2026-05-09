You are implementing Component 1/5 of the Commodity AI Engine: KMeans Behavioral Clustering.

Objective:
Build a modular clustering component that consumes existing feature-engineering outputs and generates robust customer segments for downstream modules.

Critical context:
- Feature engineering is already implemented in backend/data_processing and must be reused.
- Do not recreate feature engineering logic from raw CSVs.
- Use the feature table schema as source of truth.
- Read `backend/data_processing/inibsa_feature_tables.xlsx` before coding.
- If parquet columns differ from assumptions, follow Excel naming/ownership rules.

Input data contract:
- Base path pattern: backend/processed_data/<mode>/features/
- Mode: historical or daily
- Files required:
  - client_features.parquet
  - client_product_features.parquet (optional enrichment)

Schema contract:
- Source of truth: `backend/data_processing/inibsa_feature_tables.xlsx`
- Validate that `client_features.parquet` contains the exact columns required by the Excel for clustering-ready client behavior features.

Primary features expected in client_features.parquet:
- customer_total_revenue
- customer_total_orders
- customer_avg_ticket
- customer_frequency
- days_since_last_order
- return_rate_30d
- campaign_lift
- coefficient_variation_30d

Tasks:
1. Implement CommodityCustomerCluster in a modular way.
2. Build a preparation method that:
   - Loads parquet tables for a given mode.
  - Validates schema against the Excel definition.
   - Validates required columns.
   - Handles missing values with simple explicit rules (median/zero as justified).
   - Standardizes numeric features.
3. Train KMeans with configurable n_clusters (default 5).
4. Produce interpretable cluster profiles.
5. Persist outputs for downstream components.

Class requirements:
```python
class CommodityCustomerCluster:
    def __init__(self, n_clusters: int = 5, random_state: int = 42): ...
    def load_inputs(self, features_dir: Path) -> pd.DataFrame: ...
    def validate_schema(self, df: pd.DataFrame) -> None: ...
    def prepare_matrix(self, df: pd.DataFrame) -> pd.DataFrame: ...
    def fit(self, X: pd.DataFrame) -> None: ...
    def predict(self, X: pd.DataFrame) -> np.ndarray: ...
    def build_cluster_profiles(self, raw_df: pd.DataFrame, labels: np.ndarray) -> pd.DataFrame: ...
    def save_outputs(self, output_dir: Path, customer_ids: pd.Series, labels: np.ndarray, profiles: pd.DataFrame) -> None: ...
```

Output contract:
- Write to backend/commodity-ai-engine/output/<mode>/
- Files:
  - cluster_assignments.parquet with columns: customer_id, cluster_id
  - cluster_profiles.parquet with aggregate stats per cluster

Implementation rules:
- Keep functions short and readable.
- No outlier removal.
- Use logging for each stage.
- Raise clear errors for missing columns or empty inputs.
- Keep no hidden state beyond fitted scaler/model.

Quality checks:
- Each cluster has at least one customer.
- Cluster profiles include mean and count.
- Reproducibility via random_state.

Deliverable:
Production-friendly clustering module using existing feature tables only.

Pre-delivery checks (mandatory):
- Confirm used columns are documented in `backend/data_processing/inibsa_feature_tables.xlsx`.
- Log schema validation pass/fail before training.
