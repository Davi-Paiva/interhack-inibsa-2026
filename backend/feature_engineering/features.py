from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .config import FeatureConfig, RunMode
    from .embeddings import (
        CLIENT_EMBEDDING_COLUMNS,
        CLIENT_PRODUCT_EMBEDDING_COLUMNS,
        EMBEDDING_FEATURE_PREFIXES,
        PRODUCT_EMBEDDING_COLUMNS,
        EmbeddingFeatureBundle,
        build_embedding_feature_bundle,
    )
    from .utils import ensure_directory, read_csv_frame, write_csv_frame, write_json
except (ImportError, ValueError):
    from config import FeatureConfig, RunMode
    from embeddings import (
        CLIENT_EMBEDDING_COLUMNS,
        CLIENT_PRODUCT_EMBEDDING_COLUMNS,
        EMBEDDING_FEATURE_PREFIXES,
        PRODUCT_EMBEDDING_COLUMNS,
        EmbeddingFeatureBundle,
        build_embedding_feature_bundle,
    )
    from utils import ensure_directory, read_csv_frame, write_csv_frame, write_json


logger = logging.getLogger(__name__)

COMMODITY_BLOCK_NAME = "Commodities"
SOURCE_DATASET_CANDIDATES = ("sales_enriched.csv",)
SOURCE_COLUMN_ALIASES = {
    "invoice_id": "invoice_number",
    "date": "sale_date",
    "sales_value": "amount",
}
CLIENT_REFERENCE_COLUMNS = {
    "Id. Cliente": "client_id",
    "Codigo Postal": "postal_code",
    "Provincia": "province",
}
PRODUCT_REFERENCE_COLUMNS = {
    "Id.Prod": "product_id",
    "Bloque analítico": "analytic_block",
    "Categoria": "category",
    "Familia": "family",
}
REQUIRED_COLUMNS = {
    "invoice_number",
    "sale_date",
    "client_id",
    "product_id",
    "amount",
    "units",
    "is_campaign_period",
    "is_return",
}

DEFAULT_PERCENTILE_RANGE = (0.01, 0.99)
COEFFICIENT_VARIATION_CLIP_RANGE = (-5.0, 5.0)
CAMPAIGN_LIFT_CLIP_RANGE = (-5.0, 5.0)
GROWTH_CLIP_RANGE = (-5.0, 5.0)
ACTIVE_CUSTOMER_THRESHOLD_DAYS = 180
FREQUENCY_MONTH_DAYS = 30.0

CLIENT_FEATURE_COLUMNS = [
    "client_id",
    "postal_code",
    "province",
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
    *CLIENT_EMBEDDING_COLUMNS,
]
PRODUCT_FEATURE_COLUMNS = [
    "product_id",
    "analytic_block",
    "category",
    "family",
    "product_total_revenue",
    "product_total_units",
    "product_frequency",
    "rolling_sales_30d",
    "product_growth_30d",
    "product_return_rate",
    "product_customer_count",
    *PRODUCT_EMBEDDING_COLUMNS,
]
CLIENT_PRODUCT_FEATURE_COLUMNS = [
    "client_id",
    "product_id",
    "rolling_sales_30d",
    "sales_growth_30d",
    "days_since_last_product_order",
    "client_product_frequency",
    "client_product_avg_ticket",
    "client_product_return_rate",
    "campaign_lift_product",
    "client_product_total_revenue",
    "client_product_total_orders",
    *CLIENT_PRODUCT_EMBEDDING_COLUMNS,
]
FEATURE_TABLE_SCHEMAS = {
    "client_features": CLIENT_FEATURE_COLUMNS,
    "product_features": PRODUCT_FEATURE_COLUMNS,
    "client_product_features": CLIENT_PRODUCT_FEATURE_COLUMNS,
}
FEATURE_OUTPUT_FILES = {
    "client_features": "clients.csv",
    "product_features": "products.csv",
    "client_product_features": "client_product_features.csv",
}
FEATURE_PRIMARY_KEYS = {
    "client_features": ["client_id"],
    "product_features": ["product_id"],
    "client_product_features": ["client_id", "product_id"],
}
DAILY_DELTA_OUTPUT_FILES = {
    "client_features": "changed_clients.csv",
    "product_features": "changed_products.csv",
    "client_product_features": "changed_client_product_features.csv",
}
FEATURE_STATE_OUTPUT_FILES = {
    "client_features": "clients.json",
    "product_features": "products.json",
    "client_product_features": "client_product_features.json",
}
DAILY_DELTA_MANIFEST_FILE = "daily_feature_delta.json"
FEATURE_STATE_MANIFEST_FILE = "feature_state_manifest.json"


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    numeric_numerator = pd.to_numeric(numerator, errors="coerce")
    numeric_denominator = pd.to_numeric(denominator, errors="coerce").replace(0, np.nan)
    return numeric_numerator.div(numeric_denominator).replace([np.inf, -np.inf], np.nan).fillna(0.0)


