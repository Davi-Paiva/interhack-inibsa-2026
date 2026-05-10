# Commodity AI Engine

Smart Demand Signals for the INIBSA hackathon platform.

## What It Does

This module now:
- reads the current processed tables from `backend/processed_data/<mode>/`
- clusters real commodity customers from `clients.csv`
- backtests a real next-30-day forecast from `sales_enriched.csv`
- scores demand leakage opportunities from forecast + feature outputs
- writes clustering, forecast, and evaluation artifacts under `backend/commodity-ai-engine/output/<mode>/`

## Inputs

Expected processed inputs:
- `clients.csv`
- `products.csv`
- `client_product_features.csv`
- `sales_enriched.csv`

Backward compatibility:
- legacy parquet feature tables are still accepted as fallback where applicable

## Run

```bash
python src/commodity_engine.py --mode historical --task clustering
python src/commodity_engine.py --mode historical --task forecast
python src/commodity_engine.py --mode historical --task leakage
python src/commodity_engine.py --mode historical --task capture
python src/commodity_engine.py --mode historical --task next_purchase
```

Available tasks:
- `clustering`
- `forecast`
- `evaluation`
- `leakage`
- `capture`
- `next_purchase`

## Outputs

Main artifacts:
- `cluster_assignments.parquet`
- `cluster_profiles.parquet`
- `consumption_forecast.parquet`
- `demand_leakage_signals.parquet`
- `capture_opportunities.parquet`
- `next_purchase_predictions.parquet`
- `metrics/cluster_metrics.json`
- `metrics/forecast_metrics.json`
- `metrics/forecast_backtest_predictions.parquet`
- `metrics/demand_leakage_metrics.json`
- `metrics/capture_opportunity_metrics.json`
- `metrics/next_purchase_metrics.json`

## Entry Points

Use these functions from code:
- `run_customer_clustering()`
- `run_model_evaluation()`
- `run_consumption_forecast()`
- `run_demand_leakage()`
- `run_capture_scoring()`
- `run_next_purchase_prediction()`

## Notes

- The schema source of truth remains `backend/data_processing/inibsa_feature_tables.xlsx`.
- `customer_frequency_log1p` and `is_active_customer` are treated as valid model extras on top of the Excel client contract.
- Real forecast evaluation is currently implemented for `historical` mode only.
