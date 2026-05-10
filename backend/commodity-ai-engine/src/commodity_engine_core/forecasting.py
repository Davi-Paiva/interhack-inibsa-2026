from __future__ import annotations

from .common import *

class DemandForecaster:
    """
    LightGBM-based demand forecasting for commodity products.
    Predicts next 30-day expected sales using a temporal training panel.
    """

    _client_sheet = "clients"
    _product_sheet = "products"
    _client_product_sheet = "client_product_features"
    _cluster_file_name = "cluster_assignments.parquet"
    _target_candidates: Tuple[str, ...] = (
        "target_30d_sales",
        "next_30d_sales",
        "future_30d_sales",
        "expected_30d_sales",
    )
    _time_columns: Tuple[str, ...] = (
        "snapshot_date",
        "feature_date",
        "as_of_date",
        "forecast_date",
        "date",
        "month",
    )
    _customer_id_candidates: Tuple[str, ...] = (
        "customer_id",
        "client_id",
    )
    _product_id_candidates: Tuple[str, ...] = (
        "product_id",
        "product_family",
        "family",
    )
    _priority_client_product_columns: Tuple[str, ...] = (
        "rolling_sales_30d",
        "sales_growth_30d",
        "days_since_last_product_order",
        "client_product_frequency",
        "client_product_avg_ticket",
        "client_product_return_rate",
        "campaign_lift_product",
        "client_product_total_revenue",
        "client_product_total_orders",
    )
    _priority_product_columns: Tuple[str, ...] = (
        "product_growth_30d",
        "product_frequency",
        "product_return_rate",
    )
    _priority_client_columns: Tuple[str, ...] = (
        "customer_frequency",
        "customer_frequency_log1p",
        "campaign_lift",
        "is_active_customer",
    )
    _client_table_candidates: Tuple[str, ...] = (
        "clients.csv",
        "client_features.csv",
        "client_features.parquet",
        "clients.parquet",
    )
    _product_table_candidates: Tuple[str, ...] = (
        "products.csv",
        "product_features.csv",
        "product_features.parquet",
        "products.parquet",
    )
    _client_product_table_candidates: Tuple[str, ...] = (
        "client_product_features.csv",
        "client_product_features.parquet",
    )
    _model_file_name = "consumption_forecaster.pkl"

    def __init__(self, model_params: Optional[Dict] = None):
        self.model = None
        self.model_backend = "lightgbm" if lgb is not None else "sklearn"
        self.feature_names: List[str] = []
        self.raw_feature_columns: List[str] = []
        self.feature_dtypes: Dict[str, str] = {}
        self.categorical_levels: Dict[str, List[str]] = {}
        self.numeric_fill_values: Dict[str, float] = {}
        self.validation_rmse_: Optional[float] = None
        self.validation_mae_: Optional[float] = None
        self.base_confidence_: float = 0.5
        self.train_feature_means_: Optional[pd.Series] = None
        self.train_feature_stds_: Optional[pd.Series] = None
        self.training_order_: Optional[pd.Series] = None
        self.target_column: Optional[str] = None
        self.product_key_column: Optional[str] = None
        self.customer_key_column: str = "customer_id"
        self.model_params = model_params or {
            "learning_rate": 0.05,
            "num_leaves": 31,
            "max_depth": 5,
            "objective": "regression",
            "metric": "rmse",
            "verbosity": -1,
            "seed": 42,
        }

    def load_inputs(self, features_dir: Path, commodity_output_dir: Path) -> pd.DataFrame:
        """Load and merge latest feature tables with cluster assignments."""
        features_dir = Path(features_dir)
        commodity_output_dir = Path(commodity_output_dir)
        if not features_dir.exists():
            raise FileNotFoundError(f"Features directory not found: {features_dir}")
        if not commodity_output_dir.exists():
            raise FileNotFoundError(f"Commodity output directory not found: {commodity_output_dir}")

        client_product_path = _resolve_existing_path(
            features_dir,
            self._client_product_table_candidates,
            "client-product table",
        )
        product_path = _resolve_existing_path(
            features_dir,
            self._product_table_candidates,
            "product table",
        )
        client_path = _resolve_existing_path(
            features_dir,
            self._client_table_candidates,
            "client table",
        )
        cluster_path = commodity_output_dir / self._cluster_file_name
        if not cluster_path.exists():
            raise FileNotFoundError(f"Missing cluster assignments file: {cluster_path}")

        logger.info("Loading forecast inputs from %s", features_dir)
        client_product_df = _read_frame(client_product_path)
        product_df = _read_frame(product_path)
        client_df = _read_frame(client_path)
        cluster_df = _read_frame(cluster_path)
        return self.merge_feature_tables(
            client_product_df,
            product_df,
            client_df,
            cluster_df,
            source_names={
                "client_product": client_product_path.name,
                "product": product_path.name,
                "client": client_path.name,
            },
            require_target=False,
        )

    def merge_feature_tables(
        self,
        client_product_df: pd.DataFrame,
        product_df: pd.DataFrame,
        client_df: pd.DataFrame,
        cluster_df: pd.DataFrame,
        *,
        source_names: Optional[dict] = None,
        require_target: bool = False,
    ) -> pd.DataFrame:
        """Canonicalize, validate, and merge feature tables."""
        source_names = source_names or {
            "client_product": "client_product_features",
            "product": "products",
            "client": "clients",
        }
        schema_contracts = self._load_schema_contracts()

        client_product_df = self._canonicalize_client_product_df(client_product_df)
        product_df = self._canonicalize_product_df(product_df)
        client_df = self._canonicalize_client_df(client_df)
        cluster_df = self._canonicalize_cluster_df(cluster_df)

        self._validate_input_table(
            client_product_df,
            schema_contracts[self._client_product_sheet],
            source_names["client_product"],
            self._priority_client_product_columns,
            ("customer_id", self._resolved_product_key(client_product_df)),
        )
        self._validate_input_table(
            product_df,
            schema_contracts[self._product_sheet],
            source_names["product"],
            self._priority_product_columns,
            (self._resolved_product_key(product_df),),
        )
        self._validate_input_table(
            client_df,
            schema_contracts[self._client_sheet],
            source_names["client"],
            self._priority_client_columns,
            ("customer_id",),
        )
        self._validate_cluster_assignments(cluster_df)

        merged = client_product_df.merge(
            client_df,
            how="left",
            on="customer_id",
            suffixes=("", "_client"),
            validate="many_to_one",
        )
        product_key = self._resolved_product_key(client_product_df)
        merged = merged.merge(
            product_df,
            how="left",
            on=product_key,
            suffixes=("", "_product"),
            validate="many_to_one",
        )
        merged = merged.merge(
            cluster_df[["customer_id", "cluster_id"]],
            how="left",
            on="customer_id",
            validate="many_to_one",
        )

        self.product_key_column = product_key
        merged = _normalize_frame_types(merged)
        self.validate_schema(merged, require_target=require_target)
        return merged

    def validate_schema(self, df: pd.DataFrame, *, require_target: bool = True) -> None:
        """Validate merged forecast schema before training or inference."""
        if df.empty:
            raise ValueError("Forecast input DataFrame is empty")

        required_columns = {
            "customer_id",
            "cluster_id",
            self._resolved_product_key(df),
        }
        for column_group in (
            self._priority_client_product_columns,
            self._priority_product_columns,
            self._priority_client_columns,
        ):
            required_columns.update(column_group)

        missing_columns = sorted(column for column in required_columns if column not in df.columns)
        if missing_columns:
            raise ValueError(
                "Merged forecast frame is missing required columns: "
                + ", ".join(missing_columns)
            )

        if require_target:
            self.target_column = None
            for column in self._target_candidates:
                if column in df.columns:
                    self.target_column = column
                    break
            if self.target_column is None:
                raise ValueError(
                    "Forecast target column not found. Expected one of: "
                    + ", ".join(self._target_candidates)
                )

    def build_training_frame(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare the model feature matrix and supervised target."""
        self.validate_schema(df, require_target=True)
        assert self.target_column is not None
        target = pd.to_numeric(df[self.target_column], errors="coerce")
        if target.isna().all():
            raise ValueError(f"Target column {self.target_column} contains only NaN values")

        model_df = self._build_raw_feature_frame(df)
        valid_mask = target.notna()
        model_df = model_df.loc[valid_mask].reset_index(drop=True)
        target = target.loc[valid_mask].clip(lower=0).reset_index(drop=True)

        self.training_order_ = self._build_time_order(model_df)
        X = self._prepare_model_frame(model_df, fit=True)
        self.raw_feature_columns = model_df.columns.tolist()
        self.feature_names = X.columns.tolist()
        return X, target

    def build_prediction_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        """Select raw model columns for inference after training."""
        if not self.raw_feature_columns:
            raise ValueError("Model feature columns are not initialized")
        self.validate_schema(df, require_target=False)
        frame = df.copy()
        for column in self.raw_feature_columns:
            if column not in frame.columns:
                frame[column] = pd.NA
        return frame.loc[:, self.raw_feature_columns].copy()

    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        """Train the demand forecasting model using a time-aware split."""
        if X.empty or y.empty:
            raise ValueError("Cannot train forecast model on empty data")

        if self.training_order_ is not None and len(self.training_order_) == len(X):
            order = self.training_order_
        else:
            order = self._build_time_order(X)
        train_idx, val_idx = self._time_aware_split_indices(order, len(X))

        X_train = X.iloc[train_idx].reset_index(drop=True)
        y_train = y.iloc[train_idx].reset_index(drop=True)
        X_val = X.iloc[val_idx].reset_index(drop=True)
        y_val = y.iloc[val_idx].reset_index(drop=True)

        self.train_feature_means_ = X_train.mean()
        self.train_feature_stds_ = X_train.std(ddof=0).replace(0, 1).fillna(1)

        if self.model_backend == "lightgbm":
            train_data = lgb.Dataset(X_train, label=y_train, feature_name=self.feature_names)
            valid_sets = [train_data]
            valid_names = ["train"]
            callbacks = []
            if not X_val.empty:
                valid_data = lgb.Dataset(
                    X_val,
                    label=y_val,
                    feature_name=self.feature_names,
                    reference=train_data,
                )
                valid_sets.append(valid_data)
                valid_names.append("valid")
                callbacks.append(lgb.early_stopping(20, verbose=False))
            self.model = lgb.train(
                self.model_params,
                train_data,
                num_boost_round=200,
                valid_sets=valid_sets,
                valid_names=valid_names,
                callbacks=callbacks,
            )
        else:
            self.model = RandomForestRegressor(
                n_estimators=300,
                max_depth=8,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
            )
            self.model.fit(X_train, y_train)

        eval_features = X_val if not X_val.empty else X_train
        eval_target = y_val if not y_val.empty else y_train
        eval_pred = np.clip(self.predict(eval_features), a_min=0, a_max=None)
        residuals = eval_target.to_numpy(dtype=float) - eval_pred
        self.validation_rmse_ = float(np.sqrt(np.mean(np.square(residuals))))
        self.validation_mae_ = float(np.mean(np.abs(residuals)))
        denominator = float(np.mean(np.abs(eval_target.to_numpy(dtype=float)))) + 1e-6
        relative_error = min(self.validation_mae_ / denominator, 1.0)
        self.base_confidence_ = float(np.clip(1.0 - relative_error, 0.05, 0.95))

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict expected consumption."""
        if self.model is None:
            raise ValueError("Model not trained yet")
        transformed = self._prepare_model_frame(X, fit=False)
        predictions = self.model.predict(transformed)
        return np.clip(np.asarray(predictions, dtype=float), a_min=0, a_max=None)

    def estimate_confidence(self, X: pd.DataFrame, y_pred: np.ndarray) -> np.ndarray:
        """Estimate per-row forecast confidence in the [0, 1] range."""
        if self.train_feature_means_ is None or self.train_feature_stds_ is None:
            raise ValueError("Forecast model must be trained before estimating confidence")
        transformed = self._prepare_model_frame(X, fit=False)
        aligned_means = self.train_feature_means_.reindex(transformed.columns).fillna(0)
        aligned_stds = self.train_feature_stds_.reindex(transformed.columns).fillna(1)
        z_scores = ((transformed - aligned_means) / aligned_stds).abs().replace([np.inf, -np.inf], 0)
        drift_penalty = np.tanh(z_scores.mean(axis=1) / 3.0)

        scale = (
            self.validation_rmse_
            if self.validation_rmse_ is not None and self.validation_rmse_ > 0
            else max(float(np.nanmean(np.abs(y_pred))), 1.0)
        )
        uncertainty = np.clip(np.abs(y_pred) / (np.abs(y_pred) + scale), 0, 1)
        confidence = self.base_confidence_ * (1 - 0.5 * drift_penalty) * (0.6 + 0.4 * uncertainty)
        confidence = np.nan_to_num(confidence.to_numpy(dtype=float), nan=self.base_confidence_)
        return np.clip(confidence, 0, 1)

    def save_outputs(
        self,
        output_dir: Path,
        base_df: pd.DataFrame,
        y_pred: np.ndarray,
        confidence: np.ndarray,
    ) -> Path:
        """Persist the consumption forecast parquet output."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        product_key = self._resolved_product_key(base_df)
        export_df = pd.DataFrame(
            {
                "customer_id": base_df["customer_id"].astype("string"),
                product_key: base_df[product_key].astype("string"),
                "predicted_30d_sales": np.clip(np.asarray(y_pred, dtype=float), 0, None),
                "forecast_confidence": np.clip(np.asarray(confidence, dtype=float), 0, 1),
                "forecast_date": self._build_forecast_dates(base_df),
            }
        )
        if export_df.isna().any().any():
            missing_columns = export_df.columns[export_df.isna().any()].tolist()
            raise ValueError("Forecast output contains NaN values in columns: " + ", ".join(missing_columns))
        output_path = output_dir / "consumption_forecast.parquet"
        _write_parquet(export_df, output_path)
        logger.info("Saved consumption forecast to %s", output_path)
        return output_path

    def get_feature_importance(self) -> Dict[str, float]:
        if self.model is None:
            return {}
        if self.model_backend == "lightgbm":
            importance = self.model.feature_importance()
        else:
            importance = getattr(self.model, "feature_importances_", np.zeros(len(self.feature_names)))
        return {name: float(imp) for name, imp in zip(self.feature_names, importance)}

    def save_model(self, output_dir: Path) -> Path:
        """Persist the trained forecasting artifact for daily inference."""
        if self.model is None:
            raise ValueError("Cannot persist an untrained forecast model")
        artifact = {
            "model": self.model,
            "model_backend": self.model_backend,
            "feature_names": self.feature_names,
            "raw_feature_columns": self.raw_feature_columns,
            "feature_dtypes": self.feature_dtypes,
            "categorical_levels": self.categorical_levels,
            "numeric_fill_values": self.numeric_fill_values,
            "validation_rmse_": self.validation_rmse_,
            "validation_mae_": self.validation_mae_,
            "base_confidence_": self.base_confidence_,
            "train_feature_means_": self.train_feature_means_,
            "train_feature_stds_": self.train_feature_stds_,
            "training_order_": self.training_order_,
            "target_column": self.target_column,
            "product_key_column": self.product_key_column,
            "customer_key_column": self.customer_key_column,
            "model_params": self.model_params,
        }
        output_path = _write_pickle(artifact, _models_dir(Path(output_dir)) / self._model_file_name)
        logger.info("Saved forecast model artifact to %s", output_path)
        return output_path

    @classmethod
    def load_model(cls, model_path: Path) -> "DemandForecaster":
        """Restore a trained forecasting artifact for inference-only runs."""
        artifact = _read_pickle(Path(model_path))
        forecaster = cls(model_params=artifact.get("model_params"))
        forecaster.model = artifact["model"]
        forecaster.model_backend = artifact["model_backend"]
        forecaster.feature_names = list(artifact["feature_names"])
        forecaster.raw_feature_columns = list(artifact["raw_feature_columns"])
        forecaster.feature_dtypes = dict(artifact["feature_dtypes"])
        forecaster.categorical_levels = dict(artifact["categorical_levels"])
        forecaster.numeric_fill_values = dict(artifact["numeric_fill_values"])
        forecaster.validation_rmse_ = artifact["validation_rmse_"]
        forecaster.validation_mae_ = artifact["validation_mae_"]
        forecaster.base_confidence_ = float(artifact["base_confidence_"])
        forecaster.train_feature_means_ = artifact["train_feature_means_"]
        forecaster.train_feature_stds_ = artifact["train_feature_stds_"]
        forecaster.training_order_ = artifact["training_order_"]
        forecaster.target_column = artifact["target_column"]
        forecaster.product_key_column = artifact["product_key_column"]
        forecaster.customer_key_column = artifact["customer_key_column"]
        return forecaster

    @staticmethod
    def _schema_path() -> Path:
        return BACKEND_ROOT / "data_processing" / "inibsa_feature_tables.xlsx"

    def _load_schema_contracts(self) -> Dict[str, List[str]]:
        schema_path = self._schema_path()
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        try:
            workbook = pd.ExcelFile(schema_path)
        except ImportError as exc:
            raise ImportError(
                "Reading inibsa_feature_tables.xlsx requires 'openpyxl' to be installed"
            ) from exc
        contracts = {}
        for sheet_name in (
            self._client_sheet,
            self._product_sheet,
            self._client_product_sheet,
        ):
            if sheet_name not in workbook.sheet_names:
                raise ValueError(f"Sheet '{sheet_name}' not found in schema workbook")
            sheet_df = pd.read_excel(schema_path, sheet_name=sheet_name)
            if "Column" not in sheet_df.columns:
                raise ValueError(f"Schema sheet '{sheet_name}' must include a 'Column' header")
            contracts[sheet_name] = sheet_df["Column"].dropna().astype(str).str.strip().tolist()
        return contracts

    def _validate_input_table(
        self,
        df: pd.DataFrame,
        schema_columns: List[str],
        file_name: str,
        priority_columns: Iterable[str],
        identifier_columns: Iterable[str],
    ) -> None:
        if df.empty:
            raise ValueError(f"{file_name} is empty")
        required_columns = self._normalize_expected_columns(schema_columns)
        required_columns.update(priority_columns)
        required_columns.update(identifier_columns)
        missing_columns = sorted(column for column in required_columns if column not in df.columns)
        if missing_columns:
            raise ValueError(
                f"{file_name} is missing required columns from Excel contract: "
                + ", ".join(missing_columns)
            )

    def _validate_cluster_assignments(self, df: pd.DataFrame) -> None:
        required_columns = {"customer_id", "cluster_id"}
        missing_columns = sorted(required_columns - set(df.columns))
        if missing_columns:
            raise ValueError(
                "cluster_assignments.parquet is missing required columns: "
                + ", ".join(missing_columns)
            )
        if df["cluster_id"].isna().any():
            raise ValueError("cluster_assignments.parquet contains NaN cluster_id values")

    def _canonicalize_client_product_df(self, df: pd.DataFrame) -> pd.DataFrame:
        renamed = _normalize_frame_types(df)
        customer_column = self._find_first_column(renamed.columns, self._customer_id_candidates)
        if customer_column is None:
            raise ValueError("client_product_features must include client_id or customer_id")
        renamed = renamed.rename(columns={customer_column: "customer_id"})
        if "family" in renamed.columns and "product_family" not in renamed.columns:
            renamed = renamed.rename(columns={"family": "product_family"})
        if "client_product_total_orders" not in renamed.columns:
            total_orders_candidates = (
                "client_product_total_units",
                "client_product_orders",
                "client_product_total_transactions",
            )
            fallback = self._find_first_column(renamed.columns, total_orders_candidates)
            if fallback is not None:
                renamed = renamed.rename(columns={fallback: "client_product_total_orders"})
        return renamed

    def _canonicalize_product_df(self, df: pd.DataFrame) -> pd.DataFrame:
        renamed = _normalize_frame_types(df)
        if "family" in renamed.columns and "product_family" not in renamed.columns:
            renamed = renamed.rename(columns={"family": "product_family"})
        return renamed

    def _canonicalize_client_df(self, df: pd.DataFrame) -> pd.DataFrame:
        renamed = _normalize_frame_types(df)
        customer_column = self._find_first_column(renamed.columns, self._customer_id_candidates)
        if customer_column is None:
            raise ValueError("client features must include client_id or customer_id")
        return renamed.rename(columns={customer_column: "customer_id"})

    def _canonicalize_cluster_df(self, df: pd.DataFrame) -> pd.DataFrame:
        renamed = _normalize_frame_types(df)
        customer_column = self._find_first_column(renamed.columns, self._customer_id_candidates)
        if customer_column is None:
            raise ValueError("cluster_assignments.parquet must include client_id or customer_id")
        renamed = renamed.rename(columns={customer_column: "customer_id"})
        renamed["cluster_id"] = pd.to_numeric(renamed["cluster_id"], errors="coerce")
        return renamed

    @staticmethod
    def _normalize_expected_columns(columns: Iterable[str]) -> set[str]:
        normalized = set()
        for column in columns:
            if column == "client_id":
                normalized.add("customer_id")
            elif column == "family":
                normalized.add("product_family")
            else:
                normalized.add(column)
        return normalized

    @staticmethod
    def _find_first_column(columns: Iterable[str], candidates: Iterable[str]) -> Optional[str]:
        column_set = set(columns)
        for candidate in candidates:
            if candidate in column_set:
                return candidate
        return None

    def _resolved_product_key(self, df: pd.DataFrame) -> str:
        product_key = self._find_first_column(df.columns, self._product_id_candidates)
        if product_key is None:
            raise ValueError("Forecast inputs must include product_id or product_family/family")
        return product_key

    def _build_raw_feature_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        excluded_columns = {
            "customer_id",
            "cluster_id",
            "predicted_30d_sales",
            "forecast_confidence",
            "baseline_30d_sales",
        }
        if self.target_column is not None:
            excluded_columns.add(self.target_column)

        feature_columns = [
            column
            for column in df.columns
            if column not in excluded_columns and not column.endswith("_id")
        ]
        feature_columns.append("cluster_id")
        feature_columns = list(dict.fromkeys(feature_columns))

        missing_for_training = [column for column in feature_columns if column not in df.columns]
        if missing_for_training:
            raise ValueError("Missing expected training columns: " + ", ".join(missing_for_training))
        return df.loc[:, feature_columns].copy()

    def _prepare_model_frame(self, df: pd.DataFrame, fit: bool) -> pd.DataFrame:
        frame = _normalize_frame_types(df)
        transformed_columns: Dict[str, pd.Series] = {}
        for column in frame.columns:
            if fit:
                inferred_numeric = pd.to_numeric(frame[column], errors="coerce")
                numeric_ratio = inferred_numeric.notna().mean()
                if numeric_ratio >= 0.8:
                    fill_value = inferred_numeric.median()
                    if pd.isna(fill_value):
                        fill_value = 0.0
                    self.feature_dtypes[column] = "numeric"
                    self.numeric_fill_values[column] = float(fill_value)
                    transformed_columns[column] = inferred_numeric.fillna(fill_value).astype(float)
                else:
                    values = frame[column].astype("string").fillna("__missing__")
                    categories = pd.Index(values.unique()).astype(str).tolist()
                    self.feature_dtypes[column] = "categorical"
                    self.categorical_levels[column] = categories
                    codes = pd.Categorical(values, categories=categories).codes.astype(float)
                    transformed_columns[column] = pd.Series(codes, index=frame.index)
            else:
                dtype = self.feature_dtypes.get(column)
                if dtype == "numeric":
                    numeric_series = pd.to_numeric(frame[column], errors="coerce")
                    fill_value = self.numeric_fill_values.get(column, 0.0)
                    transformed_columns[column] = numeric_series.fillna(fill_value).astype(float)
                elif dtype == "categorical":
                    categories = list(self.categorical_levels.get(column, []))
                    if "__unseen__" not in categories:
                        categories.append("__unseen__")
                    values = frame[column].astype("string").fillna("__missing__")
                    values = values.where(values.isin(categories), "__unseen__")
                    codes = pd.Categorical(values, categories=categories).codes.astype(float)
                    transformed_columns[column] = pd.Series(codes, index=frame.index)
                else:
                    transformed_columns[column] = pd.Series(0.0, index=frame.index)
        transformed = pd.DataFrame(transformed_columns, index=frame.index)
        transformed = transformed.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        if not fit:
            for missing_column in self.feature_names:
                if missing_column not in transformed.columns:
                    transformed[missing_column] = 0.0
            transformed = transformed.loc[:, self.feature_names]
        return transformed

    def _build_time_order(self, X: pd.DataFrame) -> pd.Series:
        for column in self._time_columns:
            if column not in X.columns:
                continue
            series = X[column]
            if column == "month":
                parsed = pd.to_numeric(series, errors="coerce")
            else:
                parsed = pd.to_datetime(series, errors="coerce")
                if parsed.notna().sum() > 0:
                    numeric_order = parsed.map(lambda value: value.value if pd.notna(value) else np.nan)
                    numeric_order = numeric_order.fillna(numeric_order.median()).fillna(0)
                    return pd.Series(numeric_order, index=X.index)
            if parsed.notna().sum() > 0:
                return pd.Series(parsed, index=X.index)
        if "days_since_last_product_order" in X.columns:
            fallback = pd.to_numeric(X["days_since_last_product_order"], errors="coerce").fillna(0)
            return fallback * -1
        return pd.Series(np.arange(len(X)), index=X.index)

    @staticmethod
    def _time_aware_split_indices(order: pd.Series, total_rows: int) -> Tuple[np.ndarray, np.ndarray]:
        if total_rows < 2:
            single_index = np.arange(total_rows)
            return single_index, single_index
        ordered_index = order.sort_values(kind="mergesort").index.to_numpy()
        split_point = max(int(total_rows * 0.8), 1)
        split_point = min(split_point, total_rows - 1)
        train_idx = ordered_index[:split_point]
        val_idx = ordered_index[split_point:]
        return train_idx, val_idx

    def _build_forecast_dates(self, base_df: pd.DataFrame) -> pd.Series:
        for column in self._time_columns:
            if column not in base_df.columns:
                continue
            parsed = pd.to_datetime(base_df[column], errors="coerce")
            if parsed.notna().sum() == 0:
                continue
            return (parsed + pd.Timedelta(days=30)).dt.date.astype("string")
        fallback_date = pd.Timestamp.utcnow().date().isoformat()
        return pd.Series([fallback_date] * len(base_df), index=base_df.index, dtype="string")

