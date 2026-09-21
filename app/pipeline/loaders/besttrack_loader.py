"""
besttrack_loader.py

"""

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
        return datetime.fromisoformat(date_value.replace('Z', '+00:00'))

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
                    row.get('sid')
                    or row.get('storm_id')
                    or row.get('track_id')
                    or row.get('trackid')
                )
                date_value = (row.get('iso_time') or row.get('date') or '').strip()
                lat_value = (row.get('lat') or row.get('latitude') or '').strip()
                lon_value = (row.get('lon') or row.get('longitude') or '').strip()

                if not track_id or not date_value or not lat_value or not lon_value:
                    continue

                try:
                    parsed_time = self.parse_time(date_value, row.get('time'))
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
                            row.get('usa_wind') or row.get('wind_speed') or row.get('wind')
                        ),
                        pressure=self.to_float(
                            row.get('usa_pres') or row.get('pressure')
                        ),
                        category=self.to_int(row.get('category') or row.get('usa_sshs')),
                        over_land=(
                            row.get('landfall', '').strip().lower() in {'1', 'true', 'yes'}
                        ) if row.get('landfall') is not None else None,
                    )
                )
        return [
            self.build_record(track_id=track_id, points=points, data_source='real')
            for track_id, points in grouped.items()
            if points
        ]