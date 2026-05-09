from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from .plots import (
        plot_campaign_impact_overlay,
        plot_daily_sales_time_series,
        plot_monthly_contextual_boxplot,
        plot_rolling_mean_std,
        plot_weekday_month_heatmap,
    )
except ImportError:
    from plots import (
        plot_campaign_impact_overlay,
        plot_daily_sales_time_series,
        plot_monthly_contextual_boxplot,
        plot_rolling_mean_std,
        plot_weekday_month_heatmap,
    )


BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = BASE_DIR / "processed_data"


def load_processed_sales(mode: str) -> pd.DataFrame:
    sales_path = PROCESSED_DIR / mode / "sales_clean.parquet"
    sales = pd.read_parquet(sales_path)
    sales["sale_date"] = pd.to_datetime(sales["sale_date"], errors="coerce")
    return sales


def main() -> None:
    st.set_page_config(page_title="Data Processing Dashboard", layout="wide")
    st.title("Data Processing Dashboard")

    mode = st.sidebar.selectbox("Processed data", options=["historical", "daily"], index=0)
    sales = load_processed_sales(mode)

    st.caption(f"Source: {PROCESSED_DIR / mode / 'sales_clean.parquet'}")

    st.plotly_chart(plot_daily_sales_time_series(sales), use_container_width=True)
    st.plotly_chart(plot_rolling_mean_std(sales), use_container_width=True)
    st.plotly_chart(plot_campaign_impact_overlay(sales), use_container_width=True)
    st.plotly_chart(plot_monthly_contextual_boxplot(sales), use_container_width=True)
    st.plotly_chart(plot_weekday_month_heatmap(sales), use_container_width=True)


if __name__ == "__main__":
    main()
