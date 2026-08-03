from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime

from app.models.tc_record import TCPoint
from app.pipeline.loaders.base import BaseTCLoader


class TETrackerLoader(BaseTCLoader):
    def parse_time(self, value: str) -> datetime:
        return datetime.fromisoformat(value)

    def load(self) -> list:
        grouped: dict[str, list[TCPoint]] = defaultdict(list)
        with self.source_file.open('r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                track_id = row.get('te_id') or row.get('track_id') or row.get('storm_id')
                if not track_id:
                    continue
                grouped[track_id].append(
                    TCPoint(
                        time=self.parse_time(row['time']),
                        lat=float(row['lat']),
                        lon=float(row['lon']),
                        wind_speed=self.to_float(row.get('wind') or row.get('wind_speed')),
                        pressure=self.to_float(row.get('pressure') or row.get('pmin')),
                        category=self.to_int(row.get('category')),
                    )
                )
        return [
            self.build_record(track_id=track_id, points=points, tracker='TE')
            for track_id, points in grouped.items()
        ]