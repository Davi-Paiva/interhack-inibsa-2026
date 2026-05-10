from __future__ import annotations

from .common import *

class CommodityCustomerCluster:
    """
    KMeans clustering for commodity product customers.
    Segments customers by purchasing behavior using current client feature tables.
    """

    _cluster_feature_columns: Tuple[str, ...] = (
        "customer_total_revenue",
        "customer_total_orders",
        "customer_avg_ticket",
        "customer_frequency",
        "customer_frequency_log1p",
        "days_since_last_order",
        "is_active_customer",
        "return_rate_30d",
        "campaign_lift",
        "coefficient_variation_30d",
    )
    _excel_required_columns: Tuple[str, ...] = (
        "customer_total_revenue",
        "customer_total_orders",
        "customer_avg_ticket",
        "customer_frequency",
        "days_since_last_order",
        "return_rate_30d",
        "campaign_lift",
        "coefficient_variation_30d",
    )
    _zero_fill_columns: Tuple[str, ...] = (
        "return_rate_30d",
        "campaign_lift",
    )
    _customer_id_columns: Tuple[str, ...] = (
        "client_id",
        "customer_id",
    )
    _client_table_candidates: Tuple[str, ...] = (
        "clients.csv",
        "client_features.csv",
        "client_features.parquet",
        "clients.parquet",
    )
    _model_file_name = "customer_clustering.pkl"

    def __init__(self, n_clusters: int = 3, random_state: int = 42):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
        self.scaler = StandardScaler()

    def load_inputs(self, features_dir: Path) -> pd.DataFrame:
        """Load client-level feature tables for clustering."""
        features_dir = Path(features_dir)
        if not features_dir.exists():
            raise FileNotFoundError(f"Features directory not found: {features_dir}")

        client_path = _resolve_existing_path(
            features_dir,
            self._client_table_candidates,
            "client table",
        )
        logger.info("Loading client features from %s", client_path)
        df = _normalize_frame_types(_read_frame(client_path))
        if df.empty:
            raise ValueError(f"{client_path.name} is empty")
        logger.info("Loaded %s rows with %s columns", len(df), len(df.columns))
        return df

    def validate_schema(self, df: pd.DataFrame) -> None:
        """Validate the input schema against the Excel definition plus real model extras."""
        if df.empty:
            raise ValueError("Input features DataFrame is empty")

        schema_columns = self._load_schema_columns()
        missing_in_schema = sorted(set(self._excel_required_columns) - set(schema_columns))
        if missing_in_schema:
            missing = ", ".join(missing_in_schema)
            raise ValueError(f"Excel schema missing required clustering columns: {missing}")

        missing_in_df = sorted(set(self._cluster_feature_columns) - set(df.columns))
        if missing_in_df:
            missing = ", ".join(missing_in_df)
            raise ValueError(f"Input data missing required clustering columns: {missing}")

        id_column = self._resolve_customer_id_column(df.columns)
        if id_column is None:
            raise ValueError("Input data must include client_id or customer_id")

    def prepare_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare standardized numeric feature matrix for clustering."""
        self.validate_schema(df)
        features = self._coerce_and_fill(df.loc[:, self._cluster_feature_columns])
        if hasattr(self.scaler, "mean_"):
            scaled = self.scaler.transform(features)
        else:
            scaled = self.scaler.fit_transform(features)
        return pd.DataFrame(scaled, columns=self._cluster_feature_columns, index=df.index)

    def fit(self, X: pd.DataFrame, raw_df: Optional[pd.DataFrame] = None) -> None:
        """Fit KMeans clustering on a prepared feature matrix."""
        if X is None or len(X) == 0:
            raise ValueError("Cannot fit clustering on empty feature matrix")
        self.kmeans.fit(X)
        counts = np.bincount(self.kmeans.labels_, minlength=self.n_clusters)
        if (counts == 0).any():
            raise ValueError("At least one cluster has zero customers; adjust n_clusters")
        if raw_df is not None:
            self._remap_cluster_order(raw_df, self.kmeans.labels_)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict cluster assignments for a prepared feature matrix."""
        if not hasattr(self.kmeans, "cluster_centers_"):
            raise ValueError("KMeans model is not fitted yet")
        return self.kmeans.predict(X)

    def build_cluster_profiles(self, raw_df: pd.DataFrame, labels: np.ndarray) -> pd.DataFrame:
        """Build mean profiles and counts for each cluster."""
        if raw_df.empty:
            raise ValueError("Cannot build profiles from empty data")
        self.validate_schema(raw_df)
        profiles_source = self._coerce_and_fill(raw_df.loc[:, self._cluster_feature_columns])
        profiles_source["cluster_id"] = labels
        means = profiles_source.groupby("cluster_id")[list(self._cluster_feature_columns)].mean()
        counts = profiles_source.groupby("cluster_id").size().rename("count")
        profiles = means.join(counts).reset_index().sort_values("cluster_id").reset_index(drop=True)
        profiles["cluster_name"] = profiles["cluster_id"].map(self.get_cluster_name)
        if (profiles["count"] == 0).any():
            raise ValueError("Cluster profiles contain empty clusters")
        return profiles

    def compute_metrics(self, X: pd.DataFrame, labels: np.ndarray) -> dict:
        counts = pd.Series(labels).value_counts().sort_index()
        total = int(counts.sum()) if len(counts) else 0
        return {
            "n_clusters": int(self.n_clusters),
            "rows": int(len(X)),
            "inertia": float(self.kmeans.inertia_),
            "silhouette_score": float(silhouette_score(X, labels)) if len(counts) > 1 else 0.0,
            "davies_bouldin_score": float(davies_bouldin_score(X, labels)) if len(counts) > 1 else 0.0,
            "calinski_harabasz_score": float(calinski_harabasz_score(X, labels)) if len(counts) > 1 else 0.0,
            "cluster_counts": {str(int(cluster_id)): int(count) for cluster_id, count in counts.items()},
            "cluster_labels": {str(int(cluster_id)): self.get_cluster_name(int(cluster_id)) for cluster_id in counts.index},
            "min_cluster_share": float(counts.min() / total) if total else 0.0,
        }

    def save_outputs(
        self,
        output_dir: Path,
        customer_ids: pd.Series,
        labels: np.ndarray,
        profiles: pd.DataFrame,
    ) -> Tuple[Path, Path]:
        """Persist cluster assignments and profiles to parquet files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        assignments = pd.DataFrame(
            {
                "customer_id": customer_ids.astype("string"),
                "cluster_id": labels.astype(int),
            }
        )
        assignments_path = _write_parquet(assignments, output_dir / "cluster_assignments.parquet")
        profiles_path = _write_parquet(profiles, output_dir / "cluster_profiles.parquet")
        logger.info("Saved cluster assignments to %s", assignments_path)
        logger.info("Saved cluster profiles to %s", profiles_path)
        return assignments_path, profiles_path

    def save_model(self, output_dir: Path) -> Path:
        """Persist the trained clustering artifact for daily inference."""
        if not hasattr(self.kmeans, "cluster_centers_"):
            raise ValueError("Cannot persist an unfitted clustering model")
        artifact = {
            "n_clusters": self.n_clusters,
            "random_state": self.random_state,
            "kmeans": self.kmeans,
            "scaler": self.scaler,
        }
        output_path = _write_pickle(artifact, _models_dir(Path(output_dir)) / self._model_file_name)
        logger.info("Saved clustering model artifact to %s", output_path)
        return output_path

    @classmethod
    def load_model(cls, model_path: Path) -> "CommodityCustomerCluster":
        """Restore a trained clustering artifact for inference-only runs."""
        artifact = _read_pickle(Path(model_path))
        clusterer = cls(
            n_clusters=int(artifact["n_clusters"]),
            random_state=int(artifact["random_state"]),
        )
        clusterer.kmeans = artifact["kmeans"]
        clusterer.scaler = artifact["scaler"]
        return clusterer

    def get_cluster_name(self, cluster_id: int) -> str:
        if self.n_clusters == 3:
            try:
                return CustomerCluster(cluster_id).name.lower()
            except ValueError:
                return f"cluster_{cluster_id}"
        return f"cluster_{cluster_id}"

    @staticmethod
    def _schema_path() -> Path:
        return BACKEND_ROOT / "data_processing" / "inibsa_feature_tables.xlsx"

    def _load_schema_columns(self) -> List[str]:
        schema_path = self._schema_path()
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        try:
            schema_df = pd.read_excel(schema_path, sheet_name="clients")
        except ImportError as exc:
            raise ImportError(
                "Reading inibsa_feature_tables.xlsx requires 'openpyxl' to be installed"
            ) from exc
        except ValueError as exc:
            raise ValueError("Sheet 'clients' not found in schema workbook") from exc
        if "Column" not in schema_df.columns:
            raise ValueError("Schema sheet must include a 'Column' header")
        return schema_df["Column"].dropna().astype(str).str.strip().tolist()

    def _coerce_and_fill(self, features: pd.DataFrame) -> pd.DataFrame:
        filled = features.copy()
        for column in self._cluster_feature_columns:
            if column == "is_active_customer":
                filled[column] = _normalize_boolean(filled[column]).astype(int)
            else:
                filled[column] = pd.to_numeric(filled[column], errors="coerce")
        for column in self._zero_fill_columns:
            filled[column] = filled[column].fillna(0.0)
        for column in self._cluster_feature_columns:
            if column in self._zero_fill_columns:
                continue
            median_value = filled[column].median()
            if pd.isna(median_value):
                median_value = 0.0
            filled[column] = filled[column].fillna(median_value)
        return filled.fillna(0.0)

    def _resolve_customer_id_column(self, columns: Iterable[str]) -> Optional[str]:
        column_set = set(columns)
        for candidate in self._customer_id_columns:
            if candidate in column_set:
                return candidate
        return None

    def _remap_cluster_order(self, raw_df: pd.DataFrame, labels: np.ndarray) -> None:
        profiles_source = self._coerce_and_fill(raw_df.loc[:, self._cluster_feature_columns])
        profiles_source["cluster_id"] = labels
        ordering = (
            profiles_source.groupby("cluster_id")
            .agg(
                revenue=("customer_total_revenue", "mean"),
                frequency=("customer_frequency", "mean"),
                recency=("days_since_last_order", "mean"),
                active_ratio=("is_active_customer", "mean"),
                return_rate_30d=("return_rate_30d", "mean"),
                coefficient_variation_30d=("coefficient_variation_30d", "mean"),
            )
            .sort_values(
                ["revenue", "frequency", "recency", "active_ratio"],
                ascending=[False, False, True, False],
            )
        )
        if self.n_clusters == 3:
            ordered_cluster_ids = self._business_cluster_order(ordering)
        else:
            ordered_cluster_ids = ordering.index.tolist()
        mapping = {old_id: new_id for new_id, old_id in enumerate(ordered_cluster_ids)}
        reordered_centers = self.kmeans.cluster_centers_[ordered_cluster_ids]
        self.kmeans.cluster_centers_ = reordered_centers
        self.kmeans.labels_ = np.asarray([mapping[label] for label in labels], dtype=int)

    def _business_cluster_order(self, ordering: pd.DataFrame) -> List[int]:
        profiles = ordering.copy()
        revenue = self._scale_series(profiles["revenue"], high_is_good=True)
        frequency = self._scale_series(profiles["frequency"], high_is_good=True)
        recency = self._scale_series(profiles["recency"], high_is_good=True)
        active_ratio = self._scale_series(profiles["active_ratio"], high_is_good=True)

        profiles["loyal_score"] = revenue + frequency + active_ratio + (1 - recency)
        profiles["marginal_score"] = recency + (1 - active_ratio) + (1 - revenue) + (1 - frequency)
        profiles["promiscuous_score"] = (
            self._scale_series(profiles["frequency"], high_is_good=True) * 0.5
            + self._scale_series(profiles["active_ratio"], high_is_good=True) * 0.25
            + self._scale_series(profiles["recency"], high_is_good=False) * 0.25
        )
        if "return_rate_30d" in profiles.columns:
            profiles["promiscuous_score"] = profiles["promiscuous_score"] + self._scale_series(
                profiles["return_rate_30d"], high_is_good=True
            )
        if "coefficient_variation_30d" in profiles.columns:
            profiles["promiscuous_score"] = profiles["promiscuous_score"] + self._scale_series(
                profiles["coefficient_variation_30d"], high_is_good=True
            )

        available_ids = set(profiles.index.tolist())
        marginal_id = int(profiles["marginal_score"].idxmax())
        available_ids.remove(marginal_id)
        loyal_candidates = profiles.loc[list(available_ids)]
        loyal_id = int(loyal_candidates["loyal_score"].idxmax())
        available_ids.remove(loyal_id)
        promiscuous_id = int(next(iter(available_ids)))
        return [marginal_id, loyal_id, promiscuous_id]

    @staticmethod
    def _scale_series(series: pd.Series, *, high_is_good: bool) -> pd.Series:
        numeric = pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)
        if numeric.nunique() <= 1:
            scaled = pd.Series(0.0, index=numeric.index, dtype=float)
        else:
            scaled = (numeric - numeric.min()) / (numeric.max() - numeric.min())
        return scaled if high_is_good else 1.0 - scaled

