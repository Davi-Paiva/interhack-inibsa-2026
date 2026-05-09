from __future__ import annotations

import pandas as pd

from .utils import first_non_null_value


def build_client_dimension(cleaned_tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    clients = cleaned_tables["clients"].copy()
    sales_client_ids = set(cleaned_tables["sales"]["client_id"].dropna())
    potential_client_ids = set(cleaned_tables["potential"]["client_id"].dropna())
    master_client_ids = set(clients["client_id"].dropna())
    all_client_ids = sorted(master_client_ids | sales_client_ids | potential_client_ids)

    client_dimension = pd.DataFrame({"client_id": pd.Series(all_client_ids, dtype="string")})
    canonical_master = (
        clients.sort_values(["client_id", "province", "postal_code"], na_position="last")
        .drop_duplicates(subset=["client_id"], keep="first")
        [["client_id", "postal_code", "province"]]
    )
    master_profile = (
        clients.groupby("client_id", as_index=False)
        .agg(
            client_master_records=("client_id", "size"),
            postal_code_options=("postal_code", pd.Series.nunique),
            province_options=("province", pd.Series.nunique),
        )
    )

    client_dimension = client_dimension.merge(canonical_master, on="client_id", how="left")
    client_dimension = client_dimension.merge(master_profile, on="client_id", how="left")
    for column in ["client_master_records", "postal_code_options", "province_options"]:
        client_dimension[column] = client_dimension[column].fillna(0).astype("Int64")

    client_dimension["in_clients_master"] = client_dimension["client_id"].isin(master_client_ids)
    client_dimension["has_sales_history"] = client_dimension["client_id"].isin(sales_client_ids)
    client_dimension["has_potential"] = client_dimension["client_id"].isin(potential_client_ids)
    client_dimension["client_master_conflict"] = (
        (client_dimension["client_master_records"] > 1)
        | (client_dimension["postal_code_options"] > 1)
        | (client_dimension["province_options"] > 1)
    )

    return client_dimension[
        [
            "client_id",
            "postal_code",
            "province",
            "in_clients_master",
            "has_sales_history",
            "has_potential",
            "client_master_conflict",
        ]
    ]


def build_product_dimension(cleaned_tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    products = (
        cleaned_tables["products"]
        .copy()
        .sort_values("product_id")
        .drop_duplicates(subset=["product_id"], keep="first")
    )
    products["product_type"] = products["analytical_block"].map({"Commodities": "commodity"}).fillna("technical")
    return products[["product_id", "analytical_block", "product_category", "product_family", "product_type"]]


def build_category_dimension(product_dimension: pd.DataFrame) -> pd.DataFrame:
    return (
        product_dimension.groupby("product_category", as_index=False)
        .agg(
            product_type=("product_type", first_non_null_value),
            category_product_count=("product_id", "nunique"),
        )
    )


def build_potential_table(cleaned_tables: dict[str, pd.DataFrame], category_dimension: pd.DataFrame) -> pd.DataFrame:
    potential = (
        cleaned_tables["potential"]
        .groupby(["client_id", "product_category"], as_index=False)
        .agg(
            potential_value=("potential_value", "sum"),
            potential_family_count=("potential_family", "nunique"),
        )
    )
    potential["potential_value"] = potential["potential_value"].round(2)
    potential = potential.merge(category_dimension, on="product_category", how="left")
    return potential[["client_id", "product_category", "product_type", "potential_value", "potential_family_count"]]


def build_sales_transactions(
    cleaned_tables: dict[str, pd.DataFrame],
    client_dimension: pd.DataFrame,
    product_dimension: pd.DataFrame,
) -> pd.DataFrame:
    sales = cleaned_tables["sales"].copy().rename(columns={"units": "signed_units", "value": "signed_value"})
    sales["purchase_units"] = sales["signed_units"].where(
        (sales["signed_units"] > 0) & ~sales["is_refund"] & ~sales["is_non_purchase_signal"],
        0,
    )
    sales["purchase_value"] = sales["signed_value"].where(
        (sales["signed_value"] > 0) & ~sales["is_refund"] & ~sales["is_non_purchase_signal"],
        0.0,
    ).round(2)
    sales["refund_units"] = sales["signed_units"].where(sales["signed_units"] < 0, 0).abs()
    sales["refund_value"] = sales["signed_value"].where(sales["signed_value"] < 0, 0.0).abs().round(2)
    sales["campaign_purchase_value"] = sales["purchase_value"].where(sales["is_campaign_period"], 0.0).round(2)

    sales = sales.merge(
        client_dimension[["client_id", "postal_code", "province", "in_clients_master", "client_master_conflict"]],
        on="client_id",
        how="left",
    )
    sales = sales.merge(product_dimension, on="product_id", how="left")

    return sales[
        [
            "invoice_id",
            "date",
            "client_id",
            "postal_code",
            "province",
            "in_clients_master",
            "client_master_conflict",
            "product_id",
            "product_category",
            "product_family",
            "product_type",
            "campaign",
            "is_campaign_period",
            "signed_units",
            "signed_value",
            "purchase_units",
            "purchase_value",
            "campaign_purchase_value",
            "refund_units",
            "refund_value",
            "is_refund",
            "is_non_purchase_signal",
        ]
    ]


def build_client_category_daily(
    sales_transactions: pd.DataFrame,
    client_dimension: pd.DataFrame,
    potential_table: pd.DataFrame,
    category_dimension: pd.DataFrame,
) -> pd.DataFrame:
    daily = (
        sales_transactions.groupby(["client_id", "date", "product_category"], as_index=False, dropna=False)
        .agg(
            invoice_count=("invoice_id", "nunique"),
            product_count=("product_id", "nunique"),
            purchase_units=("purchase_units", "sum"),
            purchase_value=("purchase_value", "sum"),
            refund_units=("refund_units", "sum"),
            refund_value=("refund_value", "sum"),
            signed_units=("signed_units", "sum"),
            signed_value=("signed_value", "sum"),
            refund_row_count=("is_refund", "sum"),
            non_purchase_signal_count=("is_non_purchase_signal", "sum"),
            campaign=("campaign", first_non_null_value),
            is_campaign_period=("is_campaign_period", "max"),
        )
    )
    daily = daily.merge(category_dimension, on="product_category", how="left")
    daily = daily.merge(
        client_dimension[["client_id", "postal_code", "province", "in_clients_master", "client_master_conflict"]],
        on="client_id",
        how="left",
    )
    daily = daily.merge(
        potential_table[["client_id", "product_category", "potential_value", "potential_family_count"]],
        on=["client_id", "product_category"],
        how="left",
    )
    daily["has_category_potential"] = daily["potential_value"].notna()
    daily["potential_value"] = daily["potential_value"].fillna(0.0).round(2)
    daily["potential_family_count"] = daily["potential_family_count"].fillna(0).astype("Int64")
    for count_column in [
        "invoice_count",
        "product_count",
        "purchase_units",
        "refund_units",
        "signed_units",
        "refund_row_count",
        "non_purchase_signal_count",
    ]:
        daily[count_column] = daily[count_column].astype("Int64")
    for value_column in ["purchase_value", "refund_value", "signed_value"]:
        daily[value_column] = daily[value_column].round(2)

    return daily[
        [
            "client_id",
            "date",
            "product_category",
            "product_type",
            "postal_code",
            "province",
            "in_clients_master",
            "client_master_conflict",
            "has_category_potential",
            "potential_value",
            "potential_family_count",
            "invoice_count",
            "product_count",
            "purchase_units",
            "purchase_value",
            "refund_units",
            "refund_value",
            "signed_units",
            "signed_value",
            "refund_row_count",
            "non_purchase_signal_count",
            "campaign",
            "is_campaign_period",
        ]
    ]


def build_client_category_summary(
    sales_transactions: pd.DataFrame,
    client_dimension: pd.DataFrame,
    potential_table: pd.DataFrame,
    category_dimension: pd.DataFrame,
) -> pd.DataFrame:
    category_universe = pd.concat(
        [
            sales_transactions[["client_id", "product_category"]],
            potential_table[["client_id", "product_category"]],
        ],
        ignore_index=True,
    ).drop_duplicates()

    summary = (
        sales_transactions.groupby(["client_id", "product_category"], as_index=False)
        .agg(
            first_observed_date=("date", "min"),
            last_observed_date=("date", "max"),
            active_days=("date", "nunique"),
            invoice_count=("invoice_id", "nunique"),
            product_count=("product_id", "nunique"),
            purchase_units_total=("purchase_units", "sum"),
            purchase_value_total=("purchase_value", "sum"),
            refund_units_total=("refund_units", "sum"),
            refund_value_total=("refund_value", "sum"),
            non_purchase_signal_count=("is_non_purchase_signal", "sum"),
            campaign_purchase_value_total=("campaign_purchase_value", "sum"),
        )
    )

    summary = category_universe.merge(summary, on=["client_id", "product_category"], how="left")
    summary = summary.merge(category_dimension, on="product_category", how="left")
    summary = summary.merge(
        client_dimension[["client_id", "postal_code", "province", "in_clients_master", "client_master_conflict"]],
        on="client_id",
        how="left",
    )
    summary = summary.merge(
        potential_table[["client_id", "product_category", "potential_value", "potential_family_count"]],
        on=["client_id", "product_category"],
        how="left",
    )

    summary["has_observed_sales"] = summary["first_observed_date"].notna()
    summary["has_category_potential"] = summary["potential_value"].notna()
    for numeric_column in [
        "active_days",
        "invoice_count",
        "product_count",
        "non_purchase_signal_count",
        "potential_family_count",
    ]:
        summary[numeric_column] = summary[numeric_column].fillna(0).astype("Int64")
    for unit_column in ["purchase_units_total", "refund_units_total"]:
        summary[unit_column] = summary[unit_column].fillna(0).astype("Int64")
    for value_column in ["purchase_value_total", "refund_value_total", "campaign_purchase_value_total"]:
        summary[value_column] = summary[value_column].fillna(0.0).round(2)
    summary["potential_value"] = summary["potential_value"].fillna(0.0).round(2)

    return summary[
        [
            "client_id",
            "product_category",
            "product_type",
            "postal_code",
            "province",
            "in_clients_master",
            "client_master_conflict",
            "has_category_potential",
            "potential_value",
            "potential_family_count",
            "has_observed_sales",
            "first_observed_date",
            "last_observed_date",
            "active_days",
            "invoice_count",
            "product_count",
            "purchase_units_total",
            "purchase_value_total",
            "refund_units_total",
            "refund_value_total",
            "non_purchase_signal_count",
            "campaign_purchase_value_total",
        ]
    ]


def build_model_ready_tables(cleaned_tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    client_dimension = build_client_dimension(cleaned_tables)
    product_dimension = build_product_dimension(cleaned_tables)
    category_dimension = build_category_dimension(product_dimension)
    potential_table = build_potential_table(cleaned_tables, category_dimension)
    sales_transactions = build_sales_transactions(cleaned_tables, client_dimension, product_dimension)
    client_category_daily = build_client_category_daily(sales_transactions, client_dimension, potential_table, category_dimension)
    client_category_summary = build_client_category_summary(sales_transactions, client_dimension, potential_table, category_dimension)

    return {
        "client_dimension": client_dimension,
        "product_dimension": product_dimension,
        "campaign_dimension": cleaned_tables["campaigns"].copy(),
        "client_category_potential": potential_table,
        "sales_transactions": sales_transactions,
        "client_category_daily": client_category_daily,
        "client_category_summary": client_category_summary,
    }