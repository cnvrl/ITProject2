from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.data_manager import DataManager

router = APIRouter(prefix='/api', tags=['TC Explorer'])
data_manager = DataManager()


class TrackFilter(BaseModel):
    model: Optional[str] = None
    tracker: Optional[str] = None
    scenario: Optional[str] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None


@router.get('/health')
def health() -> dict:
    return {'status': 'ok'}


@router.get('/datasets')
def list_datasets() -> dict:
    return {'datasets': data_manager.list_datasets()}


@router.post('/tracks/{filename}')
def get_tracks(filename: str, filters: TrackFilter, dataset_type: Optional[str] = Query(default=None)) -> dict:
    try:
        tracks = data_manager.get_tracks(filename, dataset_type=dataset_type, filters=filters.model_dump(exclude_none=True))
        return {'filename': filename, 'count': len(tracks), 'tracks': tracks}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='Dataset file not found')
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get('/stats/{filename}')
def get_stats(filename: str, dataset_type: Optional[str] = Query(default=None), model: Optional[str] = None, tracker: Optional[str] = None, scenario: Optional[str] = None, year_min: Optional[int] = None, year_max: Optional[int] = None) -> dict:
    try:
        filters = {
            'model': model,
            'tracker': tracker,
            'scenario': scenario,
            'year_min': year_min,
            'year_max': year_max,
        }
        stats = data_manager.get_stats(filename, dataset_type=dataset_type, filters={k: v for k, v in filters.items() if v is not None})
        return {'filename': filename, 'stats': stats}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='Dataset file not found')
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))