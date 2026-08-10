from __future__ import annotations

from pathlib import Path
from typing import Any

from app.pipeline.loaders.barpa_loader import BARPALoader
from app.pipeline.loaders.besttrack_loader import BestTrackLoader
from app.pipeline.loaders.ccam_loader import CCAMLoader
from app.pipeline.loaders.cdd_tracker_loader import CDDTrackerLoader
from app.pipeline.loaders.netcdf_loader import NetCDFLoader
from app.pipeline.loaders.te_tracker_loader import TETrackerLoader
from app.pipeline.standardize import standardize_records
from app.pipeline.validators import validate_records


class Ingestor:
    def __init__(self) -> None:
        self.loader_map = {
            "barpa": BARPALoader,
            "ccam": CCAMLoader,
            "cdd": CDDTrackerLoader,
            "te": TETrackerLoader,
            "besttrack": BestTrackLoader,
            "netcdf": NetCDFLoader,
        }

    def choose_loader(
        self,
        source_file: str | Path,
        dataset_type: str | None = None,
    ):
        path = Path(source_file)
        filename = path.name.lower()
        suffix = path.suffix.lower()
        key = (dataset_type or "").strip().lower()

        if key in self.loader_map:
            return self.loader_map[key]

        if suffix in {".nc", ".nc4", ".cdf"}:
            return NetCDFLoader
        if "ibtracs" in filename or "besttrack" in filename:
            return BestTrackLoader

        if "barpa" in filename:
            return BARPALoader
        if "ccam" in filename:
            return CCAMLoader
        if "cdd" in filename:
            return CDDTrackerLoader
        if "te" in filename:
            return TETrackerLoader

        raise ValueError(f"Unable to determine a loader for {path.name}")

    def ingest(
        self,
        source_file: str | Path,
        dataset_type: str | None = None,
        **context: Any,
    ) -> dict:
        path = Path(source_file)

        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {path}")

        loader_class = self.choose_loader(path, dataset_type)
        dataset_id = context.pop("dataset_id", path.stem)

        loader = loader_class(
            dataset_id=dataset_id,
            source_file=path,
            **context,
        )

        records = loader.load()
        records = standardize_records(records, source_file=path)
        validation = validate_records(records)

        return {
            "dataset_id": dataset_id,
            "source_file": str(path),
            "loader": loader_class.__name__,
            "records": records,
            "validation": validation,
        }