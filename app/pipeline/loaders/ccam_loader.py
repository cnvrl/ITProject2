from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime

from app.models.tc_record import TCPoint
from app.pipeline.loaders.base import BaseTCLoader


class CCAMLoader(BaseTCLoader):
    def parse_time(self, value: str) -> datetime:
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
                    row.get('track_no')
                    or row.get('trackid')
                    or row.get('storm_id')
                    or row.get('track_id')
                )
                time_value = (row.get('time') or '').strip()
                lat_value = (row.get('latitude') or row.get('lat') or '').strip()
                lon_value = (row.get('longitude') or row.get('lon') or '').strip()

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
                            row.get('vmax') or row.get('wind_speed')
                        ),
                        pressure=self.to_float(row.get('pmin') or row.get('pressure')),
                        category=self.to_int(row.get('category')),
                        over_land=(
                            row.get('landfall_flag', '').strip().lower() in {'1', 'true', 'yes'}
                        ) if row.get('landfall_flag') is not None else None,
                    )
                )
        return [
            self.build_record(track_id=track_id, points=points, model='CCAM')
            for track_id, points in grouped.items()
            if points
        ]