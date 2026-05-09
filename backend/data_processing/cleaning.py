from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

try:
    from .config import ProcessingConfig, RunMode
    from .utils import (
        normalize_identifier,
        normalize_text,
        parse_datetime_series,
        parse_decimal_series,
        read_csv,
        validate_required_columns,
        write_csv_frame,
        write_parquet_frame,
    )
    from .validation import (
        build_drift_metrics,
        build_quality_metrics,
        remove_non_campaign_outliers,
        save_metrics_json,
        tag_amount_outliers,
    )
except ImportError:
    from config import ProcessingConfig, RunMode
    from utils import (
        normalize_identifier,
        normalize_text,
        parse_datetime_series,
        parse_decimal_series,
        read_csv,
        validate_required_columns,
        write_csv_frame,
        write_parquet_frame,
    )
    from validation import (
        build_drift_metrics,
        build_quality_metrics,
        remove_non_campaign_outliers,
        save_metrics_json,
        tag_amount_outliers,
    )


SALES_COLUMNS = {
    "Num.Fact": "invoice_number",
    "Fecha": "sale_date",
    "Id. Cliente": "client_id",
    "Id. Producto": "product_id",
    "Unidades": "units",
    "Valores": "amount",
}
CLIENT_COLUMNS = {
    "Id. Cliente": "client_id",
    "Codigo Postal": "postal_code",
    "Provincia": "province",
}
PRODUCT_COLUMNS = {
    "Id.Prod": "product_id",
    "Bloque analítico": "analytic_block",
    "Categoria": "category",
    "Familia": "family",
}
CAMPAIGN_COLUMNS = {
    "Campaña": "campaign_id",
    "Fecha inicio": "start_date",
    "Fecha fin": "end_date",
}
POTENTIAL_COLUMNS = {
    "Id.Cliente": "client_id",
    "Familia": "family",
    "Categoria Productos": "product_category",
    "Potencial_H": "potential_h",
}

logger = logging.getLogger(__name__)


def _drop_corrupted_rows(
    df: pd.DataFrame,
    required_columns: list[str],
    dataset_name: str,
) -> pd.DataFrame:
    valid_mask = df[required_columns].notna().all(axis=1)
    removed_rows = int((~valid_mask).sum())
    if removed_rows:
        logger.warning("Removed %s corrupted rows from %s.", removed_rows, dataset_name)
    return df.loc[valid_mask].reset_index(drop=True)


def _keep_latest_reference(df: pd.DataFrame, key_columns: list[str], dataset_name: str) -> pd.DataFrame:
    duplicate_mask = df.duplicated(subset=key_columns, keep="last")
    duplicate_rows = int(duplicate_mask.sum())
    if duplicate_rows:
        logger.warning(
            "Resolved %s duplicated reference rows in %s using the latest record.",
            duplicate_rows,
            dataset_name,
        )
    return df.loc[~duplicate_mask].reset_index(drop=True)


def _add_temporal_features(sales: pd.DataFrame) -> pd.DataFrame:
    enriched = sales.copy()
    enriched["month"] = enriched["sale_date"].dt.month
    enriched["quarter"] = enriched["sale_date"].dt.quarter
    enriched["weekday"] = enriched["sale_date"].dt.weekday
    enriched["is_month_end"] = enriched["sale_date"].dt.is_month_end
    enriched["is_quarter_end"] = enriched["sale_date"].dt.is_quarter_end
    return enriched


def _add_campaign_context(sales: pd.DataFrame, campaigns: pd.DataFrame) -> pd.DataFrame:
    enriched = sales.copy()
    enriched["is_campaign_period"] = False
    enriched["campaign_id"] = pd.Series(pd.NA, index=enriched.index, dtype="string")

    for campaign in campaigns.itertuples(index=False):
        mask = enriched["sale_date"].between(campaign.start_date, campaign.end_date)
        enriched.loc[mask, "is_campaign_period"] = True
        enriched.loc[mask, "campaign_id"] = campaign.campaign_id

    return enriched


