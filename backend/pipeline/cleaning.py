from __future__ import annotations

import pandas as pd

from .config import CLEAN_DIR, RAW_DIR, ROOT_DIR, TABLE_CONFIG
from .utils import clean_identifier, normalize_header, parse_european_numeric, parse_us_date, read_raw_csv, strip_string_columns


def clean_table(table_name: str) -> tuple[pd.DataFrame, dict[str, object]]:
    config = TABLE_CONFIG[table_name]
    source_path = RAW_DIR / f"{table_name}.csv"
    df = read_raw_csv(source_path)
    original_rows = len(df)

    df.columns = [normalize_header(column) for column in df.columns]
    df = df.rename(columns=config["rename"])
    df = strip_string_columns(df)

    duplicate_rows = int(df.duplicated().sum())
    if duplicate_rows:
        df = df.drop_duplicates().reset_index(drop=True)

    invalid_dates: dict[str, int] = {}
    for column in config["date_columns"]:
        df[column], invalid_dates[column] = parse_us_date(df[column])

    invalid_numeric: dict[str, int] = {}
    for column, numeric_kind in config["numeric_columns"].items():
        df[column], invalid_numeric[column] = parse_european_numeric(df[column], as_integer=(numeric_kind == "int"))

    for column in config["id_columns"]:
        zero_fill = 5 if column == "postal_code" else None
        df[column] = clean_identifier(df[column], zero_fill=zero_fill)

    null_counts = {column: int(count) for column, count in df.isna().sum().items() if count > 0}

    report = {
        "source_file": str(source_path.relative_to(ROOT_DIR)),
        "rows_before": original_rows,
        "rows_after": len(df),
        "duplicates_removed": duplicate_rows,
        "invalid_dates": invalid_dates,
        "invalid_numeric": invalid_numeric,
        "null_counts": null_counts,
        "output_file": str((CLEAN_DIR / f"{table_name}.csv").relative_to(ROOT_DIR)),
    }
    return df, report


def clean_all_tables() -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, object]]]:
    cleaned_tables: dict[str, pd.DataFrame] = {}
    table_reports: dict[str, dict[str, object]] = {}

    for table_name in TABLE_CONFIG:
        cleaned_tables[table_name], table_reports[table_name] = clean_table(table_name)

    return cleaned_tables, table_reports


def enrich_sales_with_business_flags(cleaned_tables: dict[str, pd.DataFrame]) -> dict[str, object]:
    sales = cleaned_tables["sales"].copy()
    campaigns = cleaned_tables["campaigns"].copy()

    sales["is_refund"] = (sales["value"] < 0) | (sales["units"] < 0)
    sales["is_zero_value"] = sales["value"] == 0
    sales["is_zero_units"] = sales["units"] == 0
    sales["is_non_purchase_signal"] = sales["is_zero_value"] | sales["is_zero_units"]
    sales["campaign"] = pd.Series(pd.NA, index=sales.index, dtype="string")
    sales["is_campaign_period"] = False

    sales_dates = pd.to_datetime(sales["date"])
    campaigns["start_date"] = pd.to_datetime(campaigns["start_date"])
    campaigns["end_date"] = pd.to_datetime(campaigns["end_date"])

    for campaign_row in campaigns.itertuples(index=False):
        mask = (sales_dates >= campaign_row.start_date) & (sales_dates <= campaign_row.end_date)
        sales.loc[mask, "campaign"] = campaign_row.campaign
        sales.loc[mask, "is_campaign_period"] = True

    cleaned_tables["sales"] = sales

    return {
        "refund_rows": int(sales["is_refund"].sum()),
        "zero_value_rows": int(sales["is_zero_value"].sum()),
        "zero_unit_rows": int(sales["is_zero_units"].sum()),
        "non_purchase_signal_rows": int(sales["is_non_purchase_signal"].sum()),
        "campaign_period_rows": int(sales["is_campaign_period"].sum()),
        "campaigns_preserved": campaigns["campaign"].tolist(),
    }


def build_cross_table_checks(cleaned_tables: dict[str, pd.DataFrame]) -> dict[str, object]:
    sales_client_ids = set(cleaned_tables["sales"]["client_id"].dropna())
    client_master_ids = set(cleaned_tables["clients"]["client_id"].dropna())
    potential_client_ids = set(cleaned_tables["potential"]["client_id"].dropna())
    sales_product_ids = set(cleaned_tables["sales"]["product_id"].dropna())
    product_master_ids = set(cleaned_tables["products"]["product_id"].dropna())

    sales_clients_missing = sorted(sales_client_ids - client_master_ids)
    potential_clients_missing = sorted(potential_client_ids - client_master_ids)
    sales_products_missing = sorted(sales_product_ids - product_master_ids)

    return {
        "sales_client_ids_missing_in_clients": {
            "count": len(sales_clients_missing),
            "sample": sales_clients_missing[:10],
        },
        "potential_client_ids_missing_in_clients": {
            "count": len(potential_clients_missing),
            "sample": potential_clients_missing[:10],
        },
        "sales_product_ids_missing_in_products": {
            "count": len(sales_products_missing),
            "sample": sales_products_missing[:10],
        },
    }