"""
ingest.py
The Ingestor class is responsible for determining the appropriate loader for a given dataset file and loading the cyclone track data into TCRecord objects. It supports various dataset types and file formats, including CSV and NetCDF. The ingestor also standardizes the loaded records and validates them before returning the final result.

class: Ingestor
    - Determines the appropriate loader based on the dataset type or file name.
    - Loads the cyclone track data using the selected loader.
    - Standardizes the loaded records and validates them.
    - Returns a dictionary containing the dataset ID, source file path, loader name, loaded records, and validation results.
    - Raises FileNotFoundError if the source file does not exist.
    - Raises ValueError if the loader cannot be determined for the given source file.

    General Usage:
        ingestor = Ingestor()
        result = ingestor.ingest(source_file="path/to/dataset.csv", dataset_type="barpa", dataset_id="my_dataset")
        records = result["records"]
        validation = result["validation"]
    
    Returns:
        A dictionary containing:
            - dataset_id: The ID of the dataset.
            - source_file: The path to the source file.
            - loader: The name of the loader class used.
            - records: A list of TCRecord objects representing the cyclone tracks.
            - validation: A dictionary containing validation results for the loaded records.
    
        

"""
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