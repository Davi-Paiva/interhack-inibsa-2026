from __future__ import annotations

import json

import pandas as pd

from .config import CLEAN_DIR, MODEL_READY_DIR, MODEL_REPORT_JSON_PATH, MODEL_REPORT_MD_PATH, MODEL_READY_DIR, REPORT_JSON_PATH, REPORT_MD_PATH


def write_cleaned_tables(cleaned_tables: dict[str, pd.DataFrame]) -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    for table_name, df in cleaned_tables.items():
        df.to_csv(CLEAN_DIR / f"{table_name}.csv", index=False, encoding="utf-8-sig")


def write_reports(summary: dict[str, object]) -> None:
    REPORT_JSON_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Basic Cleaning Summary",
        "",
        "This basic pass aligns the raw files with the exercise brief by standardizing schema, types, and traceability before feature engineering.",
        "",
        "## Table Results",
        "",
        "| Table | Rows Before | Rows After | Duplicates Removed | Invalid Dates | Invalid Numeric |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]

    for table_name, table_report in summary["tables"].items():
        lines.append(
            "| {table} | {before} | {after} | {dupes} | {dates} | {numeric} |".format(
                table=table_name,
                before=table_report["rows_before"],
                after=table_report["rows_after"],
                dupes=table_report["duplicates_removed"],
                dates=table_report["invalid_dates"],
                numeric=table_report["invalid_numeric"],
            )
        )

    lines.extend([
        "",
        "## Working Assumptions Applied",
        "",
    ])

    for assumption in summary["working_assumptions"]:
        lines.append(f"- {assumption}")

    lines.extend([
        "",
        "## Sales Business Flags",
        "",
    ])

    for flag_name, flag_value in summary["sales_business_flags"].items():
        lines.append(f"- {flag_name}: {flag_value}")

    lines.extend([
        "",
        "## Cross-Table Checks",
        "",
    ])

    for check_name, check_data in summary["cross_table_checks"].items():
        lines.append(f"- {check_name}: {check_data['count']} mismatches. Sample: {check_data['sample']}")

    lines.extend([
        "",
        "## Next Cleansing Techniques",
        "",
    ])

    for technique in summary["next_cleansing_techniques"]:
        lines.append(f"- {technique}")

    REPORT_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_model_ready_tables(model_ready_tables: dict[str, pd.DataFrame]) -> None:
    MODEL_READY_DIR.mkdir(parents=True, exist_ok=True)
    for table_name, df in model_ready_tables.items():
        df.to_csv(MODEL_READY_DIR / f"{table_name}.csv", index=False, encoding="utf-8-sig")


def write_model_ready_report(model_ready_tables: dict[str, pd.DataFrame]) -> None:
    summary = {
        "model_ready_dir": str(MODEL_READY_DIR),
        "tables": {
            table_name: {
                "rows": int(len(df)),
                "columns": df.columns.tolist(),
            }
            for table_name, df in model_ready_tables.items()
        },
    }
    MODEL_REPORT_JSON_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Model Ready Summary",
        "",
        "These files are the shared minimal layer for immediate modeling and feature work.",
        "",
        "## Output Tables",
        "",
        "| File | Rows | Purpose |",
        "| --- | ---: | --- |",
        f"| client_dimension.csv | {len(model_ready_tables['client_dimension'])} | One row per client with essential geography and master-data flags. |",
        f"| product_dimension.csv | {len(model_ready_tables['product_dimension'])} | One row per product with normalized category, family, and commodity/technical type. |",
        f"| campaign_dimension.csv | {len(model_ready_tables['campaign_dimension'])} | Campaign windows preserved exactly for modeling and feature joins. |",
        f"| client_category_potential.csv | {len(model_ready_tables['client_category_potential'])} | Potential normalized to the shared client-category grain. |",
        f"| sales_transactions.csv | {len(model_ready_tables['sales_transactions'])} | Lean transaction-level fact table with purchase, refund, and campaign flags. |",
        f"| client_category_daily.csv | {len(model_ready_tables['client_category_daily'])} | Shared client-date-category base for daily signal modeling. |",
        f"| client_category_summary.csv | {len(model_ready_tables['client_category_summary'])} | Compact client-category summary for quick baseline models. |",
        "",
        "## Modeling Guidance",
        "",
        "- Read all identifier columns as strings.",
        "- Use client_category_daily.csv when you need temporal features or daily windows.",
        "- Use client_category_summary.csv for fast baseline experiments and segmentation.",
        "- Use sales_transactions.csv when you want custom aggregations or product-level feature engineering.",
    ]
    MODEL_REPORT_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")