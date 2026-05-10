from __future__ import annotations

from .common import *
from .forecasting import DemandForecaster

class CaptureScoringEngine:
    """Scores and ranks capture opportunities."""

    _leakage_candidates: Tuple[str, ...] = ("demand_leakage_signals.parquet",)
    _backtest_candidates: Tuple[str, ...] = ("forecast_backtest_predictions.parquet",)
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
    _cluster_file_name = "cluster_assignments.parquet"
    _required_output_columns: Tuple[str, ...] = (
        "customer_id",
        "capture_score",
        "priority_rank",
        "priority_band",
        "recommended_action",
    )

    def __init__(self, weights: dict | None = None, priority_thresholds: dict | None = None):
        self.weights = weights or {
            "leakage": 0.40,
            "customer_value": 0.30,
            "urgency": 0.20,
            "confidence": 0.10,
        }
        self.priority_thresholds = priority_thresholds or {
            "critical": 40.0,
            "high": 32.0,
            "medium": 24.0,
        }
        self.product_key_column: Optional[str] = None

    def load_inputs(self, features_dir: Path, commodity_output_dir: Path) -> pd.DataFrame:
        """Load leakage outputs enriched with validated feature tables."""
        features_dir = Path(features_dir)
        commodity_output_dir = Path(commodity_output_dir)

        leakage_path = _resolve_existing_path(
            commodity_output_dir,
            self._leakage_candidates,
            "demand leakage output",
        )
        leakage_df = self._canonicalize_leakage_df(_read_frame(leakage_path))

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
        if cluster_path.exists():
            cluster_df = _read_frame(cluster_path)
        else:
            cluster_df = leakage_df.loc[:, ["customer_id", "cluster_id"]].drop_duplicates(subset=["customer_id"])

        forecaster = DemandForecaster()
        features_merged = forecaster.merge_feature_tables(
            _read_frame(client_product_path),
            _read_frame(product_path),
            _read_frame(client_path),
            cluster_df,
            source_names={
                "client_product": client_product_path.name,
                "product": product_path.name,
                "client": client_path.name,
            },
            require_target=False,
        )
        product_key = forecaster._resolved_product_key(features_merged)
        enriched = leakage_df.merge(
            features_merged,
            how="left",
            on=["customer_id", product_key],
            suffixes=("", "_feature"),
            validate="one_to_one",
        )
        if "cluster_id_feature" in enriched.columns:
            enriched["cluster_id"] = (
                pd.to_numeric(enriched["cluster_id"], errors="coerce")
                .fillna(pd.to_numeric(enriched["cluster_id_feature"], errors="coerce"))
            )
            enriched = enriched.drop(columns=["cluster_id_feature"])
        self.product_key_column = product_key
        enriched = _normalize_frame_types(enriched)
        self.validate_schema(enriched)
        return enriched

    def validate_schema(self, df: pd.DataFrame) -> None:
        if df.empty:
            raise ValueError("Capture scoring input DataFrame is empty")
        product_key = self._resolved_product_key(df)
        required_columns = {
            "customer_id",
            product_key,
            "leakage_score",
            "gap_units",
            "confidence_factor",
            "is_actionable",
            "route_to_engine",
            "customer_total_revenue",
            "customer_avg_ticket",
            "customer_frequency",
            "days_since_last_order",
            "sales_growth_30d",
        }
        missing_columns = sorted(column for column in required_columns if column not in df.columns)
        if missing_columns:
            raise ValueError(
                "Capture scoring frame is missing required columns: "
                + ", ".join(missing_columns)
            )

    def compute_value_component(self, df: pd.DataFrame) -> pd.Series:
        revenue = self._minmax_scale(df["customer_total_revenue"])
        avg_ticket = self._minmax_scale(df["customer_avg_ticket"])
        frequency = self._minmax_scale(df["customer_frequency"])
        return ((revenue + avg_ticket + frequency) / 3.0).clip(0.0, 1.0)

    def compute_urgency_component(self, df: pd.DataFrame) -> pd.Series:
        recency = self._minmax_scale(df["days_since_last_order"])
        negative_growth = np.maximum(pd.to_numeric(df["sales_growth_30d"], errors="coerce").fillna(0.0) * -1, 0.0)
        trend_decline = self._minmax_scale(negative_growth)
        gap_size = self._minmax_scale(df["gap_units"])
        return (0.4 * recency + 0.3 * trend_decline + 0.3 * gap_size).clip(0.0, 1.0)

    def compute_confidence_component(self, df: pd.DataFrame) -> pd.Series:
        return pd.to_numeric(df["confidence_factor"], errors="coerce").fillna(0.0).clip(0.0, 1.0)

    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        self.validate_schema(df)
        queue = df.loc[
            _normalize_boolean(df["is_actionable"])
            & df["route_to_engine"].astype("string").eq("commodity_ai_engine")
        ].copy()
        if queue.empty:
            product_key = self._resolved_product_key(df)
            empty_columns = [
                "customer_id",
                product_key,
                "capture_score_0_1",
                "capture_score",
                "priority_rank",
                "priority_band",
                "recommended_action",
            ]
            return pd.DataFrame(columns=empty_columns)

        queue["leakage_component"] = pd.to_numeric(queue["leakage_score"], errors="coerce").fillna(0.0).clip(0.0, 1.0)
        queue["value_component"] = self.compute_value_component(queue)
        queue["urgency_component"] = self.compute_urgency_component(queue)
        queue["confidence_component"] = self.compute_confidence_component(queue)
        queue["capture_score_0_1"] = (
            self.weights["leakage"] * queue["leakage_component"]
            + self.weights["customer_value"] * queue["value_component"]
            + self.weights["urgency"] * queue["urgency_component"]
            + self.weights["confidence"] * queue["confidence_component"]
        ).clip(0.0, 1.0)
        queue["capture_score"] = (queue["capture_score_0_1"] * 100.0).clip(0.0, 100.0)
        queue = queue.sort_values(
            ["capture_score", "leakage_score", "gap_units", "customer_total_revenue"],
            ascending=[False, False, False, False],
            kind="mergesort",
        ).reset_index(drop=True)
        queue["priority_rank"] = np.arange(1, len(queue) + 1, dtype=int)
        queue["priority_band"] = self._assign_priority_band(queue["capture_score"])
        queue["recommended_action"] = self.build_recommendations(queue)
        return queue

    def build_recommendations(self, df: pd.DataFrame) -> pd.Series:
        if df.empty:
            return pd.Series(dtype="string")
        actions: List[str] = []
        for _, row in df.iterrows():
            band = str(row["priority_band"])
            gap_units = float(pd.to_numeric(pd.Series([row["gap_units"]]), errors="coerce").fillna(0.0).iloc[0])
            decline = float(pd.to_numeric(pd.Series([row["sales_growth_30d"]]), errors="coerce").fillna(0.0).iloc[0])
            if band == "critical":
                action = "Call within 24h; prepare competitor recapture offer and validate next order window."
            elif band == "high":
                action = "Schedule follow-up within 3 days and review account-level volume drop."
            elif band == "medium":
                action = "Add to this week's priority queue and confirm replenishment timing."
            else:
                action = "Keep on watchlist and monitor next purchase signal."
            if decline < 0:
                action = action[:-1] + " Include recent negative sales trend in the sales brief."
            elif gap_units >= 200:
                action = action[:-1] + " Large current gap justifies direct outreach."
            actions.append(action)
        return pd.Series(actions, index=df.index, dtype="string")

    def save_outputs(self, output_dir: Path, df: pd.DataFrame) -> Path:
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
            "leakage_score",
            "gap_units",
            "customer_total_revenue",
            "customer_avg_ticket",
            "customer_frequency",
            "days_since_last_order",
            "sales_growth_30d",
            "leakage_component",
            "value_component",
            "urgency_component",
            "confidence_component",
            "capture_score_0_1",
            "capture_score",
            "priority_rank",
            "priority_band",
            "recommended_action",
        ]
        export_columns = [column for column in export_columns if column in df.columns]
        export_df = df.loc[:, export_columns].copy()
        missing_output = [column for column in self._required_output_columns if column not in export_df.columns]
        if missing_output:
            raise ValueError(
                "Capture opportunity output is missing required columns: "
                + ", ".join(missing_output)
            )
        if export_df.loc[:, list(self._required_output_columns)].isna().any().any():
            missing_columns = export_df.columns[export_df.isna().any()].tolist()
            raise ValueError(
                "Capture opportunity output contains NaN values in columns: "
                + ", ".join(missing_columns)
            )
        output_path = output_dir / "capture_opportunities.parquet"
        _write_parquet(export_df, output_path)
        logger.info("Saved capture opportunities to %s", output_path)
        return output_path

    def compute_metrics(
        self,
        scored_df: pd.DataFrame,
        *,
        source_df: Optional[pd.DataFrame] = None,
        historical_proxy: Optional[dict] = None,
    ) -> dict:
        scores = pd.to_numeric(scored_df["capture_score"], errors="coerce").fillna(0.0) if not scored_df.empty else pd.Series(dtype=float)
        metrics = {
            "source_rows": int(len(source_df)) if source_df is not None else int(len(scored_df)),
            "scored_rows": int(len(scored_df)),
            "score_distribution": {
                "min": float(scores.min()) if len(scores) else 0.0,
                "mean": float(scores.mean()) if len(scores) else 0.0,
                "median": float(scores.median()) if len(scores) else 0.0,
                "p90": float(scores.quantile(0.9)) if len(scores) else 0.0,
                "p99": float(scores.quantile(0.99)) if len(scores) else 0.0,
                "max": float(scores.max()) if len(scores) else 0.0,
            },
            "priority_band_counts": {
                str(level): int(count)
                for level, count in scored_df.get("priority_band", pd.Series(dtype="string")).astype("string").value_counts().sort_index().items()
            },
        }
        if source_df is not None:
            actionable_mask = (
                _normalize_boolean(source_df["is_actionable"])
                & source_df["route_to_engine"].astype("string").eq("commodity_ai_engine")
            )
            metrics["actionable_input_rows"] = int(actionable_mask.sum())
            metrics["actionable_input_share"] = float(actionable_mask.mean())
        if not scored_df.empty:
            top_5 = scored_df.head(5)
            top_10 = scored_df.head(10)
            total_gap = float(pd.to_numeric(scored_df["gap_units"], errors="coerce").fillna(0.0).sum()) + 1e-9
            total_revenue = float(pd.to_numeric(scored_df["customer_total_revenue"], errors="coerce").fillna(0.0).sum()) + 1e-9
            metrics["top_5_gap_share"] = float(pd.to_numeric(top_5["gap_units"], errors="coerce").fillna(0.0).sum() / total_gap)
            metrics["top_10_gap_share"] = float(pd.to_numeric(top_10["gap_units"], errors="coerce").fillna(0.0).sum() / total_gap)
            metrics["top_5_customer_revenue_share"] = float(pd.to_numeric(top_5["customer_total_revenue"], errors="coerce").fillna(0.0).sum() / total_revenue)
            metrics["top_10_customer_revenue_share"] = float(pd.to_numeric(top_10["customer_total_revenue"], errors="coerce").fillna(0.0).sum() / total_revenue)
            metrics["priority_rank_is_unique"] = bool(scored_df["priority_rank"].is_unique)
            metrics["priority_rank_is_monotonic"] = bool(scored_df["priority_rank"].is_monotonic_increasing)
        else:
            metrics["top_5_gap_share"] = 0.0
            metrics["top_10_gap_share"] = 0.0
            metrics["top_5_customer_revenue_share"] = 0.0
            metrics["top_10_customer_revenue_share"] = 0.0
            metrics["priority_rank_is_unique"] = True
            metrics["priority_rank_is_monotonic"] = True
        if historical_proxy is not None:
            metrics["historical_validation_proxy"] = historical_proxy
        return metrics

    def build_historical_proxy_validation(
        self,
        features_dir: Path,
        commodity_output_dir: Path,
    ) -> dict:
        """Fast proxy validation using the forecast backtest plus current feature snapshot."""
        features_dir = Path(features_dir)
        commodity_output_dir = Path(commodity_output_dir)
        backtest_path = _metrics_dir(commodity_output_dir) / self._backtest_candidates[0]
        if not backtest_path.exists():
            return {}

        backtest = _normalize_frame_types(_read_frame(backtest_path))
        source_df = self.load_inputs(features_dir, commodity_output_dir)
        product_key = self._resolved_product_key(source_df)
        feature_columns = [
            column
            for column in (
                "customer_id",
                product_key,
                "customer_total_revenue",
                "customer_avg_ticket",
                "customer_frequency",
                "days_since_last_order",
                "sales_growth_30d",
                "coefficient_variation_30d",
                "client_product_return_rate",
                "campaign_lift_product",
                "is_active_customer",
                "cluster_id",
            )
            if column in source_df.columns
        ]
        merged = backtest.merge(
            source_df.loc[:, feature_columns].drop_duplicates(subset=["customer_id", product_key]),
            how="left",
            on=["customer_id", product_key],
            validate="many_to_one",
        )
        merged["predicted_30d_sales"] = pd.to_numeric(merged["predicted_30d_sales"], errors="coerce").fillna(0.0)
        merged["observed_30d_sales"] = pd.to_numeric(merged["baseline_30d_sales"], errors="coerce").fillna(0.0)
        merged["gap_units"] = merged["predicted_30d_sales"] - merged["observed_30d_sales"]
        merged["gap_ratio"] = np.where(
            merged["predicted_30d_sales"] > 0,
            np.maximum(merged["gap_units"], 0.0) / merged["predicted_30d_sales"],
            0.0,
        )
        volatility = pd.to_numeric(merged["coefficient_variation_30d"], errors="coerce").fillna(0.0).clip(lower=0.0)
        merged["volatility_penalty"] = 1.0 / (1.0 + volatility)
        campaign = pd.to_numeric(merged["campaign_lift_product"], errors="coerce").fillna(0.0)
        merged["campaign_softener"] = 1.0 - (0.35 * np.clip(campaign, 0.0, 1.0))
        returns = pd.to_numeric(merged["client_product_return_rate"], errors="coerce").fillna(0.0)
        merged["return_penalty"] = 1.0 - (0.4 * np.clip(returns, 0.0, 0.5))
        merged["confidence_factor"] = np.clip(
            0.5 + pd.to_numeric(merged["forecast_confidence"], errors="coerce").fillna(0.0),
            0.0,
            1.0,
        )
        merged["leakage_score"] = np.clip(
            merged["gap_ratio"]
            * merged["volatility_penalty"]
            * merged["campaign_softener"]
            * merged["return_penalty"]
            * merged["confidence_factor"],
            0.0,
            1.0,
        )
        merged["is_actionable"] = (
            (pd.to_numeric(merged["gap_units"], errors="coerce").fillna(0.0) >= 25.0)
            & (pd.to_numeric(merged["gap_ratio"], errors="coerce").fillna(0.0) >= 0.25)
            & (pd.to_numeric(merged["leakage_score"], errors="coerce").fillna(0.0) >= 0.15)
            & _normalize_boolean(merged["is_active_customer"])
            & (pd.to_numeric(merged["days_since_last_order"], errors="coerce").fillna(np.inf) <= 180)
            & (pd.to_numeric(merged["observed_30d_sales"], errors="coerce").fillna(0.0) > 0.0)
        )
        merged["route_to_engine"] = np.where(
            merged["is_actionable"],
            "commodity_ai_engine",
            "none",
        )

        scored = self.score(merged)
        if scored.empty:
            return {"rows": 0}
        label = (
            (pd.to_numeric(scored["gap_units"], errors="coerce").fillna(0.0) >= 25.0)
            & (pd.to_numeric(scored["gap_ratio"], errors="coerce").fillna(0.0) >= 0.25)
            & (
                pd.to_numeric(scored["actual_30d_sales"], errors="coerce").fillna(0.0)
                <= pd.to_numeric(scored["baseline_30d_sales"], errors="coerce").fillna(0.0) * 1.05
            )
        )
        return {
            "rows": int(len(scored)),
            "missed_rebound_rate": float(label.mean()),
            "leakage_score_ranking": self._ranking_metrics(scored["leakage_score"], label),
            "capture_score_ranking": self._ranking_metrics(scored["capture_score"], label),
        }

    # Backward-compatible wrappers for the old experimental API.
    def compute_customer_value(
        self,
        customer_id: str,
        clients_df: pd.DataFrame,
        historical_spend: pd.Series,
    ) -> float:
        if "customer_total_revenue" not in clients_df.columns:
            return 0.0
        customer_row = clients_df.loc[clients_df["client_id"].astype("string").eq(str(customer_id))]
        if customer_row.empty:
            return 0.0
        score = self.compute_value_component(
            customer_row.rename(columns={"client_id": "customer_id"})
            .assign(customer_frequency=customer_row.get("customer_frequency", 0.0))
        )
        return float(score.iloc[0]) if not score.empty else 0.0

    def compute_urgency(self, leakage_df: pd.DataFrame) -> float:
        if leakage_df.empty:
            return 0.0
        if {"days_since_last_order", "sales_growth_30d", "gap_units"} - set(leakage_df.columns):
            gap = pd.to_numeric(leakage_df.get("predicted", 0), errors="coerce").fillna(0.0) - pd.to_numeric(
                leakage_df.get("observed", 0),
                errors="coerce",
            ).fillna(0.0)
            return float(np.clip(np.tanh(gap.abs().mean() / 100.0), 0.0, 1.0))
        return float(self.compute_urgency_component(leakage_df).mean())

    def score_opportunities(
        self,
        leakage_df: pd.DataFrame,
        customers_df: pd.DataFrame,
        historical_spend: pd.Series,
        forecaster: DemandForecaster,
    ) -> pd.DataFrame:
        legacy = leakage_df.copy()
        if "customer_id" not in legacy.columns:
            legacy["customer_id"] = legacy.index.astype("string")
        if "product_id" not in legacy.columns:
            legacy["product_id"] = "synthetic_product"
        if "confidence_factor" not in legacy.columns:
            legacy["confidence_factor"] = float(getattr(forecaster, "base_confidence_", 0.5))
        if "route_to_engine" not in legacy.columns:
            legacy["route_to_engine"] = "commodity_ai_engine"
        if "is_actionable" not in legacy.columns:
            legacy["is_actionable"] = True
        for column in (
            "customer_total_revenue",
            "customer_avg_ticket",
            "customer_frequency",
            "days_since_last_order",
            "sales_growth_30d",
            "gap_units",
        ):
            if column not in legacy.columns:
                legacy[column] = 0.0
        scored = self.score(legacy)
        return scored

    def generate_action_recommendations(self, scored_df: pd.DataFrame) -> Dict[str, str]:
        recommendations = self.build_recommendations(scored_df)
        return {idx: str(value) for idx, value in recommendations.items()}

    def _canonicalize_leakage_df(self, df: pd.DataFrame) -> pd.DataFrame:
        renamed = _normalize_frame_types(df)
        if "client_id" in renamed.columns and "customer_id" not in renamed.columns:
            renamed = renamed.rename(columns={"client_id": "customer_id"})
        if "family" in renamed.columns and "product_family" not in renamed.columns:
            renamed = renamed.rename(columns={"family": "product_family"})
        return renamed

    def _resolved_product_key(self, df: pd.DataFrame) -> str:
        product_key = DemandForecaster._find_first_column(df.columns, ("product_id", "product_family", "family"))
        if product_key is None:
            raise ValueError("Capture scoring inputs must include product_id or product_family/family")
        return product_key

    def _assign_priority_band(self, capture_score: pd.Series) -> pd.Series:
        numeric_score = pd.to_numeric(capture_score, errors="coerce").fillna(0.0)
        return pd.Series(
            np.select(
                [
                    numeric_score >= self.priority_thresholds["critical"],
                    numeric_score >= self.priority_thresholds["high"],
                    numeric_score >= self.priority_thresholds["medium"],
                ],
                ["critical", "high", "medium"],
                default="low",
            ),
            index=capture_score.index,
            dtype="string",
        )

    @staticmethod
    def _minmax_scale(series: pd.Series | np.ndarray) -> pd.Series:
        numeric = pd.to_numeric(pd.Series(series), errors="coerce").fillna(0.0).astype(float)
        if numeric.nunique() <= 1:
            return pd.Series(0.0, index=numeric.index, dtype=float)
        return (numeric - numeric.min()) / (numeric.max() - numeric.min())

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
        for pct in (0.01, 0.05, 0.10):
            top_k = max(int(len(ranking) * pct), 1)
            precision = float(ranking.iloc[:top_k]["label"].mean())
            label_key = f"{pct * 100:.1f}%"
            metrics[f"precision_at_{label_key}"] = precision
            metrics[f"lift_at_{label_key}"] = float(precision / base_rate) if base_rate > 0 else 0.0
        return metrics

