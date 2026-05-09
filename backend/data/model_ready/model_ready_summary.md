# Model Ready Summary

These files are the shared minimal layer for immediate modeling and feature work.

## Output Tables

| File | Rows | Purpose |
| --- | ---: | --- |
| client_dimension.csv | 11037 | One row per client with essential geography and master-data flags. |
| product_dimension.csv | 25 | One row per product with normalized category, family, and commodity/technical type. |
| campaign_dimension.csv | 10 | Campaign windows preserved exactly for modeling and feature joins. |
| client_category_potential.csv | 22117 | Potential normalized to the shared client-category grain. |
| sales_transactions.csv | 162546 | Lean transaction-level fact table with purchase, refund, and campaign flags. |
| client_category_daily.csv | 107836 | Shared client-date-category base for daily signal modeling. |
| client_category_summary.csv | 26358 | Compact client-category summary for quick baseline models. |

## Modeling Guidance

- Read all identifier columns as strings.
- Use client_category_daily.csv when you need temporal features or daily windows.
- Use client_category_summary.csv for fast baseline experiments and segmentation.
- Use sales_transactions.csv when you want custom aggregations or product-level feature engineering.
