from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px

try:
    from ..config import FeatureConfig
    from ..features import CAMPAIGN_LIFT_CLIP_RANGE, COEFFICIENT_VARIATION_CLIP_RANGE, clean_feature_for_plot
    from ..utils import read_parquet_frame
except (ImportError, ValueError):
    from config import FeatureConfig
    from features import CAMPAIGN_LIFT_CLIP_RANGE, COEFFICIENT_VARIATION_CLIP_RANGE, clean_feature_for_plot
    from utils import read_parquet_frame


FEATURE_FILE_NAMES = {
    "client_features": "client_features.parquet",
    "product_features": "product_features.parquet",
    "client_product_features": "client_product_features.parquet",
}
PLOT_NAMES = [
    "Customer Frequency Distribution",
    "Rolling Sales Trend Visualization",
    "Campaign Lift Distribution",
    "Product Growth Distribution",
    "Customer Stability Visualization",
    "Top Products by Rolling Sales",
    "Customer-Product Behavior Scatterplot",
]


def empty_figure(title: str):
    return px.scatter(title=title)


def _safe_marker_size(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").fillna(0.0)
    return numeric.clip(lower=0.0)


def _top_k_frame(frame: pd.DataFrame, sort_column: str, top_k: int) -> pd.DataFrame:
    return frame.sort_values(sort_column, ascending=False).head(top_k).reset_index(drop=True)


def _assign_clean_plot_column(
    frame: pd.DataFrame,
    source_column: str,
    output_column: str,
    *,
    clip_range: tuple[float, float] | None = None,
    log1p_transform: bool = False,
) -> pd.DataFrame:
    plot_frame = frame.copy()
    plot_frame[output_column] = clean_feature_for_plot(
        plot_frame[source_column],
        clip_range=clip_range,
        log1p_transform=log1p_transform,
    )
    return plot_frame


def _drop_missing_plot_rows(frame: pd.DataFrame, required_columns: list[str]) -> pd.DataFrame:
    return frame.dropna(subset=required_columns).copy()


def feature_file_paths(config: FeatureConfig | None = None, mode: str = "historical") -> dict[str, Path]:
    feature_config = config or FeatureConfig()
    base_dir = feature_config.features_dir_for_mode(mode)
    return {
        table_name: base_dir / file_name
        for table_name, file_name in FEATURE_FILE_NAMES.items()
    }


def load_historical_feature_tables(config: FeatureConfig | None = None) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    for table_name, path in feature_file_paths(config=config, mode="historical").items():
        tables[table_name] = read_parquet_frame(path)
    return tables


def available_filter_options(client_features: pd.DataFrame, product_features: pd.DataFrame) -> dict[str, list[str]]:
    client_ids = sorted(client_features["client_id"].astype(str).unique().tolist()) if not client_features.empty else []
    product_ids = (
        sorted(product_features["product_id"].astype(str).unique().tolist()) if not product_features.empty else []
    )
    return {
        "client_ids": client_ids,
        "product_ids": product_ids,
    }


def filter_client_features(
    client_features: pd.DataFrame,
    *,
    selected_clients: list[str] | None = None,
    revenue_range: tuple[float, float] | None = None,
) -> pd.DataFrame:
    filtered = client_features.copy()
    if selected_clients:
        filtered = filtered.loc[filtered["client_id"].astype(str).isin(selected_clients)]
    if revenue_range is not None and not filtered.empty:
        filtered = filtered.loc[
            filtered["customer_total_revenue"].between(revenue_range[0], revenue_range[1])
        ]
    return filtered


def filter_product_features(
    product_features: pd.DataFrame,
    *,
    selected_products: list[str] | None = None,
    rolling_sales_range: tuple[float, float] | None = None,
) -> pd.DataFrame:
    filtered = product_features.copy()
    if selected_products:
        filtered = filtered.loc[filtered["product_id"].astype(str).isin(selected_products)]
    if rolling_sales_range is not None and not filtered.empty:
        filtered = filtered.loc[
            filtered["rolling_sales_30d"].between(rolling_sales_range[0], rolling_sales_range[1])
        ]
    return filtered


def filter_client_product_features(
    client_product_features: pd.DataFrame,
    *,
    selected_clients: list[str] | None = None,
    selected_products: list[str] | None = None,
) -> pd.DataFrame:
    filtered = client_product_features.copy()
    if selected_clients:
        filtered = filtered.loc[filtered["client_id"].astype(str).isin(selected_clients)]
    if selected_products:
        filtered = filtered.loc[filtered["product_id"].astype(str).isin(selected_products)]
    return filtered


def build_customer_frequency_distribution(client_features: pd.DataFrame):
    if client_features.empty:
        return empty_figure("Customer Frequency Distribution")

    plot_frame = _assign_clean_plot_column(
        client_features,
        "customer_frequency_log1p" if "customer_frequency_log1p" in client_features.columns else "customer_frequency",
        "_customer_frequency_plot",
    )
    plot_frame = _drop_missing_plot_rows(plot_frame, ["_customer_frequency_plot"])

    return px.histogram(
        plot_frame,
        x="_customer_frequency_plot",
        color="is_active_customer" if "is_active_customer" in plot_frame.columns else None,
        nbins=30,
        title="Customer Frequency Distribution",
        labels={"_customer_frequency_plot": "Customer frequency log1p", "count": "Customers"},
        hover_data=["client_id", "customer_frequency", "customer_total_revenue", "customer_total_orders"],
    )


def build_rolling_sales_trend_visualization(product_features: pd.DataFrame, top_n: int = 30):
    if product_features.empty:
        return empty_figure("Rolling Sales Trend")

    ranked = _assign_clean_plot_column(
        product_features,
        "rolling_sales_30d",
        "_rolling_sales_plot",
    )
    ranked = _drop_missing_plot_rows(ranked, ["_rolling_sales_plot"])
    ranked = _top_k_frame(ranked, "_rolling_sales_plot", top_n)
    ranked["rank"] = ranked.index + 1

    return px.line(
        ranked,
        x="rank",
        y="_rolling_sales_plot",
        markers=True,
        title="Rolling Sales Trend by Product Rank",
        labels={"rank": "Product rank", "_rolling_sales_plot": "Rolling sales 30d"},
        hover_data=["product_id", "product_total_revenue", "product_growth_30d"],
    )


def build_campaign_lift_distribution(client_features: pd.DataFrame, client_product_features: pd.DataFrame):
    client_lift = client_features[["campaign_lift"]].copy()
    client_lift["feature_scope"] = "client"
    product_lift = client_product_features[["campaign_lift_product"]].rename(
        columns={"campaign_lift_product": "campaign_lift"}
    )
    product_lift["feature_scope"] = "client_product"

    combined = pd.concat([client_lift, product_lift], ignore_index=True)
    combined = _assign_clean_plot_column(
        combined,
        "campaign_lift",
        "_campaign_lift_plot",
        clip_range=CAMPAIGN_LIFT_CLIP_RANGE,
    )
    combined = _drop_missing_plot_rows(combined, ["_campaign_lift_plot"])
    if combined.empty:
        return empty_figure("Campaign Lift Distribution")

    return px.histogram(
        combined,
        x="_campaign_lift_plot",
        color="feature_scope",
        barmode="overlay",
        nbins=40,
        title="Campaign Lift Distribution",
        labels={"_campaign_lift_plot": "Campaign lift", "count": "Rows"},
    )


def build_product_growth_distribution(product_features: pd.DataFrame):
    if product_features.empty:
        return empty_figure("Product Growth Distribution")

    plot_frame = _assign_clean_plot_column(
        product_features,
        "product_growth_30d",
        "_product_growth_plot",
        clip_range=(-5.0, 5.0),
    )
    plot_frame = _drop_missing_plot_rows(plot_frame, ["_product_growth_plot"])

    return px.histogram(
        plot_frame,
        x="_product_growth_plot",
        nbins=40,
        title="Product Growth Distribution",
        labels={"_product_growth_plot": "Product growth 30d", "count": "Products"},
        hover_data=["product_id", "rolling_sales_30d"],
    )


def build_customer_stability_visualization(client_features: pd.DataFrame):
    if client_features.empty:
        return empty_figure("Customer Stability Visualization")

    plot_frame = client_features.copy()
    plot_frame["_marker_size"] = _safe_marker_size(plot_frame["customer_total_revenue"])
    plot_frame["_customer_frequency_plot"] = clean_feature_for_plot(
        plot_frame["customer_frequency_log1p"] if "customer_frequency_log1p" in plot_frame.columns else plot_frame["customer_frequency"]
    )
    plot_frame["_coefficient_variation_plot"] = clean_feature_for_plot(
        plot_frame["coefficient_variation_30d"],
        clip_range=COEFFICIENT_VARIATION_CLIP_RANGE,
    )
    plot_frame = _drop_missing_plot_rows(
        plot_frame,
        ["_customer_frequency_plot", "_coefficient_variation_plot"],
    )

    return px.scatter(
        plot_frame,
        x="_customer_frequency_plot",
        y="_coefficient_variation_plot",
        size="_marker_size",
        color="is_active_customer" if "is_active_customer" in plot_frame.columns else "days_since_last_order",
        title="Customer Stability Visualization",
        labels={
            "_customer_frequency_plot": "Customer frequency log1p",
            "_coefficient_variation_plot": "Coefficient variation 30d",
            "days_since_last_order": "Days since last order",
            "_marker_size": "Customer total revenue (clipped to >= 0)",
            "is_active_customer": "Active customer",
        },
        hover_data=["client_id", "customer_total_orders", "return_rate_30d", "campaign_lift"],
    )


def build_top_products_by_rolling_sales(product_features: pd.DataFrame, top_n: int = 15):
    if product_features.empty:
        return empty_figure("Top Products by Rolling Sales")

    top_products = _assign_clean_plot_column(
        product_features,
        "rolling_sales_30d",
        "_rolling_sales_plot",
    )
    top_products = _drop_missing_plot_rows(top_products, ["_rolling_sales_plot"])
    top_products = _top_k_frame(top_products, "_rolling_sales_plot", top_n)
    return px.bar(
        top_products,
        x="product_id",
        y="_rolling_sales_plot",
        title="Top Products by Rolling Sales",
        labels={"product_id": "Product", "_rolling_sales_plot": "Rolling sales 30d"},
        hover_data=["product_total_revenue", "product_growth_30d", "product_customer_count"],
    )


def build_customer_product_behavior_scatterplot(client_product_features: pd.DataFrame):
    if client_product_features.empty:
        return empty_figure("Customer-Product Behavior Scatterplot")

    plot_frame = client_product_features.copy()
    plot_frame["_marker_size"] = _safe_marker_size(
        clean_feature_for_plot(plot_frame["rolling_sales_30d"]).reindex(plot_frame.index)
    )
    plot_frame["_client_product_frequency_plot"] = clean_feature_for_plot(
        plot_frame["client_product_frequency"],
        log1p_transform=True,
    ).reindex(plot_frame.index)
    plot_frame["_avg_ticket_plot"] = clean_feature_for_plot(plot_frame["client_product_avg_ticket"]).reindex(
        plot_frame.index
    )
    plot_frame["_sales_growth_plot"] = clean_feature_for_plot(
        plot_frame["sales_growth_30d"],
        clip_range=(-5.0, 5.0),
    ).reindex(plot_frame.index)
    plot_frame = _drop_missing_plot_rows(
        plot_frame,
        ["_client_product_frequency_plot", "_avg_ticket_plot", "_sales_growth_plot"],
    )

    return px.scatter(
        plot_frame,
        x="_client_product_frequency_plot",
        y="_avg_ticket_plot",
        size="_marker_size",
        color="_sales_growth_plot",
        title="Customer-Product Behavior Scatterplot",
        labels={
            "_client_product_frequency_plot": "Client-product frequency log1p",
            "_avg_ticket_plot": "Client-product avg ticket",
            "_sales_growth_plot": "Sales growth 30d",
            "rolling_sales_30d": "Rolling sales 30d",
            "_marker_size": "Rolling sales 30d (clipped to >= 0)",
        },
        hover_data=[
            "client_id",
            "product_id",
            "client_product_total_revenue",
            "client_product_total_orders",
            "campaign_lift_product",
        ],
    )


def build_dashboard_figure(
    selected_plot: str,
    *,
    client_features: pd.DataFrame,
    product_features: pd.DataFrame,
    client_product_features: pd.DataFrame,
):
    if selected_plot == "Customer Frequency Distribution":
        return build_customer_frequency_distribution(client_features)
    if selected_plot == "Rolling Sales Trend Visualization":
        return build_rolling_sales_trend_visualization(product_features)
    if selected_plot == "Campaign Lift Distribution":
        return build_campaign_lift_distribution(client_features, client_product_features)
    if selected_plot == "Product Growth Distribution":
        return build_product_growth_distribution(product_features)
    if selected_plot == "Customer Stability Visualization":
        return build_customer_stability_visualization(client_features)
    if selected_plot == "Top Products by Rolling Sales":
        return build_top_products_by_rolling_sales(product_features)
    return build_customer_product_behavior_scatterplot(client_product_features)


def preview_table_for_plot(
    selected_plot: str,
    *,
    client_features: pd.DataFrame,
    product_features: pd.DataFrame,
    client_product_features: pd.DataFrame,
) -> pd.DataFrame:
    if selected_plot in {
        "Customer Frequency Distribution",
        "Campaign Lift Distribution",
        "Customer Stability Visualization",
    }:
        return client_features
    if selected_plot in {
        "Rolling Sales Trend Visualization",
        "Product Growth Distribution",
        "Top Products by Rolling Sales",
    }:
        return product_features
    return client_product_features