def _add_sales_enrichment_features(sales: pd.DataFrame) -> pd.DataFrame:
    enriched = sales.copy()
    if enriched.empty:
        enriched["rolling_sales_7d"] = pd.Series(dtype="float64")
        enriched["sales_delta_vs_7d"] = pd.Series(dtype="float64")
        return enriched

    daily_sales = (
        enriched.groupby(["client_id", "product_id", "sale_date"], dropna=False)["amount"]
        .sum()
        .reset_index(name="daily_sales_value")
        .sort_values(["client_id", "product_id", "sale_date"])
        .reset_index(drop=True)
    )

    rolling = (
        daily_sales.groupby(["client_id", "product_id"])
        .rolling("7D", on="sale_date")["daily_sales_value"]
        .sum()
        .reset_index()
        .rename(columns={"daily_sales_value": "rolling_sales_7d"})
    )
    daily_sales = daily_sales.merge(
        rolling,
        on=["client_id", "product_id", "sale_date"],
        how="left",
    )
    daily_sales["previous_rolling_sales_7d"] = (
        daily_sales.groupby(["client_id", "product_id"], dropna=False)["rolling_sales_7d"].shift(1)
    )
    daily_sales["sales_delta_vs_7d"] = (
        daily_sales["rolling_sales_7d"] - daily_sales["previous_rolling_sales_7d"].fillna(0.0)
    )

    return enriched.merge(
        daily_sales[["client_id", "product_id", "sale_date", "rolling_sales_7d", "sales_delta_vs_7d"]],
        on=["client_id", "product_id", "sale_date"],
        how="left",
    )


def _build_sales_enriched_output(sales: pd.DataFrame) -> pd.DataFrame:
    enriched = _add_sales_enrichment_features(sales)
    output = enriched.rename(
        columns={
            "invoice_number": "invoice_id",
            "sale_date": "date",
            "amount": "sales_value",
        }
    ).copy()
    return output[
        [
            "invoice_id",
            "date",
            "client_id",
            "product_id",
            "units",
            "sales_value",
            "is_return",
            "is_campaign_period",
            "campaign_id",
            "month",
            "quarter",
            "weekday",
            "is_month_end",
            "is_quarter_end",
            "rolling_sales_7d",
            "sales_delta_vs_7d",
        ]
    ].reset_index(drop=True)


def _build_campaigns_output(campaigns: pd.DataFrame) -> pd.DataFrame:
    output = campaigns.copy()
    output["campaign_duration_days"] = (
        output["end_date"].dt.normalize() - output["start_date"].dt.normalize()
    ).dt.days.add(1)
    return output[["campaign_id", "start_date", "end_date", "campaign_duration_days"]].reset_index(drop=True)


def _build_potential_output(sales: pd.DataFrame, potential: pd.DataFrame) -> pd.DataFrame:
    current_sales = (
        sales.groupby(["client_id", "family", "product_category"], dropna=False)["amount"]
        .sum()
        .reset_index(name="current_sales")
    )
    output = potential.merge(
        current_sales,
        on=["client_id", "family", "product_category"],
        how="left",
    )
    output["current_sales"] = output["current_sales"].fillna(0.0)
    output["potential_gap"] = output["potential_h"] - output["current_sales"]
    denominator = output["potential_h"].replace(0, pd.NA)
    output["capture_ratio"] = (output["current_sales"] / denominator).fillna(0.0)
    return output[
        [
            "client_id",
            "family",
            "product_category",
            "potential_h",
            "current_sales",
            "potential_gap",
            "capture_ratio",
        ]
    ].reset_index(drop=True)


def _merge_datasets(
    sales: pd.DataFrame,
    clients: pd.DataFrame,
    products: pd.DataFrame,
    potential: pd.DataFrame,
    campaigns: pd.DataFrame,
) -> pd.DataFrame:
    merged = sales.merge(products, on="product_id", how="left")
    merged = merged.merge(clients, on="client_id", how="left")
    merged = merged.merge(
        potential,
        on=["client_id", "family"],
        how="left",
    )
    merged = _add_temporal_features(merged)
    merged = _add_campaign_context(merged, campaigns)
    merged["is_return"] = merged["units"].lt(0) | merged["amount"].lt(0)
    merged = tag_amount_outliers(merged)
    return remove_non_campaign_outliers(merged)


def _load_raw_frames(
    *,
    mode: RunMode,
    config: ProcessingConfig,
    sales_path: Path | None = None,
) -> dict[str, pd.DataFrame]:
    sales_source = sales_path or (config.raw_data_dir / config.sales_file_for_mode(mode))
    logger.info("Loading raw input files for %s mode.", mode)
    return {
        "sales": read_csv(sales_source),
        "clients": read_csv(config.raw_data_dir / config.clients_file),
        "products": read_csv(config.raw_data_dir / config.products_file),
        "campaigns": read_csv(config.raw_data_dir / config.campaigns_file),
        "potential": read_csv(config.raw_data_dir / config.potential_file),
    }


