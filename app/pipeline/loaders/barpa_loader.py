"""
barpa_loader.py

The BARPA loader is responsible for loading cyclone track data from BARPA/CCAM CSV files into TCRecord objects. It handles parsing of timestamps, grouping of points into tracks and segments, and conversion of wind speed units. The loader also derives metadata such as model, tracker, season, and segment number for each track.

Class: BARPALoader(BaseTCLoader)
    - Inherits from BaseTCLoader and implements the load() method to read BARPA/CCAM CSV files.
    - Parses timestamps, normalizes row data, and converts values to appropriate types.
    - Groups points by model, tracker, season, and raw track ID, and segments tracks based on time gaps.
    - Returns a list of TCRecord objects representing the cyclone tracks.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from typing import Any

from app.models.tc_record import TCPoint, TCRecord
from app.pipeline.loaders.base import BaseTCLoader


class BARPALoader(BaseTCLoader):
    @staticmethod
    def parse_time(value: str) -> datetime:
        value = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y%m%d %H%M",
            ):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    pass
        raise ValueError(f"Unsupported timestamp: {value}")

    def load(self) -> list[TCRecord]:
        grouped: dict[tuple[str, str, str, str], list[TCPoint]] = defaultdict(list)

        with self.source_file.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)

            for raw_row in reader:
                row = self.normalize_row(raw_row)

                raw_track_id = (
                    row.get("trackid")
                    or row.get("track_id")
                    or row.get("stormid")
                    or row.get("tcid")
                )
                time_text = row.get("time")
                lat = self.to_float(row.get("lat") or row.get("latitude"))
                lon = self.to_float(row.get("lon") or row.get("longitude"))

                if not raw_track_id or not time_text or lat is None or lon is None:
                    continue

                try:
                    point_time = self.parse_time(time_text)
                except ValueError:
                    continue

                model = row.get("model") or "BARPA"
                tracker = row.get("tracker") or (
                    "CDD" if "cdd" in self.source_file.name.lower() else "TE"
                )
                season = row.get("season") or str(point_time.year)

                raw_wind_speed = self.to_float(
                    row.get("wspd")
                    or row.get("wind_speed")
                    or row.get("windspeed")
                    or row.get("wind")
                )

                point = TCPoint(
                    time=point_time,
                    lat=lat,
                    lon=lon,
                    wind_speed=(
                        self.metres_per_second_to_kmh(raw_wind_speed)
                        if raw_wind_speed is not None
                        else None
                    ),
                    pressure=self.to_float(
                        row.get("pres")
                        or row.get("pressure")
                        or row.get("pmin")
                    ),
                    category=self.to_int(row.get("category")),
                    over_land=self.to_bool(
                        row.get("overland") or row.get("landfallflag")
                    ),
                )

                key = (str(model), str(tracker), str(season), str(raw_track_id))
                grouped[key].append(point)

        records: list[TCRecord] = []
        max_gap_hours = 48

        for (model, tracker, season, raw_track_id), points in grouped.items():
            points = sorted(points, key=lambda point: point.time)
            segments: list[list[TCPoint]] = []
            current_segment: list[TCPoint] = []

            for point in points:
                if current_segment:
                    previous_point = current_segment[-1]
                    gap_hours = (
                        point.time - previous_point.time
                    ).total_seconds() / 3600

                    if gap_hours > max_gap_hours:
                        segments.append(current_segment)
                        current_segment = []

                current_segment.append(point)

            if current_segment:
                segments.append(current_segment)

            for segment_number, segment in enumerate(segments, start=1):
                record_id = (
                    f"{self.dataset_id}"
                    f"|{model}"
                    f"|{tracker}"
                    f"|season-{season}"
                    f"|track-{raw_track_id}"
                    f"|segment-{segment_number}"
                )

                records.append(
                    self.build_record(
                        track_id=record_id,
                        points=segment,
                        model="BARPA",
                        tracker=tracker if tracker in {"CDD", "TE"} else None,
                        scenario="historical"
                        if model.upper() == "ERA5"
                        else "future",
                        region="Australia",
                        metadata={
                            "raw_track_id": raw_track_id,
                            "season": season,
                            "source_model_value": model,
                            "source_tracker_value": tracker,
                            "segment_number": segment_number,
                            "segment_gap_threshold_hours": max_gap_hours,
                            "wind_speed_source_unit": "m/s",
                            "wind_speed_standard_unit": "km/h",
                        },
                    )
                )

        return records