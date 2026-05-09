# Data Processing

Small pandas-based cleaning module for preparing historical training data and daily incoming data.

## Structure

```text
data_processing
├── cleaning.py
├── config.py
├── utils.py
├── validation.py
├── run_cleaning.py
├── README.md
└── plots
    ├── plots.py
    └── dashboard.py
```

## What it does

- Reuses the same cleaning logic for `historical` and `daily` runs.
- Cleans raw CSV inputs from `backend/raw_data`.
- Normalizes column names across `sales`, `clients`, `products`, `campaigns`, and `potential`.
- Parses Spanish numeric formats safely.
- Parses dates safely with pandas.
- Enriches sales with product and client reference data.
- Merges sales with product, client, campaign, and potential context.
- Adds temporal features: `month`, `quarter`, `weekday`, `is_month_end`, `is_quarter_end`.
- Adds business flags: `is_campaign_period`, `is_return`.
- Tags contextual anomalies such as returns and amount outliers.
- Removes only corrupted rows with missing or invalid critical fields.
- Removes amount outliers that are not inside campaign periods.
- Filters a `Productos Técnicos` sales dataset ready for downstream analytics.
- Writes processed outputs as parquet and CSV under `backend/processed_data/<mode>/`.
- Saves lightweight monitoring metrics as JSON, including daily-vs-historical drift checks.
- Triggers downstream feature engineering after cleaning for historical runs.

## Run

```bash
pip install -r backend/data_processing/requirements.txt
python3 backend/data_processing/run_cleaning.py --mode historical
python3 backend/data_processing/run_cleaning.py --mode daily
python3 backend/feature_engineering/run_features.py --mode historical
streamlit run backend/data_processing/plots/dashboard.py
```

## Notes

- The pipeline expects `pandas` plus a parquet engine such as `pyarrow` or `fastparquet`.
- The cleaning flow now includes logging for load, cleaning, and output summary steps.
- Validation includes missing ratio, duplicate ratio, invalid date ratio, outlier ratio, and drift monitoring for daily runs when a historical baseline is available.
- The plots module reads processed parquet files and exposes a minimal Streamlit dashboard for `historical` and `daily` views.
- Feature engineering now lives in `backend/feature_engineering` and reads cleaned parquet outputs from this module.
- No modeling is included yet.