def clean_sales(df: pd.DataFrame, config: ProcessingConfig) -> pd.DataFrame:
    validate_required_columns(df, SALES_COLUMNS.keys(), "sales")

    sales = df.rename(columns=SALES_COLUMNS).copy()
    sales["invoice_number"] = normalize_identifier(sales["invoice_number"])
    sales["client_id"] = normalize_identifier(sales["client_id"])
    sales["product_id"] = normalize_identifier(sales["product_id"])
    sales["sale_date"] = parse_datetime_series(sales["sale_date"], config.date_format)
    sales["units"] = pd.to_numeric(sales["units"], errors="coerce")
    sales["amount"] = parse_decimal_series(sales["amount"])
    sales = _drop_corrupted_rows(
        sales,
        ["invoice_number", "sale_date", "client_id", "product_id", "units", "amount"],
        "sales",
    )
    return sales.sort_values(["sale_date", "invoice_number"]).reset_index(drop=True)


def clean_clients(df: pd.DataFrame) -> pd.DataFrame:
    validate_required_columns(df, CLIENT_COLUMNS.keys(), "clients")

    clients = df.rename(columns=CLIENT_COLUMNS).copy()
    clients["client_id"] = normalize_identifier(clients["client_id"])
    clients["postal_code"] = normalize_text(clients["postal_code"])
    clients["province"] = normalize_text(clients["province"])
    clients = _drop_corrupted_rows(clients, ["client_id"], "clients")
    return _keep_latest_reference(clients, ["client_id"], "clients")


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    validate_required_columns(df, PRODUCT_COLUMNS.keys(), "products")

    products = df.rename(columns=PRODUCT_COLUMNS).copy()
    products["product_id"] = normalize_identifier(products["product_id"])
    products["analytic_block"] = normalize_text(products["analytic_block"])
    products["category"] = normalize_text(products["category"])
    products["family"] = normalize_text(products["family"])
    products = _drop_corrupted_rows(products, ["product_id"], "products")
    return _keep_latest_reference(products, ["product_id"], "products")


def clean_campaigns(df: pd.DataFrame, config: ProcessingConfig) -> pd.DataFrame:
    validate_required_columns(df, CAMPAIGN_COLUMNS.keys(), "campaigns")

    campaigns = df.rename(columns=CAMPAIGN_COLUMNS).copy()
    campaigns["campaign_id"] = normalize_text(campaigns["campaign_id"])
    campaigns["start_date"] = parse_datetime_series(campaigns["start_date"], config.date_format)
    campaigns["end_date"] = parse_datetime_series(campaigns["end_date"], config.date_format)
    campaigns = _drop_corrupted_rows(
        campaigns,
        ["campaign_id", "start_date", "end_date"],
        "campaigns",
    )
    return _keep_latest_reference(campaigns, ["campaign_id"], "campaigns")


def clean_potential(df: pd.DataFrame) -> pd.DataFrame:
    validate_required_columns(df, POTENTIAL_COLUMNS.keys(), "potential")

    potential = df.rename(columns=POTENTIAL_COLUMNS).copy()
    potential["client_id"] = normalize_identifier(potential["client_id"])
    potential["family"] = normalize_text(potential["family"])
    potential["product_category"] = normalize_text(potential["product_category"])
    potential["potential_h"] = parse_decimal_series(potential["potential_h"])
    potential = _drop_corrupted_rows(
        potential,
        ["client_id", "family", "product_category", "potential_h"],
        "potential",
    )
    return _keep_latest_reference(
        potential,
        ["client_id", "family", "product_category"],
        "potential",
    )


