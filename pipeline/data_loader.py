from pathlib import Path

import pandas as pd

from backend.data_processing.cleaning import (
    CAMPAIGN_COLUMNS,
    CLIENT_COLUMNS,
    POTENTIAL_COLUMNS,
    PRODUCT_COLUMNS,
    SALES_COLUMNS,
)


REQUIRED_RAW_COLUMNS = {
    "campaigns": tuple(CAMPAIGN_COLUMNS.keys()),
    "clients": tuple(CLIENT_COLUMNS.keys()),
    "potential": tuple(POTENTIAL_COLUMNS.keys()),
    "products": tuple(PRODUCT_COLUMNS.keys()),
    "sales": tuple(SALES_COLUMNS.keys()),
}


def _date_columns_for_dataset(columns: list[str], dataset: str) -> list[str]:
    if dataset == "campaigns":
        return [column for column in columns if any(token in column.lower() for token in ("date", "start", "end"))]
    if dataset == "sales":
        return [column for column in columns if "date" in column.lower()]
    return []


def _validate_raw_schema(dataset: str, columns: list[str]) -> None:
    expected_columns = REQUIRED_RAW_COLUMNS[dataset]
    missing_columns = [column for column in expected_columns if column not in columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Raw CSV '{dataset}.csv' is missing required columns: {missing}")


def load_raw_data(data_dir: str) -> dict[str, pd.DataFrame]:
    base_path = Path(data_dir)

    files = {
        "campaigns": base_path / "campaigns.csv",
        "clients": base_path / "clients.csv",
        "potential": base_path / "potential.csv",
        "products": base_path / "products.csv",
        "sales": base_path / "sales.csv",
    }

    missing_files = [str(path) for path in files.values() if not path.is_file()]
    if missing_files:
        missing_list = ", ".join(missing_files)
        raise FileNotFoundError(f"Missing required raw CSV files: {missing_list}")

    raw_data: dict[str, pd.DataFrame] = {}
    for dataset, file_path in files.items():
        header_columns = pd.read_csv(file_path, nrows=0).columns.tolist()
        _validate_raw_schema(dataset, header_columns)
        parse_dates = _date_columns_for_dataset(header_columns, dataset)
        raw_data[dataset] = pd.read_csv(
            file_path,
            parse_dates=parse_dates or None,
            low_memory=False,
        )

    return raw_data
