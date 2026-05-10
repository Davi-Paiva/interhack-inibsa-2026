from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import roc_auc_score

from backend.feature_engineering.config import FeatureConfig
from backend.feature_engineering.features import (
    build_client_features,
    build_client_product_features,
    build_embedding_bundle,
    build_product_features,
    load_feature_source_frame,
    prepare_all_product_feature_source_frame,
)

from .domain.loaders import load_campaigns, load_potential
from .domain.models import Campaign, Client, ClientProductFeatures, Potential, Product
from .services import DataAggregator, TechnicalProductEngine


TECHNICAL_BLOCK = "Productos Técnicos"
FORECAST_HORIZON_DAYS = 60
SNAPSHOT_STRIDE_MONTHS = 3
WARMUP_MONTHS = 12
MAX_SNAPSHOTS = 6


def _safe_float(value: Any) -> float:
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    try:
        return int(value) if value is not None else 0
    except (TypeError, ValueError):
        return 0


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    return normalized in {"true", "1", "yes"}


def _to_clients(frame: pd.DataFrame) -> list[Client]:
    rows: list[Client] = []
    for row in frame.to_dict(orient="records"):
        rows.append(
            Client(
                client_id=str(row["client_id"]),
                postal_code=str(row.get("postal_code", "") or ""),
                province=str(row.get("province", "") or ""),
                customer_total_revenue=_safe_float(row.get("customer_total_revenue")),
                customer_total_orders=_safe_int(row.get("customer_total_orders")),
                customer_avg_ticket=_safe_float(row.get("customer_avg_ticket")),
                customer_frequency=_safe_float(row.get("customer_frequency")),
                customer_frequency_log1p=_safe_float(row.get("customer_frequency_log1p")),
                days_since_last_order=_safe_int(row.get("days_since_last_order")),
                is_active_customer=_safe_bool(row.get("is_active_customer")),
                return_rate_30d=_safe_float(row.get("return_rate_30d")),
                campaign_lift=_safe_float(row.get("campaign_lift")),
                coefficient_variation_30d=_safe_float(row.get("coefficient_variation_30d")),
                client_embedding_0=_safe_float(row.get("client_embedding_0")),
                client_embedding_1=_safe_float(row.get("client_embedding_1")),
                client_embedding_2=_safe_float(row.get("client_embedding_2")),
                client_embedding_3=_safe_float(row.get("client_embedding_3")),
            )
        )
    return rows


def _to_products(frame: pd.DataFrame) -> list[Product]:
    rows: list[Product] = []
    for row in frame.to_dict(orient="records"):
        rows.append(
            Product(
                product_id=str(row["product_id"]),
                analytic_block=str(row.get("analytic_block", "") or ""),
                category=str(row.get("category", "") or ""),
                family=str(row.get("family", "") or ""),
                product_total_revenue=_safe_float(row.get("product_total_revenue")),
                product_total_units=_safe_int(row.get("product_total_units")),
                product_frequency=_safe_float(row.get("product_frequency")),
                rolling_sales_30d=_safe_float(row.get("rolling_sales_30d")),
                product_growth_30d=_safe_float(row.get("product_growth_30d")),
                product_return_rate=_safe_float(row.get("product_return_rate")),
                product_customer_count=_safe_int(row.get("product_customer_count")),
            )
        )
    return rows


def _to_client_product_features(frame: pd.DataFrame) -> list[ClientProductFeatures]:
    rows: list[ClientProductFeatures] = []
    for row in frame.to_dict(orient="records"):
        rows.append(
            ClientProductFeatures(
                client_id=str(row["client_id"]),
                product_id=str(row["product_id"]),
                rolling_sales_30d=_safe_float(row.get("rolling_sales_30d")),
                sales_growth_30d=_safe_float(row.get("sales_growth_30d")),
                days_since_last_product_order=_safe_int(row.get("days_since_last_product_order")),
                client_product_frequency=_safe_float(row.get("client_product_frequency")),
                client_product_avg_ticket=_safe_float(row.get("client_product_avg_ticket")),
                client_product_return_rate=_safe_float(row.get("client_product_return_rate")),
                campaign_lift_product=_safe_float(row.get("campaign_lift_product")),
                client_product_total_revenue=_safe_float(row.get("client_product_total_revenue")),
                client_product_total_orders=_safe_int(row.get("client_product_total_orders")),
                client_product_embedding_score=_safe_float(row.get("client_product_embedding_score")),
                client_product_embedding_cosine=_safe_float(row.get("client_product_embedding_cosine")),
                client_product_preference_gap=_safe_float(row.get("client_product_preference_gap")),
            )
        )
    return rows


