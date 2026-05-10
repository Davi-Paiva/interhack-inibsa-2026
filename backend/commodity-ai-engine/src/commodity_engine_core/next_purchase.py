from __future__ import annotations

from .common import *
from .forecasting import DemandForecaster
from .leakage import DemandLeakageDetector

class NextPurchasePredictor:
    """Predicts next purchase timing and contact windows for capture opportunities."""

    _client_sheet = "clients"
    _client_product_sheet = "client_product_features"
    _capture_candidates: Tuple[str, ...] = ("capture_opportunities.parquet",)
    _client_table_candidates: Tuple[str, ...] = (
        "clients.csv",
        "client_features.csv",
        "client_features.parquet",
        "clients.parquet",
    )
    _client_product_table_candidates: Tuple[str, ...] = (
        "client_product_features.csv",
        "client_product_features.parquet",
    )
    _cluster_file_name = "cluster_assignments.parquet"
    _sales_candidates: Tuple[str, ...] = ("sales_enriched.csv",)
    _required_output_columns: Tuple[str, ...] = (
        "customer_id",
        "expected_next_purchase_date",
        "purchase_probability",
        "contact_window_start",
        "contact_window_end",
        "contact_recommendation",
    )

    def __init__(self, min_probability: float = 0.0):
        self.min_probability = float(min_probability)
        self.product_key_column: Optional[str] = None

    def load_inputs(self, features_dir: Path, commodity_output_dir: Path) -> pd.DataFrame:
        """Load capture opportunities enriched with client-product timing features."""
        features_dir = Path(features_dir)
        commodity_output_dir = Path(commodity_output_dir)

        capture_path = _resolve_existing_path(
            commodity_output_dir,
            self._capture_candidates,
            "capture opportunity output",
        )
        client_product_path = _resolve_existing_path(
            features_dir,
            self._client_product_table_candidates,
            "client-product table",
        )
        client_path = _resolve_existing_path(
            features_dir,
            self._client_table_candidates,
            "client table",
        )

        capture_df = self._canonicalize_capture_df(_read_frame(capture_path))
        client_product_df = self._canonicalize_client_product_df(_read_frame(client_product_path))
        client_df = self._canonicalize_client_df(_read_frame(client_path))
        cluster_path = commodity_output_dir / self._cluster_file_name
        cluster_df: Optional[pd.DataFrame] = None
        if cluster_path.exists():
            cluster_df = self._canonicalize_cluster_df(_read_frame(cluster_path))

        merged = self.merge_feature_tables(
            capture_df,
            client_product_df,
            client_df,
            cluster_df=cluster_df,
            source_names={
                "capture": capture_path.name,
                "client_product": client_product_path.name,
                "client": client_path.name,
            },
        )
        return merged

    def merge_feature_tables(
        self,
        capture_df: pd.DataFrame,
        client_product_df: pd.DataFrame,
        client_df: pd.DataFrame,
        *,
        cluster_df: Optional[pd.DataFrame] = None,
        source_names: Optional[Dict[str, str]] = None,
    ) -> pd.DataFrame:
        source_names = source_names or {
            "capture": "capture_opportunities.parquet",
            "client_product": "client_product_features",
            "client": "clients",
        }
        schema_contracts = self._load_schema_contracts()
        self._validate_input_table(
            client_product_df,
            schema_contracts[self._client_product_sheet],
            source_names["client_product"],
            (
                "days_since_last_product_order",
                "client_product_frequency",
                "sales_growth_30d",
                "campaign_lift_product",
            ),
            ("customer_id", self._resolved_product_key(client_product_df)),
        )
        self._validate_input_table(
            client_df,
            schema_contracts[self._client_sheet],
            source_names["client"],
            ("coefficient_variation_30d", "days_since_last_order"),
            ("customer_id",),
        )
        self._validate_capture_inputs(capture_df, source_names["capture"])
        if cluster_df is not None:
            self._validate_cluster_assignments(cluster_df)

        product_key = self._resolved_product_key(capture_df)
        merged = capture_df.merge(
            client_product_df,
            how="left",
            on=["customer_id", product_key],
            suffixes=("", "_client_product"),
            validate="one_to_one",
        )
        merged = merged.merge(
            client_df,
            how="left",
            on="customer_id",
            suffixes=("", "_client"),
            validate="many_to_one",
        )
        if cluster_df is not None:
            merged = merged.merge(
                cluster_df[["customer_id", "cluster_id"]],
                how="left",
                on="customer_id",
                validate="many_to_one",
                suffixes=("", "_cluster"),
            )
            if "cluster_id_cluster" in merged.columns:
                merged["cluster_id"] = (
                    pd.to_numeric(merged["cluster_id"], errors="coerce")
                    .fillna(pd.to_numeric(merged["cluster_id_cluster"], errors="coerce"))
                )
                merged = merged.drop(columns=["cluster_id_cluster"])

        for primary, duplicate in (
            ("sales_growth_30d", "sales_growth_30d_client_product"),
            ("days_since_last_product_order", "days_since_last_product_order_client_product"),
            ("client_product_frequency", "client_product_frequency_client_product"),
            ("campaign_lift_product", "campaign_lift_product_client_product"),
            ("coefficient_variation_30d", "coefficient_variation_30d_client"),
        ):
            if primary not in merged.columns and duplicate in merged.columns:
                merged = merged.rename(columns={duplicate: primary})
        self.product_key_column = product_key
        merged = _normalize_frame_types(merged)
        self.validate_schema(merged)
        return merged

    def validate_schema(self, df: pd.DataFrame) -> None:
        if df.empty:
            raise ValueError("Next purchase input DataFrame is empty")
        product_key = self._resolved_product_key(df)
        required_columns = {
            "customer_id",
            product_key,
            "capture_score",
            "priority_band",
            "days_since_last_product_order",
            "client_product_frequency",
            "sales_growth_30d",
            "campaign_lift_product",
            "coefficient_variation_30d",
        }
        missing_columns = sorted(column for column in required_columns if column not in df.columns)
        if missing_columns:
            raise ValueError(
                "Next purchase frame is missing required columns: "
                + ", ".join(missing_columns)
            )

    def estimate_interval_days(self, df: pd.DataFrame) -> pd.Series:
        self.validate_schema(df)
        frequency = pd.to_numeric(df["client_product_frequency"], errors="coerce").fillna(0.0).clip(lower=1e-3)
        variability = pd.to_numeric(df["coefficient_variation_30d"], errors="coerce").fillna(0.0).clip(lower=0.0, upper=2.0)
        growth = pd.to_numeric(df["sales_growth_30d"], errors="coerce").fillna(0.0).clip(-1.0, 1.0)
        affinity = self._optional_numeric_series(df, "client_product_embedding_cosine").clip(-1.0, 1.0)
        base_interval = 30.0 / frequency
        variability_adjustment = 1.0 + (0.5 * variability)
        growth_adjustment = 1.0 - (0.15 * growth)
        affinity_adjustment = 1.0 - (0.10 * affinity)
        interval_days = (
            base_interval * variability_adjustment * growth_adjustment * affinity_adjustment
        ).clip(lower=3.0, upper=120.0)
        return pd.Series(interval_days, index=df.index, dtype=float)

    def estimate_probability(self, df: pd.DataFrame) -> pd.Series:
        estimated_interval = pd.to_numeric(df["estimated_interval_days"], errors="coerce").fillna(0.0).clip(lower=1.0)
        days_since = pd.to_numeric(df["days_since_last_product_order"], errors="coerce").fillna(0.0).clip(lower=0.0)
        raw_remaining = pd.to_numeric(df["raw_remaining_days"], errors="coerce").fillna(0.0)
        recency_fit = 1.0 - np.clip(np.abs(raw_remaining) / estimated_interval.replace(0.0, np.nan), 0.0, 1.0)
        recency_fit = pd.Series(recency_fit, index=df.index).fillna(0.0)
        capture_priority = (pd.to_numeric(df["capture_score"], errors="coerce").fillna(0.0) / 100.0).clip(0.0, 1.0)
        volatility_penalty = 1.0 / (
            1.0 + pd.to_numeric(df["coefficient_variation_30d"], errors="coerce").fillna(0.0).clip(lower=0.0)
        )
        affinity = (self._optional_numeric_series(df, "client_product_embedding_cosine").clip(-1.0, 1.0) + 1.0) / 2.0
        probability = (
            0.45 * recency_fit
            + 0.30 * capture_priority
            + 0.15 * volatility_penalty
            + 0.10 * affinity
        ).clip(self.min_probability, 1.0)
        return pd.Series(probability, index=df.index, dtype=float)

    @staticmethod
    def _optional_numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
        if column not in df.columns:
            return pd.Series(0.0, index=df.index, dtype=float)
        return pd.to_numeric(df[column], errors="coerce").fillna(0.0)

    def build_predictions(self, df: pd.DataFrame, reference_date: pd.Timestamp) -> pd.DataFrame:
        self.validate_schema(df)
        reference_date = pd.Timestamp(reference_date).normalize()
        predictions = df.copy()
        predictions["reference_date"] = reference_date
        predictions["estimated_interval_days"] = self.estimate_interval_days(predictions)
        days_since = pd.to_numeric(predictions["days_since_last_product_order"], errors="coerce").fillna(0.0).clip(lower=0.0)
        predictions["raw_remaining_days"] = predictions["estimated_interval_days"] - days_since
        predictions["days_until_expected_purchase"] = np.ceil(
            np.clip(predictions["raw_remaining_days"], 1.0, 120.0)
        ).astype(int)
        predictions["expected_next_purchase_date"] = (
            reference_date + pd.to_timedelta(predictions["days_until_expected_purchase"], unit="D")
        )
        predictions["purchase_probability"] = self.estimate_probability(predictions)

        window_offsets = predictions["priority_band"].astype("string").map(
            {
                "critical": (2, 1),
                "high": (2, 1),
                "medium": (5, 3),
                "low": (7, 5),
            }
        )
        start_offsets = window_offsets.map(lambda item: item[0] if isinstance(item, tuple) else 7).astype(int)
        end_offsets = window_offsets.map(lambda item: item[1] if isinstance(item, tuple) else 5).astype(int)
        predictions["contact_window_start"] = (
            predictions["expected_next_purchase_date"] - pd.to_timedelta(start_offsets, unit="D")
        )
        predictions["contact_window_end"] = (
            predictions["expected_next_purchase_date"] - pd.to_timedelta(end_offsets, unit="D")
        )
        predictions["contact_window_start"] = predictions["contact_window_start"].where(
            predictions["contact_window_start"].ge(reference_date),
            reference_date,
        )
        predictions["contact_window_end"] = predictions["contact_window_end"].where(
            predictions["contact_window_end"].ge(predictions["contact_window_start"]),
            predictions["contact_window_start"],
        )
        predictions["contact_recommendation"] = self.build_contact_recommendation(predictions)
        return predictions

    def build_contact_recommendation(self, df: pd.DataFrame) -> pd.Series:
        recommendations: List[str] = []
        for _, row in df.iterrows():
            due_days = int(pd.to_numeric(pd.Series([row["days_until_expected_purchase"]]), errors="coerce").fillna(1).iloc[0])
            probability = float(pd.to_numeric(pd.Series([row["purchase_probability"]]), errors="coerce").fillna(0.0).iloc[0])
            band = str(row["priority_band"])
            start = pd.Timestamp(row["contact_window_start"]).date().isoformat()
            end = pd.Timestamp(row["contact_window_end"]).date().isoformat()
            expected = pd.Timestamp(row["expected_next_purchase_date"]).date().isoformat()
            if due_days <= 2:
                prefix = "Contact today or tomorrow"
            elif due_days <= 7:
                prefix = "Contact this week"
            else:
                prefix = "Plan outreach in the recommended window"
            recommendation = (
                f"{prefix}; expected purchase around {expected}; "
                f"contact window {start} to {end}; "
                f"priority {band}; probability {probability:.2f}."
            )
            recommendations.append(recommendation)
        return pd.Series(recommendations, index=df.index, dtype="string")

    def save_outputs(self, output_dir: Path, df: pd.DataFrame) -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        product_key = self._resolved_product_key(df)
        export_columns = [
            "customer_id",
            product_key,
            "capture_score",
            "priority_band",
            "client_product_embedding_score",
            "client_product_embedding_cosine",
            "client_product_preference_gap",
            "estimated_interval_days",
            "days_until_expected_purchase",
            "expected_next_purchase_date",
            "purchase_probability",
            "contact_window_start",
            "contact_window_end",
            "contact_recommendation",
        ]
        export_df = df.loc[:, [column for column in export_columns if column in df.columns]].copy()
        missing_output = [column for column in self._required_output_columns if column not in export_df.columns]
        if missing_output:
            raise ValueError(
                "Next purchase output is missing required columns: "
                + ", ".join(missing_output)
            )
        if export_df.loc[:, list(self._required_output_columns)].isna().any().any():
            missing_columns = export_df.columns[export_df.isna().any()].tolist()
            raise ValueError(
                "Next purchase output contains NaN values in columns: "
                + ", ".join(missing_columns)
            )
        output_path = output_dir / "next_purchase_predictions.parquet"
        _write_parquet(export_df, output_path)
        logger.info("Saved next purchase predictions to %s", output_path)
        return output_path

    def compute_metrics(
        self,
        predictions_df: pd.DataFrame,
        *,
        source_df: Optional[pd.DataFrame] = None,
        historical_proxy: Optional[dict] = None,
    ) -> dict:
        probabilities = pd.to_numeric(predictions_df["purchase_probability"], errors="coerce").fillna(0.0) if not predictions_df.empty else pd.Series(dtype=float)
        due_days = pd.to_numeric(predictions_df["days_until_expected_purchase"], errors="coerce").fillna(0.0) if not predictions_df.empty else pd.Series(dtype=float)
        metrics = {
            "source_rows": int(len(source_df)) if source_df is not None else int(len(predictions_df)),
            "prediction_rows": int(len(predictions_df)),
            "probability_distribution": {
                "min": float(probabilities.min()) if len(probabilities) else 0.0,
                "mean": float(probabilities.mean()) if len(probabilities) else 0.0,
                "median": float(probabilities.median()) if len(probabilities) else 0.0,
                "p90": float(probabilities.quantile(0.9)) if len(probabilities) else 0.0,
                "max": float(probabilities.max()) if len(probabilities) else 0.0,
            },
            "days_until_purchase_distribution": {
                "min": int(due_days.min()) if len(due_days) else 0,
                "mean": float(due_days.mean()) if len(due_days) else 0.0,
                "median": float(due_days.median()) if len(due_days) else 0.0,
                "p90": float(due_days.quantile(0.9)) if len(due_days) else 0.0,
                "max": int(due_days.max()) if len(due_days) else 0,
            },
            "priority_band_counts": {
                str(level): int(count)
                for level, count in predictions_df.get("priority_band", pd.Series(dtype="string")).astype("string").value_counts().sort_index().items()
            },
            "due_within_7d": int((due_days <= 7).sum()) if len(due_days) else 0,
            "due_within_14d": int((due_days <= 14).sum()) if len(due_days) else 0,
            "due_within_30d": int((due_days <= 30).sum()) if len(due_days) else 0,
        }
        if source_df is not None:
            metrics["actionable_capture_rows"] = int(len(source_df))
        if not predictions_df.empty:
            coherent_windows = (
                pd.to_datetime(predictions_df["contact_window_start"], errors="coerce")
                <= pd.to_datetime(predictions_df["contact_window_end"], errors="coerce")
            ) & (
                pd.to_datetime(predictions_df["contact_window_end"], errors="coerce")
                < pd.to_datetime(predictions_df["expected_next_purchase_date"], errors="coerce")
            )
            metrics["coherent_contact_windows_share"] = float(coherent_windows.mean())
        else:
            metrics["coherent_contact_windows_share"] = 1.0
        if historical_proxy is not None:
            metrics["historical_validation_proxy"] = historical_proxy
        return metrics

    def build_historical_proxy_validation(
        self,
        predictions_df: pd.DataFrame,
        sales_df: pd.DataFrame,
    ) -> dict:
        if predictions_df.empty or sales_df.empty:
            return {"rows": 0}
        sales = sales_df.copy()
        rename_map = {}
        if "client_id" in sales.columns and "customer_id" not in sales.columns:
            rename_map["client_id"] = "customer_id"
        if "date" in sales.columns and "sale_date" not in sales.columns:
            rename_map["date"] = "sale_date"
        sales = sales.rename(columns=rename_map)
        if {"customer_id", "product_id", "sale_date"} - set(sales.columns):
            return {"rows": 0}
        sales["customer_id"] = sales["customer_id"].astype("string")
        sales["product_id"] = sales["product_id"].astype("string")
        sales["sale_date"] = pd.to_datetime(sales["sale_date"], errors="coerce")
        interval_rows = []
        for (customer_id, product_id), group in sales.dropna(subset=["sale_date"]).sort_values("sale_date").groupby(["customer_id", "product_id"]):
            unique_dates = (
                pd.Series(group["sale_date"].dt.normalize().drop_duplicates().sort_values().unique())
            )
            if len(unique_dates) < 2:
                continue
            intervals = unique_dates.diff().dt.days.dropna()
            if intervals.empty:
                continue
            interval_rows.append(
                {
                    "customer_id": str(customer_id),
                    "product_id": str(product_id),
                    "empirical_median_interval_days": float(intervals.median()),
                    "empirical_mean_interval_days": float(intervals.mean()),
                    "n_intervals": int(len(intervals)),
                }
            )
        empirical_df = pd.DataFrame(interval_rows)
        if empirical_df.empty:
            return {"rows": 0}
        product_key = self._resolved_product_key(predictions_df)
        validation = predictions_df.merge(
            empirical_df,
            how="left",
            on=["customer_id", product_key],
            validate="one_to_one",
        )
        validation = validation.loc[validation["n_intervals"].fillna(0) >= 2].copy()
        if validation.empty:
            return {"rows": 0}
        estimated_interval = pd.to_numeric(validation["estimated_interval_days"], errors="coerce").fillna(0.0)
        empirical_interval = pd.to_numeric(validation["empirical_median_interval_days"], errors="coerce").fillna(0.0)
        interval_error = (estimated_interval - empirical_interval).abs()
        empirical_remaining_days = np.ceil(
            np.clip(
                empirical_interval - pd.to_numeric(validation["days_since_last_product_order"], errors="coerce").fillna(0.0),
                1.0,
                120.0,
            )
        )
        due_soon_label = pd.Series(empirical_remaining_days <= 7, index=validation.index)
        probability_metrics = self._ranking_metrics(
            validation["purchase_probability"],
            due_soon_label,
            pct_points=(0.10, 0.25, 0.50),
        )
        return {
            "rows": int(len(validation)),
            "interval_mae_days": float(interval_error.mean()),
            "interval_median_ae_days": float(interval_error.median()),
            "interval_within_7d": float((interval_error <= 7).mean()),
            "interval_within_14d": float((interval_error <= 14).mean()),
            "interval_within_30d": float((interval_error <= 30).mean()),
            "due_soon_7d_rate": float(due_soon_label.mean()),
            "probability_ranking": probability_metrics,
        }

    def _load_schema_contracts(self) -> Dict[str, List[str]]:
        schema_path = DemandLeakageDetector._schema_path()
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        try:
            workbook = pd.ExcelFile(schema_path)
        except ImportError as exc:
            raise ImportError(
                "Reading inibsa_feature_tables.xlsx requires 'openpyxl' to be installed"
            ) from exc
        contracts = {}
        for sheet_name in (self._client_sheet, self._client_product_sheet):
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
        required_columns = DemandLeakageDetector._normalize_expected_columns(schema_columns)
        required_columns.update(priority_columns)
        required_columns.update(identifier_columns)
        missing_columns = sorted(column for column in required_columns if column not in df.columns)
        if missing_columns:
            raise ValueError(
                f"{file_name} is missing required columns from Excel contract: "
                + ", ".join(missing_columns)
            )

    def _validate_capture_inputs(self, df: pd.DataFrame, file_name: str) -> None:
        required_columns = {
            "customer_id",
            self._resolved_product_key(df),
            "capture_score",
            "priority_band",
        }
        missing_columns = sorted(column for column in required_columns if column not in df.columns)
        if missing_columns:
            raise ValueError(
                f"{file_name} is missing required next-purchase capture columns: "
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

    def _canonicalize_capture_df(self, df: pd.DataFrame) -> pd.DataFrame:
        renamed = _normalize_frame_types(df)
        if "client_id" in renamed.columns and "customer_id" not in renamed.columns:
            renamed = renamed.rename(columns={"client_id": "customer_id"})
        if "family" in renamed.columns and "product_family" not in renamed.columns:
            renamed = renamed.rename(columns={"family": "product_family"})
        return renamed

    def _canonicalize_client_product_df(self, df: pd.DataFrame) -> pd.DataFrame:
        renamed = _normalize_frame_types(df)
        customer_column = DemandForecaster._find_first_column(renamed.columns, ("customer_id", "client_id"))
        if customer_column is None:
            raise ValueError("client_product_features must include client_id or customer_id")
        if "family" in renamed.columns and "product_family" not in renamed.columns:
            renamed = renamed.rename(columns={"family": "product_family"})
        return renamed.rename(columns={customer_column: "customer_id"})

    def _canonicalize_client_df(self, df: pd.DataFrame) -> pd.DataFrame:
        renamed = _normalize_frame_types(df)
        customer_column = DemandForecaster._find_first_column(renamed.columns, ("customer_id", "client_id"))
        if customer_column is None:
            raise ValueError("client features must include client_id or customer_id")
        return renamed.rename(columns={customer_column: "customer_id"})

    def _canonicalize_cluster_df(self, df: pd.DataFrame) -> pd.DataFrame:
        renamed = _normalize_frame_types(df)
        customer_column = DemandForecaster._find_first_column(renamed.columns, ("customer_id", "client_id"))
        if customer_column is None:
            raise ValueError("cluster_assignments.parquet must include client_id or customer_id")
        renamed = renamed.rename(columns={customer_column: "customer_id"})
        renamed["cluster_id"] = pd.to_numeric(renamed["cluster_id"], errors="coerce")
        return renamed

    def _resolved_product_key(self, df: pd.DataFrame) -> str:
        product_key = DemandForecaster._find_first_column(df.columns, ("product_id", "product_family", "family"))
        if product_key is None:
            raise ValueError("Next purchase inputs must include product_id or product_family/family")
        return product_key

    def _ranking_metrics(
        self,
        score: pd.Series | np.ndarray,
        label: pd.Series | np.ndarray,
        *,
        pct_points: Tuple[float, ...] = (0.10, 0.25, 0.50),
    ) -> dict:
        ranking = (
            pd.DataFrame(
                {
                    "score": pd.to_numeric(pd.Series(score), errors="coerce").fillna(0.0),
                    "label": pd.Series(label).astype(bool),
                }
            )
            .sort_values("score", ascending=False, kind="mergesort")
            .reset_index(drop=True)
        )
        base_rate = float(ranking["label"].mean())
        metrics = {"base_rate": base_rate}
        for pct in pct_points:
            top_k = max(int(len(ranking) * pct), 1)
            precision = float(ranking.iloc[:top_k]["label"].mean())
            label_key = f"{pct * 100:.1f}%"
            metrics[f"precision_at_{label_key}"] = precision
            metrics[f"lift_at_{label_key}"] = float(precision / base_rate) if base_rate > 0 else 0.0
        return metrics
