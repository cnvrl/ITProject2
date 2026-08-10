from __future__ import annotations

from collections.abc import Iterable

from app.models.tc_record import TCRecord


class FilterService:
    @staticmethod
    def apply(
        records: Iterable[TCRecord],
        *,
        models: list[str] | None = None,
        trackers: list[str] | None = None,
        scenarios: list[str] | None = None,
        regions: list[str] | None = None,
        year_min: int | None = None,
        year_max: int | None = None,
        minimum_category: int = 0,
    ) -> list[TCRecord]:
        selected = []

        for record in records:
            if models and record.model not in models:
                continue
            if trackers and record.tracker not in trackers:
                continue
            if scenarios and record.scenario not in scenarios:
                continue
            if regions and record.region not in regions:
                continue
            if year_min is not None and (record.year is None or record.year < year_min):
                continue
            if year_max is not None and (record.year is None or record.year > year_max):
                continue
            if (record.max_category or 0) < minimum_category:
                continue
            selected.append(record)

        return selected