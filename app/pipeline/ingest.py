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
            'barpa': BARPALoader,
            'ccam': CCAMLoader,
            'cdd': CDDTrackerLoader,
            'te': TETrackerLoader,
            'besttrack': BestTrackLoader,
            'netcdf': NetCDFLoader,
        }

    def choose_loader(self, source_file: str | Path, dataset_type: str | None = None):
        path = Path(source_file)
        key = (dataset_type or '').lower().strip()
        if key in self.loader_map:
            return self.loader_map[key]
        suffix = path.suffix.lower()
        name = path.name.lower()
        if suffix in {'.nc', '.nc4', '.cdf'}:
            return NetCDFLoader
        if 'besttrack' in name or 'ibtracs' in name:
            return BestTrackLoader
        if 'barpa' in name and 'cdd' in name:
            return BARPALoader
        if 'barpa' in name and 'te' in name:
            return BARPALoader
        if 'ccam' in name and 'cdd' in name:
            return CCAMLoader
        if 'ccam' in name and 'te' in name:
            return CCAMLoader
        raise ValueError(f'Unable to determine loader for {path}')

    def ingest(self, source_file: str | Path, dataset_type: str | None = None, **context: Any) -> dict:
        path = Path(source_file)
        loader_cls = self.choose_loader(path, dataset_type)
        dataset_id = context.pop('dataset_id', path.stem)
        loader = loader_cls(dataset_id=dataset_id, source_file=path, **context)
        records = loader.load()
        records = standardize_records(records, source_file=path)
        validation = validate_records(records)
        return {
            'dataset_id': dataset_id,
            'source_file': str(path),
            'loader': loader_cls.__name__,
            'records': records,
            'validation': validation,
        }