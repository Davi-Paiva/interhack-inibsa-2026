from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from ..domain.structures import Alert


class DuplicateSuppressor:
    def suppress(self, alerts: Iterable[Alert]) -> list[Alert]:
        winners: dict[tuple[str, str, object], Alert] = {}
        suppressed: list[Alert] = []
        for alert in sorted(alerts, key=lambda item: item.priority_score, reverse=True):
            existing = winners.get(alert.dedupe_key)
            if existing is None:
                winners[alert.dedupe_key] = alert
                continue
            suppressed.append(
                replace(
                    alert,
                    suppressed=True,
                    suppression_reason=f"Lower priority duplicate of {existing.alert_id}",
                )
            )
        return list(winners.values()) + suppressed
