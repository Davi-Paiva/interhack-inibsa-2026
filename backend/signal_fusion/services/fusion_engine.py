from __future__ import annotations

from datetime import datetime
from typing import Iterable

from ..alarms import DEFAULT_ALARMS
from ..alarms.base import AlarmContext, AlarmGenerator
from ..domain.catalog import Catalog
from ..domain.structures import Alert, FusionTables
from .deduplication import DuplicateSuppressor
from .prioritizer import prioritize
from .routing import RoutingService
from .selection import select_alerts


class SignalFusionEngine:
    def __init__(
        self,
        alarms: Iterable[AlarmGenerator] = DEFAULT_ALARMS,
        router: RoutingService | None = None,
    ) -> None:
        self.alarms = tuple(alarms)
        self.router = router or RoutingService()
        self.suppressor = DuplicateSuppressor()

    def generate_alerts(
        self,
        tables: FusionTables,
        *,
        created_at: datetime | None = None,
        include_suppressed: bool = False,
        selection: str = "ranked",
        seed: int | None = None,
        top_n: int | None = None,
    ) -> list[Alert]:
        context = AlarmContext(
            catalog=Catalog(tables.products, tables.clients),
            router=self.router,
            created_at=created_at or datetime.utcnow(),
        )
        alerts: list[Alert] = []
        for alarm in self.alarms:
            alerts.extend(alarm.generate(tables, context))

        prioritized = [prioritize(alert) for alert in alerts]
        deduped = self.suppressor.suppress(prioritized)
        if not include_suppressed:
            deduped = [alert for alert in deduped if not alert.suppressed]
        return select_alerts(
            deduped,
            strategy=selection,
            limit=top_n,
            seed=seed,
        )
