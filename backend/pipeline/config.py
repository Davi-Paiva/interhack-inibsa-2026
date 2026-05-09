from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
RAW_DIR = BACKEND_DIR / "data" / "raw"
CLEAN_DIR = BACKEND_DIR / "data" / "cleaned"
MODEL_READY_DIR = BACKEND_DIR / "data" / "model_ready"
REPORT_JSON_PATH = CLEAN_DIR / "basic_cleaning_summary.json"
REPORT_MD_PATH = CLEAN_DIR / "basic_cleaning_summary.md"
MODEL_REPORT_JSON_PATH = MODEL_READY_DIR / "model_ready_summary.json"
MODEL_REPORT_MD_PATH = MODEL_READY_DIR / "model_ready_summary.md"


TABLE_CONFIG = {
    "campaigns": {
        "rename": {
            "campana": "campaign",
            "fecha_inicio": "start_date",
            "fecha_fin": "end_date",
        },
        "date_columns": ["start_date", "end_date"],
        "numeric_columns": {},
        "id_columns": [],
    },
    "clients": {
        "rename": {
            "id_cliente": "client_id",
            "unnamed_1": "postal_code",
            "provincia": "province",
        },
        "date_columns": [],
        "numeric_columns": {},
        "id_columns": ["client_id", "postal_code"],
    },
    "potential": {
        "rename": {
            "id_cliente": "client_id",
            "familia": "potential_family",
            "categoria_productos": "product_category",
            "potencial": "potential_value",
        },
        "date_columns": [],
        "numeric_columns": {"potential_value": "float"},
        "id_columns": ["client_id"],
    },
    "products": {
        "rename": {
            "id_prod": "product_id",
            "bloque_analitico": "analytical_block",
            "categoria": "product_category",
            "familia": "product_family",
        },
        "date_columns": [],
        "numeric_columns": {},
        "id_columns": ["product_id"],
    },
    "sales": {
        "rename": {
            "num_fact": "invoice_id",
            "fecha": "date",
            "id_cliente": "client_id",
            "id_producto": "product_id",
            "unidades": "units",
            "valores": "value",
        },
        "date_columns": ["date"],
        "numeric_columns": {"units": "int", "value": "float"},
        "id_columns": ["invoice_id", "client_id", "product_id"],
    },
}


NEXT_CLEANSING_TECHNIQUES = [
    "Reconcile sales client IDs that do not exist in the client master before modeling customer-level behavior.",
    "Validate and refine the current working assumption that negative sales lines are refunds and zero-value or zero-unit lines are non-purchase administrative records.",
    "Audit duplicate customer-master rows and resolve whether they are true duplicates or conflicting records with different postal codes or provinces.",
    "Detect extraordinary orders, campaign uplift, and promotion effects so expected consumption is not inflated by one-off spikes.",
    "Create a stable product-family mapping layer for substitutions and portfolio changes, especially for technical products.",
    "Add daily data-quality checks for schema drift, null spikes, invalid dates, and cross-table key mismatches.",
]


WORKING_ASSUMPTIONS = [
    "Negative-value or negative-unit sales lines are treated as refund signals in the basic cleaned layer.",
    "Zero-value or zero-unit sales lines are retained but flagged as non-purchase signals instead of regular demand.",
    "Campaign windows are preserved and linked to sales rows so campaign behavior remains usable for customer-type detection.",
]