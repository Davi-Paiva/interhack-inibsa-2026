from __future__ import annotations

import calendar

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def _daily_sales_frame(sales: pd.DataFrame) -> pd.DataFrame:
    daily = (
        sales.groupby("sale_date", as_index=False)
        .agg(total_amount=("amount", "sum"), is_campaign_period=("is_campaign_period", "max"))
        .sort_values("sale_date")
    )
    daily["rolling_mean"] = daily["total_amount"].rolling(window=7, min_periods=1).mean()
    daily["rolling_std"] = daily["total_amount"].rolling(window=7, min_periods=2).std()
    daily["rolling_std"] = daily["rolling_std"].fillna(0.0)
    return daily


def plot_daily_sales_time_series(sales: pd.DataFrame) -> go.Figure:
    daily = _daily_sales_frame(sales)
    fig = px.line(daily, x="sale_date", y="total_amount", title="Daily sales")
    fig.update_layout(xaxis_title="Date", yaxis_title="Amount")
    return fig


def plot_rolling_mean_std(sales: pd.DataFrame) -> go.Figure:
    daily = _daily_sales_frame(sales)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=daily["sale_date"], y=daily["total_amount"], mode="lines", name="Daily sales")
    )
    fig.add_trace(
        go.Scatter(x=daily["sale_date"], y=daily["rolling_mean"], mode="lines", name="Rolling mean")
    )
    fig.add_trace(
        go.Scatter(x=daily["sale_date"], y=daily["rolling_std"], mode="lines", name="Rolling std")
    )
    fig.update_layout(
        title="Rolling mean and rolling std",
        xaxis_title="Date",
        yaxis_title="Amount",
    )
    return fig


def plot_campaign_impact_overlay(sales: pd.DataFrame) -> go.Figure:
    daily = _daily_sales_frame(sales)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=daily["sale_date"], y=daily["total_amount"], mode="lines", name="Daily sales")
    )

    campaign_days = daily.loc[daily["is_campaign_period"]]
    fig.add_trace(
        go.Scatter(
            x=campaign_days["sale_date"],
            y=campaign_days["total_amount"],
            mode="markers",
            name="Campaign period",
            marker={"size": 8},
        )
    )
    fig.update_layout(
        title="Campaign impact overlay",
        xaxis_title="Date",
        yaxis_title="Amount",
    )
    return fig


def plot_monthly_contextual_boxplot(sales: pd.DataFrame) -> go.Figure:
    monthly = sales.copy()
    monthly["month_name"] = monthly["month"].map(lambda value: calendar.month_abbr[int(value)])
    fig = px.box(
        monthly,
        x="month_name",
        y="amount",
        color="is_campaign_period",
        title="Monthly contextual boxplot",
        category_orders={"month_name": list(calendar.month_abbr[1:])},
    )
    fig.update_layout(xaxis_title="Month", yaxis_title="Amount")
    return fig


def plot_weekday_month_heatmap(sales: pd.DataFrame) -> go.Figure:
    heatmap = (
        sales.groupby(["month", "weekday"], as_index=False)
        .agg(total_amount=("amount", "sum"))
        .pivot(index="weekday", columns="month", values="total_amount")
        .fillna(0.0)
    )
    heatmap = heatmap.reindex(index=range(7), columns=range(1, 13), fill_value=0.0)

    fig = px.imshow(
        heatmap,
        labels={"x": "Month", "y": "Weekday", "color": "Amount"},
        x=[calendar.month_abbr[month] for month in heatmap.columns],
        y=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        title="Heatmap by weekday/month",
        aspect="auto",
    )
    return fig