def _coerce_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)


def filter_nan_values(series: pd.Series) -> pd.Series:
    return series.loc[series.notna()]


def filter_inf_values(series: pd.Series) -> pd.Series:
    return series.replace([np.inf, -np.inf], np.nan).dropna()


def clip_feature_values(series: pd.Series, clip_range: tuple[float, float] | None = None) -> pd.Series:
    if clip_range is None:
        return series
    return series.clip(lower=clip_range[0], upper=clip_range[1])


def filter_feature_percentiles(
    series: pd.Series,
    percentile_range: tuple[float, float] | None = None,
) -> pd.Series:
    if percentile_range is None or series.empty:
        return series
    lower_bound = series.quantile(percentile_range[0])
    upper_bound = series.quantile(percentile_range[1])
    return series.clip(lower=lower_bound, upper=upper_bound)


def clean_feature_for_plot(
    series: pd.Series,
    *,
    percentile_range: tuple[float, float] | None = DEFAULT_PERCENTILE_RANGE,
    clip_range: tuple[float, float] | None = None,
    log1p_transform: bool = False,
) -> pd.Series:
    cleaned = _coerce_numeric(series).dropna()
    cleaned = filter_feature_percentiles(cleaned, percentile_range)
    cleaned = clip_feature_values(cleaned, clip_range)
    if log1p_transform:
        cleaned = np.log1p(cleaned.clip(lower=0.0))
    return cleaned


def stabilize_feature_values(
    series: pd.Series,
    *,
    percentile_range: tuple[float, float] | None = DEFAULT_PERCENTILE_RANGE,
    clip_range: tuple[float, float] | None = None,
    lower_bound: float | None = None,
    upper_bound: float | None = None,
) -> pd.Series:
    numeric = _coerce_numeric(series)
    cleaned = numeric.dropna()
    if cleaned.empty:
        return numeric.fillna(0.0)

    cleaned = filter_feature_percentiles(cleaned, percentile_range)
    cleaned = clip_feature_values(cleaned, clip_range)
    if lower_bound is not None:
        cleaned = cleaned.clip(lower=lower_bound)
    if upper_bound is not None:
        cleaned = cleaned.clip(upper=upper_bound)

    stabilized = numeric.copy()
    stabilized.loc[cleaned.index] = cleaned
    return stabilized.fillna(0.0)


def _resolve_source_path(mode: RunMode, config: FeatureConfig) -> Path:
    input_dir = config.input_dir_for_mode(mode)
    candidates = []
    for name in (*SOURCE_DATASET_CANDIDATES, config.source_dataset_name):
        if name not in candidates:
            candidates.append(name)
    for name in candidates:
        path = input_dir / name
        if path.exists():
            return path
    raise FileNotFoundError(f"No cleaned CSV source found in {input_dir}. Expected one of: {', '.join(candidates)}")


def resolve_feature_source_path(mode: RunMode, config: FeatureConfig) -> Path:
    return _resolve_source_path(mode, config)


def _normalize_source_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        source_name: target_name
        for source_name, target_name in SOURCE_COLUMN_ALIASES.items()
        if source_name in df.columns and target_name not in df.columns
    }
    normalized = df.rename(columns=rename_map).copy() if rename_map else df.copy()
    for column in ("invoice_number", "client_id", "product_id"):
        if column in normalized.columns:
            normalized[column] = normalized[column].astype("string").str.strip()
    return normalized


def _merge_reference_context(df: pd.DataFrame, *, mode: RunMode, config: FeatureConfig) -> pd.DataFrame:
    enriched = df.copy()
    if {"postal_code", "province"} - set(enriched.columns):
        clients_path = config.raw_data_dir / "clients.csv"
        if clients_path.exists():
            clients = (
                read_csv_frame(clients_path)
                .rename(columns=CLIENT_REFERENCE_COLUMNS)[["client_id", "postal_code", "province"]]
                .assign(client_id=lambda frame: frame["client_id"].astype("string").str.strip())
                .drop_duplicates(subset=["client_id"], keep="last")
            )
            enriched = enriched.merge(clients, on="client_id", how="left")

    if {"analytic_block", "category", "family"} - set(enriched.columns):
        products_path = config.raw_data_dir / "products.csv"
        if products_path.exists():
            products = (
                read_csv_frame(products_path)
                .rename(columns=PRODUCT_REFERENCE_COLUMNS)[
                    ["product_id", "analytic_block", "category", "family"]
                ]
                .assign(product_id=lambda frame: frame["product_id"].astype("string").str.strip())
                .drop_duplicates(subset=["product_id"], keep="last")
            )
            enriched = enriched.merge(products, on="product_id", how="left")

    return enriched


