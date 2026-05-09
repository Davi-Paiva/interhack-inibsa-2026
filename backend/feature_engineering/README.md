# Feature Engineering

Lightweight pandas-based feature engineering for the Commodity AI Engine.

## Scope

- Reads processed parquet outputs from `backend/data_processing/`.
- Runs after the cleaning pipeline.
- Materializes only `historical` features today.
- Keeps the `daily` mode entrypoints and config ready for future incremental support.
- Focuses on behavioral features, aggregations, rolling metrics, and simple trend metrics.

## Structure

```text
feature_engineering
├── features.py
├── config.py
├── utils.py
├── run_features.py
├── README.md
├── plots
│   ├── plots.py
│   └── dashboard.py
└── metrics
    └── metrics.py
```

## Inputs

- Preferred cleaned input: `backend/processed_data/<mode>/sales_enriched.parquet`
- Current fallback input: `backend/processed_data/<mode>/sales_clean.parquet`

## Outputs

- Historical features:
  `backend/processed_data/historical/features/client_features.parquet`
- Historical features:
  `backend/processed_data/historical/features/product_features.parquet`
- Historical features:
  `backend/processed_data/historical/features/client_product_features.parquet`
- Historical metrics:
  `backend/processed_data/historical/features/metrics/feature_metrics.json`

## Current Features

- Client features for revenue, order behavior, recency, campaign lift, and stability
- Product features for revenue, units, frequency, rolling sales, growth, and return behavior
- Client-product features for rolling sales, growth, recency, campaign lift, and relationship strength

## Plots

- Customer frequency distribution
- Rolling sales trend visualization
- Campaign lift distribution
- Product growth distribution
- Customer stability visualization
- Top products by rolling sales
- Customer-product behavior scatterplot

## Run

```bash
pip install -r backend/data_processing/requirements.txt
python3 backend/data_processing/run_cleaning.py --mode historical
python3 backend/feature_engineering/run_features.py --mode historical
streamlit run backend/feature_engineering/plots/dashboard.py
```

## Notes

- `daily` mode is intentionally scaffolded but does not materialize features yet.
- TODOs are already included for daily incremental features, feature drift monitoring, and future feature store support.
- This module does not perform cleaning, anomaly detection, forecasting, embeddings, or ML modeling.
- The Streamlit dashboard is intended for feature validation, debugging, explainability, and hackathon demos.
