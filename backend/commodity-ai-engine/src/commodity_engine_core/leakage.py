from __future__ import annotations

from .common import *
from .forecasting import DemandForecaster

class DemandLeakageDetector:
    """Detects demand leakage (expected > observed) indicating potential competitor capture."""

    _client_sheet = "clients"
    _client_product_sheet = "client_product_features"
    _forecast_candidates: Tuple[str, ...] = ("consumption_forecast.parquet",)
    _backtest_candidates: Tuple[str, ...] = ("forecast_backtest_predictions.parquet",)
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
    _customer_id_candidates: Tuple[str, ...] = ("customer_id", "client_id")
    _product_id_candidates: Tuple[str, ...] = ("product_id", "product_family", "family")
    _priority_client_product_columns: Tuple[str, ...] = (
        "rolling_sales_30d",
        "campaign_lift_product",
        "client_product_return_rate",
    )
    _priority_client_columns: Tuple[str, ...] = (
        "coefficient_variation_30d",
        "is_active_customer",
        "days_since_last_order",
    )
    _required_output_columns: Tuple[str, ...] = (
        "customer_id",
        "predicted_30d_sales",
        "observed_30d_sales",
        "gap_units",
        "gap_ratio",
        "volatility_penalty",
        "campaign_softener",
        "return_penalty",
        "confidence_factor",
        "leakage_score",
        "risk_level",
        "is_actionable",
        "route_to_engine",
        "routing_reason",
    )

    def __init__(
        self,
        min_gap_units: float = 15.0,
        min_gap_ratio: float = 0.20,
        min_leakage_score: float = 0.10,
        max_days_since_last_order: int = 240,
    ):
        self.min_gap_units = float(min_gap_units)
        self.min_gap_ratio = float(min_gap_ratio)
        self.min_leakage_score = float(min_leakage_score)
        self.max_days_since_last_order = int(max_days_since_last_order)
        self.product_key_column: Optional[str] = None

    def load_inputs(self, features_dir: Path, commodity_output_dir: Path) -> pd.DataFrame:
        """Load and merge the latest leakage inputs from forecast and feature tables."""
        features_dir = Path(features_dir)
        commodity_output_dir = Path(commodity_output_dir)
        metrics_dir = _metrics_dir(commodity_output_dir)

        forecast_path = _resolve_existing_path(
            commodity_output_dir,
            self._forecast_candidates,
            "forecast output",
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

        forecast_df = self._canonicalize_forecast_df(_read_frame(forecast_path))
        client_product_df = self._canonicalize_client_product_df(_read_frame(client_product_path))
        client_df = self._canonicalize_client_df(_read_frame(client_path))

        cluster_path = commodity_output_dir / self._cluster_file_name
        cluster_df: Optional[pd.DataFrame] = None
        if cluster_path.exists():
            cluster_df = self._canonicalize_cluster_df(_read_frame(cluster_path))

        merged = self.merge_feature_tables(
            forecast_df,
            client_product_df,
            client_df,
            cluster_df=cluster_df,
            source_names={
                "forecast": forecast_path.name,
                "client_product": client_product_path.name,
                "client": client_path.name,
                "metrics": metrics_dir.name,
            },
        )
        return merged

    def merge_feature_tables(
        self,
        forecast_df: pd.DataFrame,
        client_product_df: pd.DataFrame,
        client_df: pd.DataFrame,
        *,
        cluster_df: Optional[pd.DataFrame] = None,
        source_names: Optional[Dict[str, str]] = None,
    ) -> pd.DataFrame:
        source_names = source_names or {
            "forecast": "consumption_forecast.parquet",
            "client_product": "client_product_features",
            "client": "clients",
        }
        schema_contracts = self._load_schema_contracts()

        self._validate_input_table(
            client_product_df,
            schema_contracts[self._client_product_sheet],
            source_names["client_product"],
            self._priority_client_product_columns,
            ("customer_id", self._resolved_product_key(client_product_df)),
        )
        self._validate_input_table(
            client_df,
            schema_contracts[self._client_sheet],
            source_names["client"],
            self._priority_client_columns,
            ("customer_id",),
        )
        self._validate_forecast_inputs(forecast_df, source_names["forecast"])
        if cluster_df is not None:
            self._validate_cluster_assignments(cluster_df)

        product_key = self._resolved_product_key(forecast_df)
        merged = forecast_df.merge(
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
            )
        self.product_key_column = product_key
        merged = _normalize_frame_types(merged)
        self.validate_schema(merged)
        return merged

    def validate_schema(self, df: pd.DataFrame) -> None:
        if df.empty:
            raise ValueError("Demand leakage input DataFrame is empty")
        required_columns = {
            "customer_id",
            "predicted_30d_sales",
            "rolling_sales_30d",
            "campaign_lift_product",
            "client_product_return_rate",
            "coefficient_variation_30d",
            "forecast_confidence",
            "is_active_customer",
            "days_since_last_order",
        }
        required_columns.add(self._resolved_product_key(df))
        missing_columns = sorted(column for column in required_columns if column not in df.columns)
        if missing_columns:
            raise ValueError(
                "Demand leakage frame is missing required columns: "
                + ", ".join(missing_columns)
            )

    def compute_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        self.validate_schema(df)
        scored = _normalize_frame_types(df).copy()

        predicted = pd.to_numeric(scored["predicted_30d_sales"], errors="coerce").fillna(0.0).clip(lower=0.0)
        observed = pd.to_numeric(scored["rolling_sales_30d"], errors="coerce").fillna(0.0).clip(lower=0.0)
        gap_units = predicted - observed
        positive_gap = gap_units.clip(lower=0.0)

        volatility = pd.to_numeric(scored["coefficient_variation_30d"], errors="coerce").fillna(0.0).clip(lower=0.0)
        campaign_lift = pd.to_numeric(scored["campaign_lift_product"], errors="coerce").fillna(0.0)
        return_rate = pd.to_numeric(scored["client_product_return_rate"], errors="coerce").fillna(0.0)
        forecast_confidence = pd.to_numeric(scored["forecast_confidence"], errors="coerce").fillna(0.0)

        gap_ratio = np.where(predicted > 0, positive_gap / predicted, 0.0)
        scored["observed_30d_sales"] = observed
        scored["gap_units"] = gap_units
        scored["gap_ratio"] = np.clip(gap_ratio, 0.0, 1.0)
        scored["volatility_penalty"] = 1.0 / (1.0 + volatility)
        scored["campaign_softener"] = 1.0 - (0.35 * np.clip(campaign_lift, 0.0, 1.0))
        scored["return_penalty"] = 1.0 - (0.4 * np.clip(return_rate, 0.0, 0.5))
        scored["confidence_factor"] = np.clip(0.5 + forecast_confidence, 0.0, 1.0)
        scored["leakage_score"] = np.clip(
            scored["gap_ratio"]
            * scored["volatility_penalty"]
            * scored["campaign_softener"]
            * scored["return_penalty"]
            * scored["confidence_factor"],
            0.0,
            1.0,
        )
        scored["risk_level"] = self.classify_risk(scored["leakage_score"])
        return scored

    def classify_risk(self, leakage_score: pd.Series) -> pd.Series:
        numeric_score = pd.to_numeric(leakage_score, errors="coerce").fillna(0.0)
        return pd.Series(
            np.select(
                [
                    numeric_score >= 0.30,
                    numeric_score >= 0.20,
                    numeric_score >= 0.15,
                ],
                ["high", "medium", "low"],
                default="none",
            ),
            index=leakage_score.index,
            dtype="string",
        )

    def filter_actionable(self, df: pd.DataFrame) -> pd.DataFrame:
        if "leakage_score" not in df.columns:
            raise ValueError("Demand leakage scores must be computed before filtering actionability")
        filtered = df.copy()
        filtered["is_active_customer"] = _normalize_boolean(filtered["is_active_customer"])
        filtered["days_since_last_order"] = pd.to_numeric(
            filtered["days_since_last_order"],
            errors="coerce",
        ).fillna(np.inf)
        filtered["observed_30d_sales"] = pd.to_numeric(
            filtered["observed_30d_sales"],
            errors="coerce",
        ).fillna(0.0)

        threshold_mask = (
            (pd.to_numeric(filtered["gap_units"], errors="coerce").fillna(0.0) >= self.min_gap_units)
            & (pd.to_numeric(filtered["gap_ratio"], errors="coerce").fillna(0.0) >= self.min_gap_ratio)
            & (pd.to_numeric(filtered["leakage_score"], errors="coerce").fillna(0.0) >= self.min_leakage_score)
        )
        active_mask = filtered["is_active_customer"]
        recency_mask = filtered["days_since_last_order"] <= self.max_days_since_last_order
        baseline_mask = filtered["observed_30d_sales"] > 0

        route_to_technical = threshold_mask & ~(active_mask & recency_mask & baseline_mask)
        actionable_mask = threshold_mask & active_mask & recency_mask & baseline_mask

        filtered["is_actionable"] = actionable_mask.astype(bool)
        filtered["route_to_engine"] = np.where(
            actionable_mask,
            "commodity_ai_engine",
            np.where(route_to_technical, "technical_product_engine", "none"),
        )
        filtered["routing_reason"] = self._build_routing_reason(
            threshold_mask=threshold_mask,
            active_mask=active_mask,
            recency_mask=recency_mask,
            baseline_mask=baseline_mask,
            index=filtered.index,
        )
        return filtered

    def save_outputs(self, output_dir: Path, df: pd.DataFrame) -> Path:
        self.validate_schema(df)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        product_key = self._resolved_product_key(df)
        export_columns = [
            "customer_id",
            product_key,
            "cluster_id",
            "client_product_embedding_score",
            "client_product_embedding_cosine",
            "client_product_preference_gap",
            "predicted_30d_sales",
            "observed_30d_sales",
            "gap_units",
            "gap_ratio",
            "volatility_penalty",
            "campaign_softener",
            "return_penalty",
            "confidence_factor",
            "leakage_score",
            "risk_level",
            "is_actionable",
            "route_to_engine",
            "routing_reason",
        ]
        export_columns = [column for column in export_columns if column in df.columns]
        export_df = df.loc[:, export_columns].copy()
        missing_output = [column for column in self._required_output_columns if column not in export_df.columns]
        if missing_output:
            raise ValueError(
                "Demand leakage output is missing required columns: "
                + ", ".join(missing_output)
            )
        if export_df.loc[:, list(self._required_output_columns)].isna().any().any():
            missing_columns = export_df.columns[export_df.isna().any()].tolist()
            raise ValueError(
                "Demand leakage output contains NaN values in columns: "
                + ", ".join(missing_columns)
            )
        output_path = output_dir / "demand_leakage_signals.parquet"
        _write_parquet(export_df, output_path)
        logger.info("Saved demand leakage signals to %s", output_path)
        return output_path

    def compute_metrics(self, df: pd.DataFrame) -> dict:
        if df.empty:
            return {
                "rows": 0,
                "candidate_count": 0,
                "candidate_share": 0.0,
                "actionable_count": 0,
                "actionable_share": 0.0,
                "routed_to_technical_count": 0,
                "routed_to_technical_share": 0.0,
                "score_distribution": {},
                "risk_bucket_counts": {},
                "cluster_mix": {},
            }
        scores = pd.to_numeric(df["leakage_score"], errors="coerce").fillna(0.0)
        candidate_mask = (
            (pd.to_numeric(df["gap_units"], errors="coerce").fillna(0.0) >= self.min_gap_units)
            & (pd.to_numeric(df["gap_ratio"], errors="coerce").fillna(0.0) >= self.min_gap_ratio)
            & (scores >= self.min_leakage_score)
        )
        actionable_mask = df["is_actionable"].astype(bool)
        technical_mask = df["route_to_engine"].astype("string").eq("technical_product_engine")
        cluster_mix = {}
        if "cluster_id" in df.columns:
            cluster_mix = {
                str(int(cluster_id)): int(count)
                for cluster_id, count in (
                    pd.to_numeric(df.loc[actionable_mask, "cluster_id"], errors="coerce")
                    .dropna()
                    .astype(int)
                    .value_counts()
                    .sort_index()
                    .items()
                )
            }
        return {
            "rows": int(len(df)),
            "candidate_count": int(candidate_mask.sum()),
            "candidate_share": float(candidate_mask.mean()),
            "actionable_count": int(actionable_mask.sum()),
            "actionable_share": float(actionable_mask.mean()),
            "routed_to_technical_count": int(technical_mask.sum()),
            "routed_to_technical_share": float(technical_mask.mean()),
            "score_distribution": {
                "min": float(scores.min()),
                "mean": float(scores.mean()),
                "median": float(scores.median()),
                "p90": float(scores.quantile(0.9)),
                "p99": float(scores.quantile(0.99)),
                "max": float(scores.max()),
            },
            "risk_bucket_counts": {
                str(level): int(count)
                for level, count in df["risk_level"].astype("string").value_counts().sort_index().items()
            },
            "cluster_mix": cluster_mix,
        }

    def build_historical_evaluation_frame(
        self,
        panel: pd.DataFrame,
        backtest_predictions: pd.DataFrame,
    ) -> pd.DataFrame:
        if panel.empty:
            raise ValueError("Historical leakage evaluation requires a non-empty training panel")
        if backtest_predictions.empty:
            raise ValueError("Historical leakage evaluation requires non-empty backtest predictions")
        enriched_panel = _normalize_frame_types(panel).copy()
        enriched_panel["snapshot_date"] = pd.to_datetime(enriched_panel["snapshot_date"], errors="coerce")

        backtest = _normalize_frame_types(backtest_predictions).copy()
        backtest["snapshot_date"] = pd.to_datetime(backtest["snapshot_date"], errors="coerce")
        backtest["rolling_sales_30d"] = pd.to_numeric(
            backtest["baseline_30d_sales"],
            errors="coerce",
        ).fillna(0.0)

        join_columns = [
            "snapshot_date",
            "customer_id",
            self._resolved_product_key(backtest),
        ]
        panel_columns = [
            column
            for column in (
                *join_columns,
                "campaign_lift_product",
                "client_product_return_rate",
                "coefficient_variation_30d",
                "is_active_customer",
                "days_since_last_order",
                "cluster_id",
            )
            if column in enriched_panel.columns
        ]
        merged = backtest.merge(
            enriched_panel.loc[:, panel_columns].drop_duplicates(subset=join_columns),
            how="left",
            on=join_columns,
            suffixes=("", "_panel"),
            validate="many_to_one",
        )
        if "cluster_id_panel" in merged.columns and "cluster_id" in merged.columns:
            merged["cluster_id"] = (
                pd.to_numeric(merged["cluster_id"], errors="coerce")
                .fillna(pd.to_numeric(merged["cluster_id_panel"], errors="coerce"))
            )
            merged = merged.drop(columns=["cluster_id_panel"])
        self.product_key_column = self._resolved_product_key(merged)
        self.validate_schema(merged)
        scored = self.compute_scores(merged)
        scored = self.filter_actionable(scored)
        return scored

    def compute_historical_metrics(self, historical_df: pd.DataFrame) -> dict:
        metrics = self.compute_metrics(historical_df)
        if historical_df.empty:
            metrics["offline_validation"] = {}
            return metrics

        scored = historical_df.copy()
        predicted = pd.to_numeric(scored["predicted_30d_sales"], errors="coerce").fillna(0.0)
        baseline = pd.to_numeric(scored["baseline_30d_sales"], errors="coerce").fillna(0.0)
        actual = pd.to_numeric(scored["actual_30d_sales"], errors="coerce").fillna(0.0)
        volatility = pd.to_numeric(scored["coefficient_variation_30d"], errors="coerce").fillna(1.0)
        confidence = pd.to_numeric(scored["forecast_confidence"], errors="coerce").fillna(0.0)

        legacy_score = (
            np.maximum(pd.to_numeric(scored["gap_ratio"], errors="coerce").fillna(0.0), 0.0)
            * volatility.clip(lower=0.0)
            * confidence
        ).clip(0.0, 1.0)
        missed_rebound = (
            (pd.to_numeric(scored["gap_units"], errors="coerce").fillna(0.0) >= self.min_gap_units)
            & (pd.to_numeric(scored["gap_ratio"], errors="coerce").fillna(0.0) >= self.min_gap_ratio)
            & (actual <= (baseline * 1.05))
        )

        metrics["offline_validation"] = {
            "rows": int(len(scored)),
            "missed_rebound_rate": float(missed_rebound.mean()),
            "current_score": self._ranking_metrics(legacy_score, missed_rebound),
            "proposed_score": self._ranking_metrics(
                pd.to_numeric(scored["leakage_score"], errors="coerce").fillna(0.0),
                missed_rebound,
            ),
        }
        return metrics

    # Backward-compatible wrapper for earlier notebooks/tests using series-only scoring.
    def compute_leakage(
        self,
        predicted_consumption: pd.Series,
        observed_consumption: pd.Series,
        customer_volatility: pd.Series,
        model_confidence: float = 0.85,
    ) -> pd.DataFrame:
        frame = pd.DataFrame(
            {
                "customer_id": pd.Series(range(len(predicted_consumption)), dtype="string"),
                "product_id": "synthetic_product",
                "predicted_30d_sales": predicted_consumption,
                "rolling_sales_30d": observed_consumption,
                "coefficient_variation_30d": customer_volatility,
                "campaign_lift_product": 0.0,
                "client_product_return_rate": 0.0,
                "forecast_confidence": model_confidence,
                "is_active_customer": True,
                "days_since_last_order": 0,
            }
        )
        scored = self.compute_scores(frame)
        return scored.rename(
            columns={
                "predicted_30d_sales": "predicted",
                "observed_30d_sales": "observed",
            }
        )[["predicted", "observed", "gap_units", "gap_ratio", "leakage_score"]]

    def filter_significant_leakage(
        self,
        leakage_df: pd.DataFrame,
        min_gap_units: int = 10,
    ) -> pd.DataFrame:
        scored = leakage_df.copy()
        predicted_column = "predicted_30d_sales" if "predicted_30d_sales" in scored.columns else "predicted"
        observed_column = "observed_30d_sales" if "observed_30d_sales" in scored.columns else "observed"
        if "gap_units" not in scored.columns:
            scored["gap_units"] = (
                pd.to_numeric(scored[predicted_column], errors="coerce").fillna(0.0)
                - pd.to_numeric(scored[observed_column], errors="coerce").fillna(0.0)
            )
        return scored[
            (pd.to_numeric(scored["leakage_score"], errors="coerce").fillna(0.0) >= self.min_leakage_score)
            & (pd.to_numeric(scored["gap_units"], errors="coerce").fillna(0.0) >= float(min_gap_units))
        ]

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
        required_columns = self._normalize_expected_columns(schema_columns)
        required_columns.update(priority_columns)
        required_columns.update(identifier_columns)
        missing_columns = sorted(column for column in required_columns if column not in df.columns)
        if missing_columns:
            raise ValueError(
                f"{file_name} is missing required columns from Excel contract: "
                + ", ".join(missing_columns)
            )

    def _validate_forecast_inputs(self, df: pd.DataFrame, file_name: str) -> None:
        if df.empty:
            raise ValueError(f"{file_name} is empty")
        required_columns = {
            "customer_id",
            self._resolved_product_key(df),
            "predicted_30d_sales",
            "forecast_confidence",
        }
        missing_columns = sorted(column for column in required_columns if column not in df.columns)
        if missing_columns:
            raise ValueError(
                f"{file_name} is missing required leakage forecast columns: "
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

    def _canonicalize_forecast_df(self, df: pd.DataFrame) -> pd.DataFrame:
        renamed = _normalize_frame_types(df)
        customer_column = self._find_first_column(renamed.columns, self._customer_id_candidates)
        if customer_column is None:
            raise ValueError("consumption_forecast must include client_id or customer_id")
        return renamed.rename(columns={customer_column: "customer_id"})

    def _canonicalize_client_product_df(self, df: pd.DataFrame) -> pd.DataFrame:
        renamed = _normalize_frame_types(df)
        customer_column = self._find_first_column(renamed.columns, self._customer_id_candidates)
        if customer_column is None:
            raise ValueError("client_product_features must include client_id or customer_id")
        if "family" in renamed.columns and "product_family" not in renamed.columns:
            renamed = renamed.rename(columns={"family": "product_family"})
        return renamed.rename(columns={customer_column: "customer_id"})

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
            raise ValueError("Demand leakage inputs must include product_id or product_family/family")
        return product_key

    def _build_routing_reason(
        self,
        *,
        threshold_mask: pd.Series,
        active_mask: pd.Series,
        recency_mask: pd.Series,
        baseline_mask: pd.Series,
        index: pd.Index,
    ) -> pd.Series:
        reasons: List[str] = []
        for idx, meets_threshold in threshold_mask.items():
            if not meets_threshold:
                reasons.append("below_threshold")
                continue
            row_reasons = []
            if not bool(active_mask.loc[idx]):
                row_reasons.append("inactive_customer")
            if not bool(recency_mask.loc[idx]):
                row_reasons.append("stale_customer")
            if not bool(baseline_mask.loc[idx]):
                row_reasons.append("zero_baseline")
            reasons.append("commodity_actionable" if not row_reasons else "|".join(row_reasons))
        return pd.Series(reasons, index=index, dtype="string")

    def _ranking_metrics(self, score: pd.Series | np.ndarray, label: pd.Series | np.ndarray) -> dict:
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
        for pct in (0.001, 0.01, 0.05):
            top_k = max(int(len(ranking) * pct), 1)
            precision = float(ranking.iloc[:top_k]["label"].mean())
            label_key = f"{pct * 100:.1f}%".replace(".", "_")
            metrics[f"precision_at_{label_key}"] = precision
            metrics[f"lift_at_{label_key}"] = float(precision / base_rate) if base_rate > 0 else 0.0
        return metrics