def _load_static_entities(processed_dir: Path) -> tuple[list[Campaign], list[Potential]]:
    return (
        load_campaigns(processed_dir / "campaigns.csv"),
        load_potential(processed_dir / "potential.csv"),
    )


def _build_snapshot_dates(source_frame: pd.DataFrame) -> list[pd.Timestamp]:
    max_sale_date = pd.to_datetime(source_frame["sale_date"]).max().normalize()
    last_snapshot_date = max_sale_date - pd.Timedelta(days=FORECAST_HORIZON_DAYS)
    first_month_end = pd.to_datetime(source_frame["sale_date"]).min().to_period("M").to_timestamp(how="end").normalize()
    all_month_ends = pd.date_range(first_month_end, last_snapshot_date, freq="M")
    if len(all_month_ends) <= WARMUP_MONTHS:
        return []
    selected = [ts.normalize() for ts in all_month_ends[WARMUP_MONTHS - 1 :: SNAPSHOT_STRIDE_MONTHS]]
    return selected[-MAX_SNAPSHOTS:]


def _build_aggregator(
    *,
    clients: pd.DataFrame,
    products: pd.DataFrame,
    client_product_features: pd.DataFrame,
    campaigns: list[Campaign],
    potentials: list[Potential],
) -> DataAggregator:
    aggregator = DataAggregator(Path("."))
    aggregator.campaigns = campaigns
    aggregator.potentials = potentials
    aggregator.clients = _to_clients(clients)
    aggregator.products = _to_products(products)
    aggregator.client_product_features = _to_client_product_features(client_product_features)
    aggregator.sales_enriched = []
    return aggregator


