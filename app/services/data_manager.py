from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from app.pipeline.ingest import Ingestor


class DataManager:
    def __init__(self, data_dir: str | Path = 'data') -> None:
        self.data_dir = Path(data_dir)
        self.ingestor = Ingestor()
        self.cache: dict[str, dict[str, Any]] = {}

    def list_datasets(self) -> list[str]:
        if not self.data_dir.exists():
            return []
        return sorted([p.name for p in self.data_dir.iterdir() if p.is_file()])

    def load_dataset(self, filename: str, dataset_type: Optional[str] = None, force_reload: bool = False, **context: Any) -> dict[str, Any]:
        cache_key = f'{dataset_type or "auto"}:{filename}'
        if not force_reload and cache_key in self.cache:
            return self.cache[cache_key]
        file_path = self.data_dir / filename
        result = self.ingestor.ingest(file_path, dataset_type=dataset_type, **context)
        self.cache[cache_key] = result
        return result

    def get_tracks(self, filename: str, dataset_type: Optional[str] = None, filters: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
        filters = filters or {}
        result = self.load_dataset(filename, dataset_type=dataset_type)
        records = result['records']
        filtered = []
        for record in records:
            if filters.get('model') and record.model != filters['model']:
                continue
            if filters.get('tracker') and record.tracker != filters['tracker']:
                continue
            if filters.get('scenario') and record.scenario != filters['scenario']:
                continue
            if filters.get('year_min') and (record.year is None or record.year < filters['year_min']):
                continue
            if filters.get('year_max') and (record.year is None or record.year > filters['year_max']):
                continue
            filtered.append(record.model_dump(mode='json'))
        return filtered

    def get_stats(self, filename: str, dataset_type: Optional[str] = None, filters: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        tracks = self.get_tracks(filename, dataset_type=dataset_type, filters=filters)
        if not tracks:
            return {
                'total_cyclones': 0,
                'landfall_count': 0,
                'max_category': None,
                'max_wind_speed': None,
                'year_range': None,
            }
        years = [t['year'] for t in tracks if t.get('year') is not None]
        max_categories = [t['max_category'] for t in tracks if t.get('max_category') is not None]
        max_winds = [t['max_wind_speed'] for t in tracks if t.get('max_wind_speed') is not None]
        return {
            'total_cyclones': len(tracks),
            'landfall_count': sum(1 for t in tracks if t.get('landfall')),
            'max_category': max(max_categories) if max_categories else None,
            'max_wind_speed': max(max_winds) if max_winds else None,
            'year_range': {
                'min': min(years),
                'max': max(years),
            } if years else None,
        }