from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime

from app.models.tc_record import TCPoint
from app.pipeline.loaders.base import BaseTCLoader


class BestTrackLoader(BaseTCLoader):
    def parse_time(self, date_value: str, time_value: str | None = None) -> datetime:
        if time_value:
            return datetime.strptime(f"{date_value}{time_value.zfill(4)}", "%Y%m%d%H%M")
        return datetime.fromisoformat(date_value)

    def load(self) -> list:
        grouped: dict[str, list[TCPoint]] = defaultdict(list)
        with self.source_file.open('r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                track_id = row.get('sid') or row.get('storm_id') or row.get('track_id')
                if not track_id:
                    continue
                grouped[track_id].append(
                    TCPoint(
                        time=self.parse_time(row.get('iso_time') or row.get('date'), row.get('time')),
                        lat=float(row['lat']),
                        lon=float(row['lon']),
                        wind_speed=self.to_float(row.get('usa_wind') or row.get('wind_speed') or row.get('wind')),
                        pressure=self.to_float(row.get('usa_pres') or row.get('pressure')),
                        category=self.to_int(row.get('category') or row.get('usa_sshs')),
                        over_land=(row.get('landfall', '').strip().lower() in {'1', 'true', 'yes'}) if row.get('landfall') is not None else None,
                    )
                )
        return [
            self.build_record(track_id=track_id, points=points, data_source='real')
            for track_id, points in grouped.items()
        ]