def _load_product_catalog(config: FeatureConfig) -> pd.DataFrame:
    products_path = config.raw_data_dir / "products.csv"
    products = (
        read_csv_frame(products_path)
        .rename(columns=PRODUCT_REFERENCE_COLUMNS)[["product_id", "analytic_block", "category", "family"]]
        .assign(product_id=lambda frame: frame["product_id"].astype("string").str.strip())
        .drop_duplicates(subset=["product_id"], keep="last")
        .reset_index(drop=True)
    )
    return products


def _validate_source_frame(df: pd.DataFrame) -> None:
    missing_columns = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing_columns:
        raise ValueError(f"Feature source CSV is missing required columns: {', '.join(missing_columns)}")


def load_feature_source_frame(mode: RunMode, config: FeatureConfig) -> pd.DataFrame:
    source_path = _resolve_source_path(mode, config)
    logger.info("Loading feature source from %s", source_path)
    frame = read_csv_frame(source_path)
    frame = _normalize_source_columns(frame)
    frame = _merge_reference_context(frame, mode=mode, config=config)
    _validate_source_frame(frame)
    return frame


def _prepare_sales_frame(sales: pd.DataFrame, *, commodity_only: bool = True) -> pd.DataFrame:
    prepared = sales.copy()
    if commodity_only and "analytic_block" in prepared.columns:
        prepared = prepared.loc[prepared["analytic_block"].fillna("").eq(COMMODITY_BLOCK_NAME)].copy()
    prepared["sale_date"] = pd.to_datetime(prepared["sale_date"], errors="coerce")
    for column in ("invoice_number", "client_id", "product_id"):
        prepared[column] = prepared[column].astype("string").str.strip()
    prepared["amount"] = pd.to_numeric(prepared["amount"], errors="coerce")
    prepared["units"] = pd.to_numeric(prepared["units"], errors="coerce")
    prepared["is_campaign_period"] = prepared["is_campaign_period"].fillna(False).astype(bool)
    prepared["is_return"] = prepared["is_return"].fillna(False).astype(bool)
    prepared = prepared.dropna(subset=["invoice_number", "client_id", "product_id", "sale_date", "amount", "units"])
    return prepared.sort_values(["sale_date", "invoice_number", "client_id", "product_id"]).reset_index(drop=True)


def prepare_feature_source_frame(source_frame: pd.DataFrame) -> pd.DataFrame:
    return _prepare_sales_frame(source_frame, commodity_only=True)


def prepare_all_product_feature_source_frame(source_frame: pd.DataFrame) -> pd.DataFrame:
    return _prepare_sales_frame(source_frame, commodity_only=False)


def build_embedding_bundle(sales: pd.DataFrame) -> EmbeddingFeatureBundle:
    return build_embedding_feature_bundle(sales)


