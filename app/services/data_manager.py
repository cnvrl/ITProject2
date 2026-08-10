from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from app.pipeline.ingest import Ingestor


class DataManager:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)
        self.ingestor = Ingestor()
        self.cache: dict[str, dict[str, Any]] = {}

    def list_datasets(self) -> list[str]:
        if not self.data_dir.exists():
            return []

        return sorted(
            path.name
            for path in self.data_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {".csv", ".txt", ".nc", ".nc4", ".cdf"}
        )

    @staticmethod
    def _infer_context(filename: str) -> dict[str, Any]:
        name = filename.lower()

        model = "BARPA" if "barpa" in name else "CCAM" if "ccam" in name else None
        tracker = "CDD" if "_cdd_" in name else "TE" if "_te_" in name else None

        if "ssp" in name:
            scenario = "future"
        elif "historical" in name or "era5" in name:
            scenario = "historical"
        else:
            scenario = None

        return {
            "data_source": "simulated",
            "model": model,
            "tracker": tracker,
            "scenario": scenario,
            "region": "Australia",
        }

    def load_dataset(
        self,
        filename: str,
        dataset_type: Optional[str] = None,
        force_reload: bool = False,
        **context: Any,
    ) -> dict[str, Any]:
        cache_key = f"{dataset_type or 'auto'}:{filename}"

        if not force_reload and cache_key in self.cache:
            return self.cache[cache_key]

        filepath = self.data_dir / filename

        result = self.ingestor.ingest(
            filepath,
            dataset_type=dataset_type,
            context=context,
        )

        validation = result.get("validation", {})
        valid_track_ids = set(validation.get("valid_track_ids", []))

        if result.get("records") and not valid_track_ids:
            result["records"] = []
        elif valid_track_ids:
            result["records"] = [
                record
                for record in result["records"]
                if record.track_id in valid_track_ids
            ]

        result["validation"]["records_returned_to_dashboard"] = len(
            result["records"]
        )

        self.cache[cache_key] = result
        return result

    def get_tracks(
        self,
        filename: str,
        dataset_type: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        filters = filters or {}
        records = self.load_dataset(filename, dataset_type=dataset_type)["records"]

        selected = []
        for record in records:
            if filters.get("model") and record.model != filters["model"]:
                continue
            if filters.get("tracker") and record.tracker != filters["tracker"]:
                continue
            if filters.get("scenario") and record.scenario != filters["scenario"]:
                continue

            year_min = filters.get("year_min")
            if year_min is not None and (record.year is None or record.year < year_min):
                continue

            year_max = filters.get("year_max")
            if year_max is not None and (record.year is None or record.year > year_max):
                continue

            selected.append(record.model_dump(mode="json"))

        return selected

    def get_stats(
        self,
        filename: str,
        dataset_type: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        tracks = self.get_tracks(filename, dataset_type, filters)

        if not tracks:
            return {
                "total_cyclones": 0,
                "landfall_count": 0,
                "max_category": None,
                "max_wind_speed": None,
                "year_range": None,
            }

        years = [track["year"] for track in tracks if track.get("year") is not None]
        categories = [
            track["max_category"]
            for track in tracks
            if track.get("max_category") is not None
        ]
        winds = [
            track["max_wind_speed"]
            for track in tracks
            if track.get("max_wind_speed") is not None
        ]

        return {
            "total_cyclones": len(tracks),
            "landfall_count": sum(bool(track.get("landfall")) for track in tracks),
            "max_category": max(categories) if categories else None,
            "max_wind_speed": max(winds) if winds else None,
            "year_range": {"min": min(years), "max": max(years)} if years else None,
        }