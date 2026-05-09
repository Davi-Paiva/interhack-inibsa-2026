from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_csv_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required CSV input was not found: {path}")
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("utf-8", b"", 0, 1, f"Could not decode {path}")


def write_csv_frame(df: pd.DataFrame, output_path: Path) -> Path:
    ensure_directory(output_path.parent)
    df.to_csv(output_path, index=False)
    return output_path


def write_json(payload: dict, output_path: Path) -> Path:
    ensure_directory(output_path.parent)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    return output_path
