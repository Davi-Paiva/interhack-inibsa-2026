from __future__ import annotations

import random
from collections import defaultdict

from ..domain.structures import Alert


def select_alerts(
    alerts: list[Alert],
    *,
    strategy: str = "ranked",
    limit: int | None = None,
    seed: int | None = None,
) -> list[Alert]:
    if strategy == "ranked":
        selected = sorted(
            alerts,
            key=lambda alert: (alert.suppressed, -alert.priority_score, alert.alert_id),
        )
    elif strategy == "random":
        selected = list(alerts)
        random.Random(seed).shuffle(selected)
    elif strategy == "balanced":
        selected = _balanced_selection(alerts, limit=limit, seed=seed)
    else:
        raise ValueError(f"Unsupported selection strategy: {strategy}")

    if limit is not None and strategy != "balanced":
        return selected[:limit]
    return selected


def _balanced_selection(
    alerts: list[Alert],
    *,
    limit: int | None,
    seed: int | None,
) -> list[Alert]:
    grouped: dict[str, list[Alert]] = defaultdict(list)
    for alert in alerts:
        grouped[alert.alert_type.value].append(alert)

    rng = random.Random(seed)
    group_keys = sorted(grouped)
    for key in group_keys:
        grouped[key] = list(grouped[key])
        rng.shuffle(grouped[key])

    interleaved: list[Alert] = []
    while group_keys and (limit is None or len(interleaved) < limit):
        next_keys: list[str] = []
        for key in group_keys:
            bucket = grouped[key]
            if not bucket:
                continue
            interleaved.append(bucket.pop())
            if bucket:
                next_keys.append(key)
            if limit is not None and len(interleaved) >= limit:
                break
        group_keys = next_keys
    return interleaved
