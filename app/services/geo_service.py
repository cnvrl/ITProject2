from __future__ import annotations

from typing import Iterable

from app.models.tc_record import TCRecord


class GeoService:
    @staticmethod
    def track_geojson(records: Iterable[TCRecord]) -> dict:
        features = []

        for record in records:
            if len(record.points) < 2:
                continue

            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "track_id": record.track_id,
                        "dataset_id": record.dataset_id,
                        "model": record.model,
                        "tracker": record.tracker,
                        "scenario": record.scenario,
                        "year": record.year,
                        "max_category": record.max_category,
                        "max_wind_speed": record.max_wind_speed,
                        "landfall": record.landfall,
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [point.lon, point.lat] for point in record.points
                        ],
                    },
                }
            )

        return {"type": "FeatureCollection", "features": features}

    @staticmethod
    def genesis_geojson(records: Iterable[TCRecord]) -> dict:
        features = []

        for record in records:
            if record.genesis_lat is None or record.genesis_lon is None:
                continue

            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "track_id": record.track_id,
                        "model": record.model,
                        "tracker": record.tracker,
                        "year": record.year,
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [record.genesis_lon, record.genesis_lat],
                    },
                }
            )

        return {"type": "FeatureCollection", "features": features}