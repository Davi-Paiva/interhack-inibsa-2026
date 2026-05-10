from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Any

from ..domain.structures import Alert


class AlertExporter:
    def write_json(self, alerts: Iterable[Alert], path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [self._to_dict(alert) for alert in alerts]
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
        return path

    def write_csv(self, alerts: Iterable[Alert], path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [self._to_flat_row(alert) for alert in alerts]
        if not rows:
            path.write_text("", encoding="utf-8")
            return path
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return path

    def _to_flat_row(self, alert: Alert) -> dict[str, Any]:
        row = self._to_dict(alert)
        row["explanation"] = " | ".join(row["explanation"])
        row["source_engines"] = " | ".join(row["source_engines"])
        row["evidence"] = json.dumps(row["evidence"], ensure_ascii=True)
        return row

    def _to_dict(self, alert: Alert) -> dict[str, Any]:
        return _serialize(asdict(alert))


def _serialize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value
