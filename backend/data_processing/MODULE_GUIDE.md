# Data Processing Module Guide

This document explains what each file inside `backend/data_processing` does and points to the most relevant code sections.

## `config.py`

Purpose:
Central configuration for paths, run modes, output folders, and shared pipeline defaults.

Key references:
- Run modes are defined in [config.py](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/config.py:8).
- The main configuration object is [ProcessingConfig](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/config.py:11).
- Input and output path resolution for `historical` and `daily` runs is handled in [sales_file_for_mode](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/config.py:26), [output_dir_for_mode](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/config.py:29), and [metrics_dir_for_mode](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/config.py:32).

## `utils.py`

Purpose:
Small reusable helpers for file loading, validation, parsing, and output writing.

Key references:
- CSV loading with fallback encodings lives in [read_csv](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/utils.py:10).
- Required-column checks are handled in [validate_required_columns](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/utils.py:25).
- Identifier and text normalization are in [normalize_identifier](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/utils.py:36) and [normalize_text](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/utils.py:40).
- Spanish numeric parsing is implemented in [parse_decimal_series](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/utils.py:44).
- Safe date parsing is implemented in [parse_datetime_series](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/utils.py:55).
- Output writing is split between [write_parquet_frame](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/utils.py:69) and [write_csv_frame](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/utils.py:84).

## `cleaning.py`

Purpose:
Core cleaning pipeline. This is the main module that loads raw data, cleans each dataset, merges context, creates business features, and writes processed outputs.

Key references:
- Raw-to-standard column mappings are defined at the top of the file in [SALES_COLUMNS](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/cleaning.py:47), [CLIENT_COLUMNS](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/cleaning.py:55), [PRODUCT_COLUMNS](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/cleaning.py:60), [CAMPAIGN_COLUMNS](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/cleaning.py:66), and [POTENTIAL_COLUMNS](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/cleaning.py:71).
- Removal of corrupted rows is handled in [_drop_corrupted_rows](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/cleaning.py:81).
- Deduplication for reference tables is handled in [_keep_latest_reference](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/cleaning.py:93).
- Temporal feature creation happens in [_add_temporal_features](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/cleaning.py:105).
- Campaign period tagging is implemented in [_add_campaign_flag](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/cleaning.py:115).
- Dataset merges plus `is_return`, anomaly tagging, and non-campaign outlier removal happen in [_merge_datasets](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/cleaning.py:126).
- Shared loading logic for both historical and daily runs is in [_load_raw_frames](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/cleaning.py:146).
- Per-dataset cleaning functions are [clean_sales](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/cleaning.py:163), [clean_clients](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/cleaning.py:181), [clean_products](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/cleaning.py:192), [clean_campaigns](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/cleaning.py:204), and [clean_potential](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/cleaning.py:219).
- The full in-memory processed datasets are assembled in [build_processed_frames](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/cleaning.py:239).
- Monitoring metrics are built in [build_monitoring_metrics](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/cleaning.py:280).
- Final output writing and orchestration are handled in [write_processed_frames](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/cleaning.py:334) and [run_cleaning_pipeline](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/cleaning.py:356).

## `validation.py`

Purpose:
Lightweight data quality and monitoring utilities for hackathon-ready robustness.

Key references:
- Ratio calculation helper is in [_safe_ratio](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/validation.py:14).
- Contextual anomaly tagging without deleting rows is implemented in [tag_amount_outliers](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/validation.py:20).
- Removal of amount outliers outside campaign periods is implemented in [remove_non_campaign_outliers](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/validation.py:50).
- Quality metrics such as missing ratio, duplicate ratio, invalid date ratio, and outlier ratio are computed in [build_quality_metrics](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/validation.py:51).
- Daily-vs-historical drift monitoring is implemented in [build_drift_metrics](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/validation.py:83).
- Metrics export to JSON is handled in [save_metrics_json](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/validation.py:119).

## `run_cleaning.py`

Purpose:
CLI entrypoint for executing the pipeline from the terminal.

Key references:
- Argument parsing is handled in [parse_args](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/run_cleaning.py:16).
- Runtime config overrides are handled in [build_config](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/run_cleaning.py:45).
- Logging setup, pipeline execution, and output summary printing happen in [main](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/run_cleaning.py:54).

## `plots/plots.py`

Purpose:
Interactive Plotly visualizations built only from processed data, without mixing plotting logic into cleaning.

Key references:
- Shared daily aggregation used by several charts is in [_daily_sales_frame](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/plots/plots.py:10).
- Daily sales time series is implemented in [plot_daily_sales_time_series](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/plots/plots.py:22).
- Rolling mean and rolling standard deviation are implemented in [plot_rolling_mean_std](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/plots/plots.py:29).
- Campaign impact overlay is implemented in [plot_campaign_impact_overlay](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/plots/plots.py:49).
- Monthly contextual boxplot is implemented in [plot_monthly_contextual_boxplot](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/plots/plots.py:74).
- Weekday-by-month heatmap is implemented in [plot_weekday_month_heatmap](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/plots/plots.py:89).

## `plots/dashboard.py`

Purpose:
Minimal Streamlit dashboard for exploring processed historical or daily sales data.

Key references:
- Processed parquet loading is handled in [load_processed_sales](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/plots/dashboard.py:30).
- The minimal UI and chart rendering live in [main](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/plots/dashboard.py:37).

## `requirements.txt`

Purpose:
Declares the minimal runtime dependencies for the module.

Current role:
- `pandas` and `pyarrow` support cleaning and parquet IO.
- `plotly` supports interactive figures.
- `streamlit` supports the dashboard.

## `README.md`

Purpose:
High-level entry document for setup, execution commands, and the current module scope.

Recommended use:
- Start with [README.md](/Users/joanvm/Desktop/Projects/Hackathon/InterHack26/interhack-inibsa-2026/backend/data_processing/README.md:1) for the quick run commands.
- Use this guide when you need to understand where a specific responsibility lives in the code.
