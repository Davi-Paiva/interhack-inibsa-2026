# Basic Cleaning Summary

This basic pass aligns the raw files with the exercise brief by standardizing schema, types, and traceability before feature engineering.

## Table Results

| Table | Rows Before | Rows After | Duplicates Removed | Invalid Dates | Invalid Numeric |
| --- | ---: | ---: | ---: | --- | --- |
| campaigns | 10 | 10 | 0 | {'start_date': 0, 'end_date': 0} | {} |
| clients | 11031 | 11001 | 30 | {} | {} |
| potential | 33093 | 33093 | 0 | {} | {'potential_value': 0} |
| products | 25 | 25 | 0 | {} | {} |
| sales | 162546 | 162546 | 0 | {'date': 0} | {'units': 0, 'value': 0} |

## Working Assumptions Applied

- Negative-value or negative-unit sales lines are treated as refund signals in the basic cleaned layer.
- Zero-value or zero-unit sales lines are retained but flagged as non-purchase signals instead of regular demand.
- Campaign windows are preserved and linked to sales rows so campaign behavior remains usable for customer-type detection.

## Sales Business Flags

- refund_rows: 3880
- zero_value_rows: 1456
- zero_unit_rows: 3339
- non_purchase_signal_rows: 3833
- campaign_period_rows: 6769
- campaigns_preserved: ['2021_1', '2022_1', '2022_2', '2023_1', '2023_2', '2024_1', '2024_2', '2024_3', '2024_4', '2025_1']

## Cross-Table Checks

- sales_client_ids_missing_in_clients: 34 mismatches. Sample: ['1000066400', '1000074005', '1000074435', '1000076519', '1000078435', '1000078639', '1000080774', '1000080938', '1000081089', '1000081162']
- potential_client_ids_missing_in_clients: 43 mismatches. Sample: ['1000066400', '1000074005', '1000074435', '1000074942', '1000076519', '1000077806', '1000078435', '1000078639', '1000079204', '1000079796']
- sales_product_ids_missing_in_products: 0 mismatches. Sample: []

## Next Cleansing Techniques

- Reconcile sales client IDs that do not exist in the client master before modeling customer-level behavior.
- Validate and refine the current working assumption that negative sales lines are refunds and zero-value or zero-unit lines are non-purchase administrative records.
- Audit duplicate customer-master rows and resolve whether they are true duplicates or conflicting records with different postal codes or provinces.
- Detect extraordinary orders, campaign uplift, and promotion effects so expected consumption is not inflated by one-off spikes.
- Create a stable product-family mapping layer for substitutions and portfolio changes, especially for technical products.
- Add daily data-quality checks for schema drift, null spikes, invalid dates, and cross-table key mismatches.