def _future_target_frame(source_frame: pd.DataFrame, snapshot_date: pd.Timestamp) -> pd.DataFrame:
    horizon_end = snapshot_date + pd.Timedelta(days=FORECAST_HORIZON_DAYS)
    future_window = source_frame.loc[
        source_frame["sale_date"].gt(snapshot_date) & source_frame["sale_date"].le(horizon_end)
    ].copy()
    if future_window.empty:
        return pd.DataFrame(columns=["client_id", "product_id", "future_sales_60d"])
    return (
        future_window.groupby(["client_id", "product_id"], dropna=False)["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "future_sales_60d"})
    )


def _score_rows_to_frame(rows: list[Any], snapshot_date: pd.Timestamp) -> pd.DataFrame:
    frame = pd.DataFrame([asdict(row) for row in rows])
    frame["snapshot_date"] = pd.Timestamp(snapshot_date)
    return frame


def _ranking_metrics(score: pd.Series, label: pd.Series) -> dict[str, float]:
    ranking = (
        pd.DataFrame({"score": pd.to_numeric(score, errors="coerce").fillna(0.0), "label": label.astype(bool)})
        .sort_values("score", ascending=False, kind="mergesort")
        .reset_index(drop=True)
    )
    base_rate = float(ranking["label"].mean()) if not ranking.empty else 0.0
    metrics: dict[str, float] = {"base_rate": base_rate}
    for pct in (0.01, 0.05, 0.10):
        top_k = max(int(len(ranking) * pct), 1) if len(ranking) else 0
        precision = float(ranking.iloc[:top_k]["label"].mean()) if top_k else 0.0
        label_key = f"{int(pct * 100)}pct"
        metrics[f"precision_at_{label_key}"] = precision
        metrics[f"lift_at_{label_key}"] = float(precision / base_rate) if base_rate > 0 else 0.0
    return metrics


def _summarize_experiment(frame: pd.DataFrame) -> dict[str, Any]:
    label = frame["target_decline"].astype(bool)
    score = pd.to_numeric(frame["risk_score"], errors="coerce").fillna(0.0)
    summary = {
        "rows": int(len(frame)),
        "snapshots": int(frame["snapshot_date"].nunique()) if "snapshot_date" in frame.columns else 0,
        "positive_rate": float(label.mean()) if len(label) else 0.0,
        "score_distribution": {
            "mean": float(score.mean()) if len(score) else 0.0,
            "median": float(score.median()) if len(score) else 0.0,
            "p90": float(score.quantile(0.9)) if len(score) else 0.0,
            "max": float(score.max()) if len(score) else 0.0,
        },
        "ranking": _ranking_metrics(score, label),
    }
    if label.nunique() > 1:
        summary["roc_auc"] = float(roc_auc_score(label.astype(int), score))
    else:
        summary["roc_auc"] = 0.0
    return summary


def run_embedding_peer_experiment(
    *,
    project_root: Path,
) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    logging.getLogger("backend.technical_product_engine.services.data_aggregator").setLevel(logging.WARNING)
    logging.getLogger("backend.technical_product_engine.services.technical_engine_service").setLevel(logging.WARNING)
    processed_dir = project_root / "backend" / "processed_data" / "historical"
    config = FeatureConfig(processed_data_dir=project_root / "backend" / "processed_data")
    source_frame = load_feature_source_frame("historical", config)
    source_frame["sale_date"] = pd.to_datetime(source_frame["sale_date"], errors="coerce")
    source_frame = source_frame.dropna(subset=["sale_date"]).copy()
    campaigns, potentials = _load_static_entities(processed_dir)
    snapshot_dates = _build_snapshot_dates(source_frame)

    baseline_frames: list[pd.DataFrame] = []
    candidate_frames: list[pd.DataFrame] = []

    for snapshot_date in snapshot_dates:
        snapshot_source = source_frame.loc[source_frame["sale_date"].le(snapshot_date)].copy()
        snapshot_sales = prepare_all_product_feature_source_frame(snapshot_source)
        if snapshot_sales.empty:
            continue
        embedding_bundle = build_embedding_bundle(snapshot_sales)
        client_df = build_client_features(snapshot_sales, embedding_bundle=embedding_bundle)
        product_df = build_product_features(snapshot_sales, embedding_bundle=embedding_bundle)
        client_product_df = build_client_product_features(snapshot_sales, embedding_bundle=embedding_bundle)

        aggregator = _build_aggregator(
            clients=client_df,
            products=product_df,
            client_product_features=client_product_df,
            campaigns=campaigns,
            potentials=potentials,
        )
        contexts = aggregator.build_client_product_contexts(technical_only=True, analytic_block=TECHNICAL_BLOCK)
        if not contexts:
            continue

        peer_metrics_map = aggregator.compute_peer_metrics(contexts)
        baseline_peer_metrics = {
            key: value for key, value in peer_metrics_map.items() if not isinstance(key, tuple)
        }

        baseline_assessments = TechnicalProductEngine().analyze_batch(
            contexts,
            peer_metrics_map=baseline_peer_metrics,
        )
        candidate_assessments = TechnicalProductEngine().analyze_batch(
            contexts,
            peer_metrics_map=peer_metrics_map,
        )

        target_df = _future_target_frame(source_frame, snapshot_date)
        label_df = client_product_df.loc[:, ["client_id", "product_id", "rolling_sales_30d"]].merge(
            target_df,
            how="left",
            on=["client_id", "product_id"],
        )
        label_df["future_sales_60d"] = pd.to_numeric(label_df["future_sales_60d"], errors="coerce").fillna(0.0)
        label_df["rolling_sales_30d"] = pd.to_numeric(label_df["rolling_sales_30d"], errors="coerce").fillna(0.0)
        label_df["target_decline"] = (
            label_df["rolling_sales_30d"].gt(0.0)
            & label_df["future_sales_60d"].le(label_df["rolling_sales_30d"] * 0.5)
        )

        baseline_frame = _score_rows_to_frame(baseline_assessments, snapshot_date).merge(
            label_df.loc[:, ["client_id", "product_id", "target_decline"]],
            how="inner",
            on=["client_id", "product_id"],
        )
        candidate_frame = _score_rows_to_frame(candidate_assessments, snapshot_date).merge(
            label_df.loc[:, ["client_id", "product_id", "target_decline"]],
            how="inner",
            on=["client_id", "product_id"],
        )
        baseline_frames.append(baseline_frame)
        candidate_frames.append(candidate_frame)

    baseline_result = pd.concat(baseline_frames, ignore_index=True) if baseline_frames else pd.DataFrame()
    candidate_result = pd.concat(candidate_frames, ignore_index=True) if candidate_frames else pd.DataFrame()
    baseline_metrics = _summarize_experiment(baseline_result) if not baseline_result.empty else {"rows": 0}
    candidate_metrics = _summarize_experiment(candidate_result) if not candidate_result.empty else {"rows": 0}

    keep_candidate = (
        candidate_metrics.get("roc_auc", 0.0) > baseline_metrics.get("roc_auc", 0.0)
        and candidate_metrics.get("ranking", {}).get("precision_at_5pct", 0.0)
        >= baseline_metrics.get("ranking", {}).get("precision_at_5pct", 0.0)
    )
    return {
        "selected_variant": "embedding_weighted_peers" if keep_candidate else "product_average_peers",
        "keep_candidate": bool(keep_candidate),
        "snapshot_count": int(len(snapshot_dates)),
        "baseline": baseline_metrics,
        "embedding_candidate": candidate_metrics,
    }


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    result = run_embedding_peer_experiment(project_root=project_root)
    output_path = (
        project_root
        / "backend"
        / "technical_product_engine"
        / "output"
        / "historical"
        / "technical_embedding_experiment.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
