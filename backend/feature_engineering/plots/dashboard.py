from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st

FEATURE_ENGINEERING_DIR = Path(__file__).resolve().parents[1]
if str(FEATURE_ENGINEERING_DIR) not in sys.path:
    sys.path.insert(0, str(FEATURE_ENGINEERING_DIR))

try:
    from ..config import FeatureConfig
    from .plots import (
        available_filter_options,
        build_dashboard_figure,
        feature_file_paths,
        filter_client_features,
        filter_client_product_features,
        filter_product_features,
        load_historical_feature_tables,
        PLOT_NAMES,
        preview_table_for_plot,
    )
except (ImportError, ValueError):
    from config import FeatureConfig
    from plots import (
        available_filter_options,
        build_dashboard_figure,
        feature_file_paths,
        filter_client_features,
        filter_client_product_features,
        filter_product_features,
        load_historical_feature_tables,
        PLOT_NAMES,
        preview_table_for_plot,
    )


@st.cache_data(show_spinner=False)
def _load_tables() -> dict:
    return load_historical_feature_tables()


def _required_paths_exist() -> bool:
    paths = feature_file_paths(config=FeatureConfig(), mode="historical")
    return all(path.exists() for path in paths.values())


def _render_sidebar(client_features, product_features) -> dict:
    filter_options = available_filter_options(client_features, product_features)

    st.sidebar.header("Navigation")
    selected_plot = st.sidebar.radio("View", PLOT_NAMES)

    st.sidebar.header("Filters")
    selected_clients = st.sidebar.multiselect(
        "Clients",
        options=filter_options["client_ids"],
        default=[],
    )
    selected_products = st.sidebar.multiselect(
        "Products",
        options=filter_options["product_ids"],
        default=[],
    )

    client_revenue_max = float(client_features["customer_total_revenue"].max()) if not client_features.empty else 0.0
    product_rolling_max = float(product_features["rolling_sales_30d"].max()) if not product_features.empty else 0.0

    revenue_range = st.sidebar.slider(
        "Customer revenue range",
        min_value=0.0,
        max_value=max(client_revenue_max, 1.0),
        value=(0.0, max(client_revenue_max, 1.0)),
    )
    rolling_sales_range = st.sidebar.slider(
        "Product rolling sales range",
        min_value=0.0,
        max_value=max(product_rolling_max, 1.0),
        value=(0.0, max(product_rolling_max, 1.0)),
    )

    return {
        "selected_plot": selected_plot,
        "selected_clients": selected_clients,
        "selected_products": selected_products,
        "revenue_range": revenue_range,
        "rolling_sales_range": rolling_sales_range,
    }


def main() -> None:
    st.set_page_config(page_title="Feature Engineering Dashboard", layout="wide")
    st.title("Feature Engineering Dashboard")
    st.caption("Historical feature validation and debugging for the Commodity AI Engine.")

    if not _required_paths_exist():
        paths = feature_file_paths(config=FeatureConfig(), mode="historical")
        st.warning("Historical feature CSV files were not found.")
        st.code("\n".join(str(path) for path in paths.values()))
        return

    tables = _load_tables()
    client_features = tables["client_features"]
    product_features = tables["product_features"]
    client_product_features = tables["client_product_features"]

    sidebar_state = _render_sidebar(client_features, product_features)

    filtered_client_features = filter_client_features(
        client_features,
        selected_clients=sidebar_state["selected_clients"],
        revenue_range=sidebar_state["revenue_range"],
    )
    filtered_product_features = filter_product_features(
        product_features,
        selected_products=sidebar_state["selected_products"],
        rolling_sales_range=sidebar_state["rolling_sales_range"],
    )
    filtered_client_product_features = filter_client_product_features(
        client_product_features,
        selected_clients=sidebar_state["selected_clients"],
        selected_products=sidebar_state["selected_products"],
    )

    st.metric("Client features", len(filtered_client_features))
    st.metric("Product features", len(filtered_product_features))
    st.metric("Client-product features", len(filtered_client_product_features))

    selected_plot = sidebar_state["selected_plot"]
    figure = build_dashboard_figure(
        selected_plot,
        client_features=filtered_client_features,
        product_features=filtered_product_features,
        client_product_features=filtered_client_product_features,
    )

    st.plotly_chart(figure, use_container_width=True)

    with st.expander("Filtered data preview"):
        preview_table = preview_table_for_plot(
            selected_plot,
            client_features=filtered_client_features,
            product_features=filtered_product_features,
            client_product_features=filtered_client_product_features,
        )
        st.dataframe(preview_table.head(50), use_container_width=True)


if __name__ == "__main__":
    main()
