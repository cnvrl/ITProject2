from __future__ import annotations

from collections import Counter
from statistics import mean, median
from typing import Iterable

from app.models.tc_record import TCRecord


class StatsEngine:
    @staticmethod
    def summary(records: Iterable[TCRecord]) -> dict:
        records = list(records)

        if not records:
            return {
                "total_cyclones": 0,
                "landfalls": 0,
                "frequency_by_year": {},
                "category_distribution": {},
                "average_lifetime_hours": None,
                "median_lifetime_hours": None,
                "average_max_wind_speed": None,
                "maximum_wind_speed": None,
                "average_translation_speed_kmh": None,
            }

        lifetimes = [
            record.lifetime_hours
            for record in records
            if record.lifetime_hours is not None
        ]
        winds = [
            record.max_wind_speed
            for record in records
            if record.max_wind_speed is not None
        ]
        speeds = [
            record.translation_speed_mean
            for record in records
            if record.translation_speed_mean is not None
        ]

        frequency = Counter(
            record.year for record in records if record.year is not None
        )
        categories = Counter(
            record.max_category if record.max_category is not None else 0
            for record in records
        )

        return {
            "total_cyclones": len(records),
            "landfalls": sum(record.landfall for record in records),
            "frequency_by_year": dict(sorted(frequency.items())),
            "category_distribution": dict(sorted(categories.items())),
            "average_lifetime_hours": mean(lifetimes) if lifetimes else None,
            "median_lifetime_hours": median(lifetimes) if lifetimes else None,
            "average_max_wind_speed": mean(winds) if winds else None,
            "maximum_wind_speed": max(winds) if winds else None,
            "average_translation_speed_kmh": mean(speeds) if speeds else None,
        }