from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime

from app.models.tc_record import TCPoint
from app.pipeline.loaders.base import BaseTCLoader


class BARPALoader(BaseTCLoader):
    time_formats = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d %H:%M")

    def parse_time(self, value: str) -> datetime:
        for fmt in self.time_formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return datetime.fromisoformat(value.replace('Z', '+00:00'))

    @staticmethod
    def normalize_row(row: dict) -> dict:
        return {key.strip().lower(): value for key, value in row.items()}

    def load(self) -> list:
        grouped: dict[str, list[TCPoint]] = defaultdict(list)
        with self.source_file.open('r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for raw_row in reader:
                row = self.normalize_row(raw_row)

                track_id = (
                    row.get('track_id')
                    or row.get('trackid')
                    or row.get('storm_id')
                    or row.get('tc_id')
                )
                time_value = (row.get('time') or '').strip()
                lat_value = (row.get('lat') or row.get('latitude') or '').strip()
                lon_value = (row.get('lon') or row.get('longitude') or '').strip()

                if not track_id or not time_value or not lat_value or not lon_value:
                    continue

                try:
                    parsed_time = self.parse_time(time_value)
                    lat = float(lat_value)
                    lon = float(lon_value)
                except (ValueError, TypeError):
                    continue

                grouped[track_id].append(
                    TCPoint(
                        time=parsed_time,
                        lat=lat,
                        lon=lon,
                        wind_speed=self.to_float(
                            row.get('wind_speed') or row.get('wind') or row.get('wspd')
                        ),
                        pressure=self.to_float(row.get('pressure') or row.get('pres')),
                        category=self.to_int(row.get('category')),
                        over_land=(
                            row.get('over_land', '').strip().lower() in {'1', 'true', 'yes'}
                        ) if row.get('over_land') is not None else None,
                    )
                )
        return [
            self.build_record(track_id=track_id, points=points, model='BARPA')
            for track_id, points in grouped.items()
            if points
        ]