def _build_order_frame(sales: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    aggregations: dict[str, tuple[str, str]] = {
        "sale_date": ("sale_date", "max"),
        "order_revenue": ("amount", "sum"),
        "order_units": ("units", "sum"),
        "is_return": ("is_return", "max"),
        "is_campaign_period": ("is_campaign_period", "max"),
    }
    for column in ("postal_code", "province", "analytic_block", "category", "family"):
        if column in sales.columns:
            aggregations[column] = (column, "last")
    return (
        sales.groupby(group_columns + ["invoice_number"], dropna=False)
        .agg(**aggregations)
        .reset_index()
        .sort_values(group_columns + ["sale_date", "invoice_number"])
        .reset_index(drop=True)
    )


def _build_daily_order_frame(order_frame: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    return (
        order_frame.groupby(group_columns + ["sale_date"], dropna=False)
        .agg(
            daily_revenue=("order_revenue", "sum"),
            daily_orders=("invoice_number", "size"),
            daily_returns=("is_return", "sum"),
        )
        .reset_index()
        .sort_values(group_columns + ["sale_date"])
        .reset_index(drop=True)
    )


def _latest_rolling_aggregate(
    daily_frame: pd.DataFrame,
    *,
    group_columns: list[str],
    value_column: str,
    aggregate: str,
    output_column: str,
) -> pd.DataFrame:
    if daily_frame.empty:
        return pd.DataFrame(columns=[*group_columns, output_column])
    rolled = (
        daily_frame.groupby(group_columns)
        .rolling("30D", on="sale_date")[value_column]
        .agg(aggregate)
        .reset_index()
    )
    latest = rolled.groupby(group_columns, as_index=False).tail(1)
    return latest[group_columns + [value_column]].rename(columns={value_column: output_column})


def _window_sum(
    order_frame: pd.DataFrame,
    *,
    group_columns: list[str],
    value_column: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    output_column: str,
) -> pd.DataFrame:
    window_frame = order_frame.loc[order_frame["sale_date"].between(start_date, end_date)]
    if window_frame.empty:
        return pd.DataFrame(columns=[*group_columns, output_column])
    return (
        window_frame.groupby(group_columns, dropna=False)[value_column]
        .sum()
        .reset_index()
        .rename(columns={value_column: output_column})
    )


def _build_frequency(frame: pd.DataFrame, total_orders_column: str) -> pd.Series:
    active_days = (frame["last_order_date"].dt.normalize() - frame["first_order_date"].dt.normalize()).dt.days.add(1)
    active_months = active_days.astype(float).div(FREQUENCY_MONTH_DAYS).clip(lower=1.0)
    return _safe_ratio(frame[total_orders_column].astype(float), active_months)


def _build_growth(current: pd.Series, previous: pd.Series) -> pd.Series:
    growth = _safe_ratio(current - previous, previous)
    return stabilize_feature_values(growth, clip_range=GROWTH_CLIP_RANGE)


def _build_campaign_lift(order_frame: pd.DataFrame, group_columns: list[str], output_column: str) -> pd.DataFrame:
    if order_frame.empty:
        return pd.DataFrame(columns=[*group_columns, output_column])
    pivot = (
        order_frame.groupby(group_columns + ["is_campaign_period"], dropna=False)["order_revenue"]
        .mean()
        .unstack(fill_value=0.0)
        .reset_index()
    )
    with_campaign = pivot.get(True, pd.Series(0.0, index=pivot.index))
    baseline = pivot.get(False, pd.Series(0.0, index=pivot.index))
    pivot[output_column] = stabilize_feature_values(
        _safe_ratio(with_campaign - baseline, baseline),
        clip_range=CAMPAIGN_LIFT_CLIP_RANGE,
    )
    return pivot[group_columns + [output_column]]


def _finalize_feature_table(features: pd.DataFrame, output_columns: list[str], sort_column: str) -> pd.DataFrame:
    table = features.copy()
    for column in output_columns:
        if column not in table.columns:
            table[column] = pd.NA
    table = table[output_columns].copy()
    numeric_columns = table.select_dtypes(include=["number", "bool"]).columns
    table[numeric_columns] = table[numeric_columns].fillna(0)
    return table.sort_values(sort_column, ascending=False).reset_index(drop=True)


def build_client_features(
    sales: pd.DataFrame,
    *,
    embedding_bundle: EmbeddingFeatureBundle | None = None,
) -> pd.DataFrame:
    group_columns = ["client_id"]
    reference_date = sales["sale_date"].max().normalize()
    order_frame = _build_order_frame(sales, group_columns)
    daily_frame = _build_daily_order_frame(order_frame, group_columns)
    embedding_bundle = embedding_bundle or build_embedding_bundle(sales)

    base = (
        order_frame.groupby(group_columns, dropna=False)
        .agg(
            postal_code=("postal_code", "last"),
            province=("province", "last"),
            customer_total_revenue=("order_revenue", "sum"),
            customer_total_orders=("invoice_number", "size"),
            first_order_date=("sale_date", "min"),
            last_order_date=("sale_date", "max"),
        )
        .reset_index()
    )
    base["customer_avg_ticket"] = _safe_ratio(base["customer_total_revenue"], base["customer_total_orders"])
    base["customer_frequency"] = stabilize_feature_values(_build_frequency(base, "customer_total_orders"), lower_bound=0.0)
    base["customer_frequency_log1p"] = np.log1p(base["customer_frequency"].clip(lower=0.0))
    base["days_since_last_order"] = (reference_date - base["last_order_date"].dt.normalize()).dt.days.clip(lower=0)
    base["is_active_customer"] = base["days_since_last_order"].lt(ACTIVE_CUSTOMER_THRESHOLD_DAYS)

    recent = base[group_columns].copy()
    recent = recent.merge(_latest_rolling_aggregate(daily_frame, group_columns=group_columns, value_column="daily_returns", aggregate="sum", output_column="return_orders_30d"), on=group_columns, how="left")
    recent = recent.merge(_latest_rolling_aggregate(daily_frame, group_columns=group_columns, value_column="daily_orders", aggregate="sum", output_column="orders_30d"), on=group_columns, how="left")
    recent = recent.merge(_latest_rolling_aggregate(daily_frame, group_columns=group_columns, value_column="daily_revenue", aggregate="mean", output_column="daily_revenue_mean_30d"), on=group_columns, how="left")
    recent = recent.merge(_latest_rolling_aggregate(daily_frame, group_columns=group_columns, value_column="daily_revenue", aggregate="std", output_column="daily_revenue_std_30d"), on=group_columns, how="left")
    recent = recent.merge(_build_campaign_lift(order_frame, group_columns, "campaign_lift"), on=group_columns, how="left")

    features = base.merge(recent, on=group_columns, how="left")
    features["return_rate_30d"] = stabilize_feature_values(
        _safe_ratio(features["return_orders_30d"].fillna(0.0), features["orders_30d"].fillna(0.0)),
        percentile_range=None,
        clip_range=(0.0, 1.0),
        lower_bound=0.0,
        upper_bound=1.0,
    )
    features["coefficient_variation_30d"] = stabilize_feature_values(
        _safe_ratio(features["daily_revenue_std_30d"].fillna(0.0), features["daily_revenue_mean_30d"].fillna(0.0)),
        clip_range=COEFFICIENT_VARIATION_CLIP_RANGE,
    )
    features = features.merge(embedding_bundle.client_features, on="client_id", how="left")
    return _finalize_feature_table(features, CLIENT_FEATURE_COLUMNS, "customer_total_revenue")


def build_product_features(
    sales: pd.DataFrame,
    *,
    embedding_bundle: EmbeddingFeatureBundle | None = None,
) -> pd.DataFrame:
    group_columns = ["product_id"]
    reference_date = sales["sale_date"].max().normalize()
    current_start = reference_date - pd.Timedelta(days=29)
    previous_end = current_start - pd.Timedelta(days=1)
    previous_start = previous_end - pd.Timedelta(days=29)

    order_frame = _build_order_frame(sales, group_columns)
    daily_frame = _build_daily_order_frame(order_frame, group_columns)
    embedding_bundle = embedding_bundle or build_embedding_bundle(sales)
    base = (
        order_frame.groupby(group_columns, dropna=False)
        .agg(
            analytic_block=("analytic_block", "last"),
            category=("category", "last"),
            family=("family", "last"),
            product_total_revenue=("order_revenue", "sum"),
            product_total_units=("order_units", "sum"),
            product_total_orders=("invoice_number", "size"),
            first_order_date=("sale_date", "min"),
            last_order_date=("sale_date", "max"),
            product_return_rate=("is_return", "mean"),
        )
        .reset_index()
    )
    base["product_frequency"] = _build_frequency(base, "product_total_orders")

    features = base.merge(
        _latest_rolling_aggregate(daily_frame, group_columns=group_columns, value_column="daily_revenue", aggregate="sum", output_column="rolling_sales_30d"),
        on=group_columns,
        how="left",
    )
    current_sales = _window_sum(order_frame, group_columns=group_columns, value_column="order_revenue", start_date=current_start, end_date=reference_date, output_column="current_sales_30d")
    previous_sales = _window_sum(order_frame, group_columns=group_columns, value_column="order_revenue", start_date=previous_start, end_date=previous_end, output_column="previous_sales_30d")
    customer_counts = (
        sales.groupby(group_columns, dropna=False)["client_id"].nunique().reset_index().rename(columns={"client_id": "product_customer_count"})
    )
    features = features.merge(current_sales, on=group_columns, how="left")
    features = features.merge(previous_sales, on=group_columns, how="left")
    features = features.merge(customer_counts, on=group_columns, how="left")
    features["rolling_sales_30d"] = stabilize_feature_values(features["rolling_sales_30d"])
    features["product_growth_30d"] = _build_growth(
        features["current_sales_30d"].fillna(0.0),
        features["previous_sales_30d"].fillna(0.0),
    )
    features["product_return_rate"] = stabilize_feature_values(
        features["product_return_rate"],
        percentile_range=None,
        clip_range=(0.0, 1.0),
        lower_bound=0.0,
        upper_bound=1.0,
    )
    features = features.merge(embedding_bundle.product_features, on="product_id", how="left")
    return _finalize_feature_table(features, PRODUCT_FEATURE_COLUMNS, "product_total_revenue")


def build_client_product_features(
    sales: pd.DataFrame,
    *,
    embedding_bundle: EmbeddingFeatureBundle | None = None,
) -> pd.DataFrame:
    group_columns = ["client_id", "product_id"]
    reference_date = sales["sale_date"].max().normalize()
    current_start = reference_date - pd.Timedelta(days=29)
    previous_end = current_start - pd.Timedelta(days=1)
    previous_start = previous_end - pd.Timedelta(days=29)

    order_frame = _build_order_frame(sales, group_columns)
    daily_frame = _build_daily_order_frame(order_frame, group_columns)
    embedding_bundle = embedding_bundle or build_embedding_bundle(sales)
    base = (
        order_frame.groupby(group_columns, dropna=False)
        .agg(
            client_product_total_revenue=("order_revenue", "sum"),
            client_product_total_orders=("invoice_number", "size"),
            first_order_date=("sale_date", "min"),
            last_order_date=("sale_date", "max"),
            client_product_return_rate=("is_return", "mean"),
        )
        .reset_index()
    )
    base["client_product_avg_ticket"] = _safe_ratio(
        base["client_product_total_revenue"], base["client_product_total_orders"]
    )
    base["client_product_frequency"] = _build_frequency(base, "client_product_total_orders")
    base["days_since_last_product_order"] = (
        reference_date - base["last_order_date"].dt.normalize()
    ).dt.days.clip(lower=0)

    features = base.merge(
        _latest_rolling_aggregate(daily_frame, group_columns=group_columns, value_column="daily_revenue", aggregate="sum", output_column="rolling_sales_30d"),
        on=group_columns,
        how="left",
    )
    current_sales = _window_sum(order_frame, group_columns=group_columns, value_column="order_revenue", start_date=current_start, end_date=reference_date, output_column="current_sales_30d")
    previous_sales = _window_sum(order_frame, group_columns=group_columns, value_column="order_revenue", start_date=previous_start, end_date=previous_end, output_column="previous_sales_30d")
    features = features.merge(current_sales, on=group_columns, how="left")
    features = features.merge(previous_sales, on=group_columns, how="left")
    features = features.merge(_build_campaign_lift(order_frame, group_columns, "campaign_lift_product"), on=group_columns, how="left")
    features["rolling_sales_30d"] = stabilize_feature_values(features["rolling_sales_30d"])
    features["sales_growth_30d"] = _build_growth(
        features["current_sales_30d"].fillna(0.0),
        features["previous_sales_30d"].fillna(0.0),
    )
    features["client_product_return_rate"] = stabilize_feature_values(
        features["client_product_return_rate"],
        percentile_range=None,
        clip_range=(0.0, 1.0),
        lower_bound=0.0,
        upper_bound=1.0,
    )
    features = features.merge(
        embedding_bundle.client_product_features,
        on=["client_id", "product_id"],
        how="left",
    )
    return _finalize_feature_table(features, CLIENT_PRODUCT_FEATURE_COLUMNS, "client_product_total_revenue")


def _align_table_to_contract(frame: pd.DataFrame, expected_columns: list[str]) -> tuple[pd.DataFrame, list[str]]:
    removed_columns = [column for column in frame.columns if column not in expected_columns]
    aligned = frame.copy()
    for column in expected_columns:
        if column not in aligned.columns:
            aligned[column] = pd.NA
    return aligned[expected_columns].copy(), removed_columns


def align_feature_tables_to_contract(
    frames: dict[str, pd.DataFrame],
) -> tuple[dict[str, pd.DataFrame], dict[str, list[str]]]:
    aligned_frames: dict[str, pd.DataFrame] = {}
    removed_columns_by_table: dict[str, list[str]] = {}
    for table_name, frame in frames.items():
        aligned_frames[table_name], removed_columns_by_table[table_name] = _align_table_to_contract(
            frame, FEATURE_TABLE_SCHEMAS[table_name]
        )
    return aligned_frames, removed_columns_by_table


def _json_safe_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return pd.Timestamp(value).isoformat()
    if isinstance(value, np.generic):
        return value.item()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _row_signature_frame(frame: pd.DataFrame, *, key_columns: list[str]) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=[*key_columns, "__signature"])
    value_columns = [
        column
        for column in frame.columns
        if column not in key_columns
        and not any(column.startswith(prefix) for prefix in EMBEDDING_FEATURE_PREFIXES)
    ]
    signatures = frame.apply(
        lambda row: hashlib.sha1(
            json.dumps(
                {column: _json_safe_value(row[column]) for column in value_columns},
                ensure_ascii=True,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest(),
        axis=1,
    )
    return frame[key_columns].copy().assign(__signature=signatures.astype("string"))


def _read_state_frame(path: Path, expected_columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=expected_columns)
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        frame = pd.DataFrame(payload) if isinstance(payload, list) else pd.DataFrame(columns=expected_columns)
    else:
        frame = read_csv_frame(path)
    for column in expected_columns:
        if column not in frame.columns:
            frame[column] = pd.NA
    return frame[expected_columns].copy()


def load_feature_state_frames(
    *,
    mode: RunMode,
    config: FeatureConfig,
) -> dict[str, pd.DataFrame]:
    state_dir = config.state_dir_for_mode(mode)
    frames: dict[str, pd.DataFrame] = {}
    for table_name, file_name in FEATURE_STATE_OUTPUT_FILES.items():
        json_path = state_dir / file_name
        csv_fallback_path = state_dir / FEATURE_OUTPUT_FILES[table_name]
        path = json_path if json_path.exists() else csv_fallback_path
        frames[table_name] = _read_state_frame(path, FEATURE_TABLE_SCHEMAS[table_name])
    return frames


def _daily_delta_table(
    current: pd.DataFrame,
    previous: pd.DataFrame,
    *,
    key_columns: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    current_normalized = current.copy()
    previous_normalized = previous.copy()
    for key_column in key_columns:
        if key_column in current_normalized.columns:
            current_normalized[key_column] = current_normalized[key_column].astype("string").str.strip()
        if key_column in previous_normalized.columns:
            previous_normalized[key_column] = previous_normalized[key_column].astype("string").str.strip()

    current_signature = _row_signature_frame(current_normalized, key_columns=key_columns)
    previous_signature = _row_signature_frame(previous_normalized, key_columns=key_columns)
    merged = current_signature.merge(
        previous_signature,
        on=key_columns,
        how="outer",
        suffixes=("_current", "_previous"),
        indicator=True,
    )

    new_or_updated_keys = merged.loc[
        merged["_merge"].eq("left_only")
        | (
            merged["_merge"].eq("both")
            & merged["__signature_current"].ne(merged["__signature_previous"])
        ),
        key_columns,
    ].drop_duplicates()
    removed_keys = merged.loc[merged["_merge"].eq("right_only"), key_columns].drop_duplicates()

    changed_rows = (
        current_normalized.merge(new_or_updated_keys, on=key_columns, how="inner")
        if not new_or_updated_keys.empty
        else current_normalized.iloc[0:0].copy()
    )
    stats = {
        "current_rows": int(len(current_normalized)),
        "previous_rows": int(len(previous_normalized)),
        "changed_rows": int(len(changed_rows)),
        "removed_rows": int(len(removed_keys)),
        "unchanged_rows": int(
            max(len(current_signature) - len(new_or_updated_keys), 0)
        ),
    }
    return changed_rows, removed_keys, stats


def compute_daily_feature_delta(
    frames: dict[str, pd.DataFrame],
    *,
    mode: RunMode,
    config: FeatureConfig,
    source_rows: int,
    snapshot_date: pd.Timestamp | None,
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], dict[str, object]]:
    previous_frames = load_feature_state_frames(mode=mode, config=config)
    changed_frames: dict[str, pd.DataFrame] = {}
    removed_keys_by_table: dict[str, pd.DataFrame] = {}
    table_stats: dict[str, object] = {}

    for table_name, frame in frames.items():
        changed_rows, removed_keys, stats = _daily_delta_table(
            frame,
            previous_frames.get(table_name, pd.DataFrame(columns=frame.columns)),
            key_columns=FEATURE_PRIMARY_KEYS[table_name],
        )
        changed_frames[table_name] = changed_rows
        removed_keys_by_table[table_name] = removed_keys
        table_stats[table_name] = {
            **stats,
            "primary_key": FEATURE_PRIMARY_KEYS[table_name],
        }

    manifest: dict[str, object] = {
        "mode": mode,
        "generated_at": datetime.now(UTC).isoformat(),
        "source_rows": int(source_rows),
        "snapshot_date": snapshot_date.date().isoformat() if snapshot_date is not None and not pd.isna(snapshot_date) else None,
        "tables": table_stats,
    }
    return changed_frames, removed_keys_by_table, manifest


def persist_daily_feature_delta(
    changed_frames: dict[str, pd.DataFrame],
    removed_keys_by_table: dict[str, pd.DataFrame],
    manifest: dict[str, object],
    *,
    mode: RunMode,
    config: FeatureConfig,
) -> dict[str, Path]:
    delta_dir = ensure_directory(config.delta_dir_for_mode(mode))
    outputs: dict[str, Path] = {
        "daily_feature_delta_manifest": write_json(manifest, delta_dir / DAILY_DELTA_MANIFEST_FILE),
    }
    for table_name, file_name in DAILY_DELTA_OUTPUT_FILES.items():
        outputs[file_name[:-4]] = write_csv_frame(changed_frames[table_name], delta_dir / file_name)
        removed_output_name = f"removed_{file_name}"
        outputs[removed_output_name[:-4]] = write_csv_frame(
            removed_keys_by_table[table_name],
            delta_dir / removed_output_name,
        )
    return outputs


def persist_feature_state(
    frames: dict[str, pd.DataFrame],
    manifest: dict[str, object],
    *,
    mode: RunMode,
    config: FeatureConfig,
) -> dict[str, Path]:
    state_dir = ensure_directory(config.state_dir_for_mode(mode))
    outputs: dict[str, Path] = {
        "feature_state_manifest": write_json(manifest, state_dir / FEATURE_STATE_MANIFEST_FILE),
    }
    for table_name, file_name in FEATURE_STATE_OUTPUT_FILES.items():
        output_path = state_dir / file_name
        output_path.write_text(
            json.dumps(frames[table_name].to_dict(orient="records"), indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        outputs[f"state_{file_name[:-5]}"] = output_path
    return outputs


def write_feature_frames(
    frames: dict[str, pd.DataFrame],
    *,
    mode: RunMode,
    config: FeatureConfig,
) -> dict[str, Path]:
    output_dir = ensure_directory(config.features_dir_for_mode(mode))
    output_frames = dict(frames)
    product_catalog = _load_product_catalog(config)
    output_frames["product_features"] = product_catalog.merge(
        frames["product_features"],
        on=["product_id", "analytic_block", "category", "family"],
        how="left",
    )
    numeric_columns = output_frames["product_features"].select_dtypes(include=["number", "bool"]).columns
    output_frames["product_features"][numeric_columns] = output_frames["product_features"][numeric_columns].fillna(0)
    output_frames["product_features"] = output_frames["product_features"][PRODUCT_FEATURE_COLUMNS].copy()

    outputs: dict[str, Path] = {}
    for dataset_name, file_name in FEATURE_OUTPUT_FILES.items():
        output_key = file_name[:-4] if file_name.endswith(".csv") else dataset_name
        outputs[output_key] = write_csv_frame(
            output_frames[dataset_name],
            output_dir / file_name,
        )
    return outputs


def _empty_frames() -> dict[str, pd.DataFrame]:
    return {
        "client_features": pd.DataFrame(columns=CLIENT_FEATURE_COLUMNS),
        "product_features": pd.DataFrame(columns=PRODUCT_FEATURE_COLUMNS),
        "client_product_features": pd.DataFrame(columns=CLIENT_PRODUCT_FEATURE_COLUMNS),
    }


def run_feature_pipeline(
    *,
    mode: RunMode,
    config: FeatureConfig,
) -> dict[str, Path]:
    source_frame = load_feature_source_frame(mode, config)
    commodity_sales = _prepare_sales_frame(source_frame, commodity_only=True)
    all_product_sales = _prepare_sales_frame(source_frame, commodity_only=False)
    snapshot_date = (
        all_product_sales["sale_date"].max().normalize()
        if not all_product_sales.empty and "sale_date" in all_product_sales.columns
        else None
    )
    embedding_bundle = build_embedding_bundle(all_product_sales) if not all_product_sales.empty else None
    frames = _empty_frames() if commodity_sales.empty and all_product_sales.empty else {
        "client_features": build_client_features(all_product_sales, embedding_bundle=embedding_bundle) if not all_product_sales.empty else pd.DataFrame(columns=CLIENT_FEATURE_COLUMNS),
        "product_features": build_product_features(all_product_sales, embedding_bundle=embedding_bundle) if not all_product_sales.empty else pd.DataFrame(columns=PRODUCT_FEATURE_COLUMNS),
        "client_product_features": build_client_product_features(all_product_sales, embedding_bundle=embedding_bundle) if not all_product_sales.empty else pd.DataFrame(columns=CLIENT_PRODUCT_FEATURE_COLUMNS),
    }
    frames, _ = align_feature_tables_to_contract(frames)
    outputs = write_feature_frames(frames, mode=mode, config=config)
    if mode == "daily":
        changed_frames, removed_keys_by_table, delta_manifest = compute_daily_feature_delta(
            frames,
            mode=mode,
            config=config,
            source_rows=len(source_frame),
            snapshot_date=snapshot_date,
        )
        outputs.update(
            persist_daily_feature_delta(
                changed_frames,
                removed_keys_by_table,
                delta_manifest,
                mode=mode,
                config=config,
            )
        )
        outputs.update(
            persist_feature_state(
                frames,
                delta_manifest,
                mode=mode,
                config=config,
            )
        )
    logger.info(
        "Feature tables built: clients=%s, products=%s, client_products=%s",
        len(frames["client_features"]),
        len(frames["product_features"]),
        len(frames["client_product_features"]),
    )
    return outputs