def build_processed_frames(
    *,
    mode: RunMode,
    config: ProcessingConfig,
    sales_path: Path | None = None,
) -> dict[str, pd.DataFrame]:
    raw_frames = _load_raw_frames(mode=mode, config=config, sales_path=sales_path)

    sales = clean_sales(raw_frames["sales"], config)
    clients = clean_clients(raw_frames["clients"])
    products = clean_products(raw_frames["products"])
    campaigns = clean_campaigns(raw_frames["campaigns"], config)
    potential = clean_potential(raw_frames["potential"])

    sales_clean = _merge_datasets(sales, clients, products, potential, campaigns)
    technical_mask = sales_clean["analytic_block"].fillna("").eq(config.technical_block_name)
    sales_technical = sales_clean.loc[technical_mask].copy()
    sales_enriched = _build_sales_enriched_output(sales_clean)
    campaigns_output = _build_campaigns_output(campaigns)
    potential_output = _build_potential_output(sales_clean, potential)

    logger.info(
        "Built processed frames: sales=%s, technical_sales=%s, clients=%s, products=%s, campaigns=%s, potential=%s",
        len(sales_clean),
        len(sales_technical),
        len(clients),
        len(products),
        len(campaigns),
        len(potential),
    )

    return {
        "sales_clean": sales_clean,
        "sales_technical_clean": sales_technical,
        "sales_enriched": sales_enriched,
        "clients_clean": clients,
        "products_clean": products,
        "campaigns_clean": campaigns,
        "potential_clean": potential,
        "campaigns": campaigns_output,
        "potential": potential_output,
    }


def build_monitoring_metrics(
    frames: Mapping[str, pd.DataFrame],
    *,
    mode: RunMode,
    config: ProcessingConfig,
) -> dict[str, Any]:
    sales_metrics = build_quality_metrics(
        frames["sales_clean"],
        dataset_name="sales_clean",
        duplicate_subset=["invoice_number", "client_id", "product_id", "sale_date"],
    )
    technical_sales_metrics = build_quality_metrics(
        frames["sales_technical_clean"],
        dataset_name="sales_technical_clean",
        duplicate_subset=["invoice_number", "client_id", "product_id", "sale_date"],
    )

    metrics: dict[str, Any] = {
        "mode": mode,
        "datasets": {
            "sales_clean": sales_metrics,
            "sales_technical_clean": technical_sales_metrics,
        },
        "drift_monitoring": {"status": "not_applicable", "features": {}},
    }

    if mode == "daily":
        historical_path = config.output_dir_for_mode("historical") / "sales_clean.parquet"
        if historical_path.exists():
            historical_sales = pd.read_parquet(historical_path)
            metrics["drift_monitoring"] = build_drift_metrics(
                historical_sales,
                frames["sales_clean"],
                numeric_columns=["amount", "units"],
            )
        else:
            logger.warning("Historical baseline not found at %s. Drift monitoring skipped.", historical_path)

    for dataset_metrics in metrics["datasets"].values():
        if dataset_metrics["missing_ratio"] > 0.05:
            logger.warning(
                "%s has elevated missing ratio: %.2f%%",
                dataset_metrics["dataset_name"],
                dataset_metrics["missing_ratio"] * 100,
            )
        if dataset_metrics["invalid_date_ratio"] > 0.0:
            logger.warning(
                "%s has invalid dates after processing: %.2f%%",
                dataset_metrics["dataset_name"],
                dataset_metrics["invalid_date_ratio"] * 100,
            )

    return metrics


def write_processed_frames(
    frames: Mapping[str, pd.DataFrame],
    *,
    mode: RunMode,
    config: ProcessingConfig,
) -> dict[str, dict[str, Path]]:
    output_dir = config.output_dir_for_mode(mode)
    outputs: dict[str, dict[str, Path]] = {}

    for dataset_name, frame in frames.items():
        parquet_path = output_dir / f"{dataset_name}.parquet"
        csv_path = output_dir / f"{dataset_name}.csv"
        outputs[dataset_name] = {
            "parquet": write_parquet_frame(
                frame,
                parquet_path,
                compression=config.parquet_compression,
            ),
            "csv": write_csv_frame(frame, csv_path),
        }

    return outputs


def run_cleaning_pipeline(
    *,
    mode: RunMode,
    config: ProcessingConfig,
    sales_path: Path | None = None,
) -> dict[str, dict[str, Path]]:
    frames = build_processed_frames(mode=mode, config=config, sales_path=sales_path)
    outputs = write_processed_frames(frames, mode=mode, config=config)
    metrics = build_monitoring_metrics(frames, mode=mode, config=config)
    metrics_path = config.metrics_dir_for_mode(mode) / "quality_metrics.json"
    save_metrics_json(metrics, metrics_path)
    outputs["quality_metrics"] = {"json": metrics_path}
    return outputs
