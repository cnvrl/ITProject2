"""

ccam_loader.py
The CCAM loader is responsible for loading cyclone track data from CCAM CSV files into TCRecord objects. It handles parsing of timestamps, grouping of points into tracks and segments, and conversion of wind speed units. The loader also derives metadata such as model, tracker, season, and segment number for each track.

class: CCAMLoader(BaseTCLoader)
    - Inherits from BaseTCLoader and implements the load() method to read CCAM CSV files.
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


class CCAMLoader(BaseTCLoader):

    MAX_GAP_HOURS = 48.0

    @staticmethod
    def parse_time(value: str) -> datetime:
        value = value.strip().replace("Z", "+00:00")

        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass

        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y%m%d %H%M",
        ):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue

        raise ValueError(f"Unsupported timestamp: {value}")

    @staticmethod
    def _source_truthy(value: Any) -> bool | None:
        if value is None:
            return None

        return str(value).strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
        }

    def _point_from_row(self, row: dict[str, Any]) -> TCPoint | None:
        time_text = row.get("time")
        lat = self.to_float(row.get("lat") or row.get("latitude"))
        lon = self.to_float(row.get("lon") or row.get("longitude"))

        if not time_text or lat is None or lon is None:
            return None

        try:
            point_time = self.parse_time(str(time_text))
        except ValueError:
            return None

        raw_wind_ms = self.to_float(
            row.get("wspd")
            or row.get("vmax")
            or row.get("wind_speed")
            or row.get("windspeed")
            or row.get("wind")
        )

        # Assumption: CCAM Wspd/Vmax is metres per second.
        # Confirm this against the CCAM dataset documentation when available.
        wind_kmh = (
            self.metres_per_second_to_kmh(raw_wind_ms)
            if raw_wind_ms is not None
            else None
        )

        return TCPoint(
            time=point_time,
            lat=lat,
            lon=lon,
            wind_speed=wind_kmh,
            pressure=self.to_float(
                row.get("pres")
                or row.get("pmin")
                or row.get("pressure")
            ),
            category=self.to_int(row.get("category")),
            over_land=self._source_truthy(
                row.get("overland")
                or row.get("landfallflag")
                or row.get("landfall")
            ),
        )

    def load(self) -> list[TCRecord]:
        grouped: dict[
            tuple[str, str, str, str],
            list[TCPoint],
        ] = defaultdict(list)

        filename = self.source_file.name.lower()
        inferred_tracker = (
            "CDD" if "cdd" in filename
            else "TE" if "te" in filename
            else None
        )
        inferred_scenario = "future" if "ssp" in filename else "historical"

        with self.source_file.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            reader = csv.DictReader(handle)

            for raw_row in reader:
                row = self.normalize_row(raw_row)

                raw_track_id = (
                    row.get("trackid")
                    or row.get("track_no")
                    or row.get("stormid")
                    or row.get("tcid")
                )

                if raw_track_id is None or str(raw_track_id).strip() == "":
                    continue

                point = self._point_from_row(row)
                if point is None:
                    continue

                source_model = str(row.get("model") or "CCAM").strip()
                tracker = str(
                    row.get("tracker") or inferred_tracker or "unknown"
                ).strip()

                # Season is distinct from calendar year for storms crossing
                # December/January. Use timestamp year only as a fallback.
                season = str(
                    row.get("season")
                    or row.get("tc_season")
                    or point.time.year
                ).strip()

                group_key = (
                    source_model,
                    tracker,
                    season,
                    str(raw_track_id).strip(),
                )
                grouped[group_key].append(point)

        records: list[TCRecord] = []

        for (
            source_model,
            tracker,
            season,
            raw_track_id,
        ), points in grouped.items():
            sorted_points = sorted(points, key=lambda point: point.time)

            segments: list[list[TCPoint]] = []
            current_segment: list[TCPoint] = []

            for point in sorted_points:
                if current_segment:
                    previous_time = current_segment[-1].time
                    gap_hours = (
                        point.time - previous_time
                    ).total_seconds() / 3600

                    if gap_hours > self.MAX_GAP_HOURS:
                        segments.append(current_segment)
                        current_segment = []

                current_segment.append(point)

            if current_segment:
                segments.append(current_segment)

            for segment_number, segment in enumerate(segments, start=1):
                record_id = (
                    f"{self.dataset_id}"
                    f"|CCAM"
                    f"|{tracker}"
                    f"|season-{season}"
                    f"|track-{raw_track_id}"
                    f"|segment-{segment_number}"
                )

                record = self.build_record(
                    track_id=record_id,
                    points=segment,
                    model="CCAM",
                    tracker=tracker if tracker in {"CDD", "TE"} else None,
                    scenario=inferred_scenario,
                    region="Australia",
                    metadata={
                        "raw_track_id": raw_track_id,
                        "season": season,
                        "source_model_value": source_model,
                        "source_tracker_value": tracker,
                        "segment_number": segment_number,
                        "segment_gap_threshold_hours": self.MAX_GAP_HOURS,
                        "wind_speed_source_unit": "m/s",
                        "wind_speed_standard_unit": "km/h",
                    },
                )

                records.append(record)

        return records