from __future__ import annotations

from .cleaning import build_cross_table_checks, clean_all_tables, enrich_sales_with_business_flags
from .config import CLEAN_DIR, MODEL_READY_DIR, MODEL_REPORT_MD_PATH, NEXT_CLEANSING_TECHNIQUES, RAW_DIR, WORKING_ASSUMPTIONS
from .model_ready import build_model_ready_tables
from .reporting import write_cleaned_tables, write_model_ready_report, write_model_ready_tables, write_reports


def run_pipeline() -> dict[str, object]:
    cleaned_tables, table_reports = clean_all_tables()
    sales_business_flags = enrich_sales_with_business_flags(cleaned_tables)
    write_cleaned_tables(cleaned_tables)
    cross_table_checks = build_cross_table_checks(cleaned_tables)
    model_ready_tables = build_model_ready_tables(cleaned_tables)
    write_model_ready_tables(model_ready_tables)
    write_model_ready_report(model_ready_tables)

    summary = {
        "raw_dir": str(RAW_DIR),
        "clean_dir": str(CLEAN_DIR),
        "tables": table_reports,
        "working_assumptions": WORKING_ASSUMPTIONS,
        "sales_business_flags": sales_business_flags,
        "cross_table_checks": cross_table_checks,
        "next_cleansing_techniques": NEXT_CLEANSING_TECHNIQUES,
    }
    write_reports(summary)

    return {
        "summary": summary,
        "sales_business_flags": sales_business_flags,
        "cross_table_checks": cross_table_checks,
        "model_ready_tables": model_ready_tables,
    }


def main() -> None:
    result = run_pipeline()
    sales_business_flags = result["sales_business_flags"]
    cross_table_checks = result["cross_table_checks"]

    print(f"Cleaned files written to: {CLEAN_DIR}")
    print(f"Model-ready files written to: {MODEL_READY_DIR}")
    print(f"Model-ready summary written to: {MODEL_REPORT_MD_PATH}")
    print(f"refund_rows: {sales_business_flags['refund_rows']}")
    print(f"non_purchase_signal_rows: {sales_business_flags['non_purchase_signal_rows']}")
    print(f"campaign_period_rows: {sales_business_flags['campaign_period_rows']}")
    for check_name, check_data in cross_table_checks.items():
        print(f"{check_name}: {check_data['count']} mismatches")