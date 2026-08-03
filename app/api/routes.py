"""API routes for TC-Explorer 2.0."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.services.data_manager import (
    available_sources,
    dataframe_to_csv,
    get_dataset,
)
from app.services.filter_service import apply_filters
from app.services.geo_service import to_feature_collection
from app.services.stats_engine import calculate_statistics


router = APIRouter()


def _filtered_dataset(
    *,
    regional_model: str,
    tracker: str,
    driving_model: str | None,
    start_season: int | None,
    end_season: int | None,
    min_wind: float | None,
    max_wind: float | None,
    min_lon: float | None,
    max_lon: float | None,
    min_lat: float | None,
    max_lat: float | None,
):
    try:
        frame = get_dataset(regional_model, tracker)
        return apply_filters(
            frame,
            driving_model=driving_model,
            start_season=start_season,
            end_season=end_season,
            min_wind=min_wind,
            max_wind=max_wind,
            min_lon=min_lon,
            max_lon=max_lon,
            min_lat=min_lat,
            max_lat=max_lat,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/health", tags=["Health"])
def health_check() -> dict:
    """Check the API and report availability of configured local data."""
    sources = available_sources()

    return {
        "status": (
            "healthy" if all(source["available"] for source in sources)
            else "degraded"
        ),
        "service": "TC-Explorer 2.0 API",
        "sources": sources,
    }


@router.get("/tracks", tags=["Tracks"])
def get_tracks(
    regional_model: Literal["BARPA", "CCAM"],
    tracker: Literal["CDD", "TE"],
    driving_model: str | None = None,
    start_season: int | None = Query(default=None, ge=1900, le=2200),
    end_season: int | None = Query(default=None, ge=1900, le=2200),
    min_wind: float | None = Query(default=None, ge=0),
    max_wind: float | None = Query(default=None, ge=0),
    min_lon: float | None = Query(default=None, ge=-180, le=360),
    max_lon: float | None = Query(default=None, ge=-180, le=360),
    min_lat: float | None = Query(default=None, ge=-90, le=90),
    max_lat: float | None = Query(default=None, ge=-90, le=90),
    limit: int = Query(default=250, ge=1, le=2000),
) -> dict:
    """Return filtered cyclone tracks as GeoJSON."""
    frame = _filtered_dataset(
        regional_model=regional_model,
        tracker=tracker,
        driving_model=driving_model,
        start_season=start_season,
        end_season=end_season,
        min_wind=min_wind,
        max_wind=max_wind,
        min_lon=min_lon,
        max_lon=max_lon,
        min_lat=min_lat,
        max_lat=max_lat,
    )

    try:
        return to_feature_collection(frame, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/stats", tags=["Statistics"])
def get_statistics(
    regional_model: Literal["BARPA", "CCAM"],
    tracker: Literal["CDD", "TE"],
    metric: Literal[
        "summary",
        "frequency",
        "intensity",
        "lifetime",
        "translation_speed",
    ] = "summary",
    driving_model: str | None = None,
    start_season: int | None = Query(default=None, ge=1900, le=2200),
    end_season: int | None = Query(default=None, ge=1900, le=2200),
    min_wind: float | None = Query(default=None, ge=0),
    max_wind: float | None = Query(default=None, ge=0),
    min_lon: float | None = Query(default=None, ge=-180, le=360),
    max_lon: float | None = Query(default=None, ge=-180, le=360),
    min_lat: float | None = Query(default=None, ge=-90, le=90),
    max_lat: float | None = Query(default=None, ge=-90, le=90),
) -> dict:
    """Return filtered statistical summaries."""
    frame = _filtered_dataset(
        regional_model=regional_model,
        tracker=tracker,
        driving_model=driving_model,
        start_season=start_season,
        end_season=end_season,
        min_wind=min_wind,
        max_wind=max_wind,
        min_lon=min_lon,
        max_lon=max_lon,
        min_lat=min_lat,
        max_lat=max_lat,
    )

    try:
        return calculate_statistics(frame, metric)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/export", tags=["Export"])
def export_data(
    regional_model: Literal["BARPA", "CCAM"],
    tracker: Literal["CDD", "TE"],
    driving_model: str | None = None,
    start_season: int | None = Query(default=None, ge=1900, le=2200),
    end_season: int | None = Query(default=None, ge=1900, le=2200),
    min_wind: float | None = Query(default=None, ge=0),
    max_wind: float | None = Query(default=None, ge=0),
    min_lon: float | None = Query(default=None, ge=-180, le=360),
    max_lon: float | None = Query(default=None, ge=-180, le=360),
    min_lat: float | None = Query(default=None, ge=-90, le=90),
    max_lat: float | None = Query(default=None, ge=-90, le=90),
    row_limit: int = Query(default=100_000, ge=1, le=500_000),
) -> Response:
    """Download filtered prepared records as CSV."""
    frame = _filtered_dataset(
        regional_model=regional_model,
        tracker=tracker,
        driving_model=driving_model,
        start_season=start_season,
        end_season=end_season,
        min_wind=min_wind,
        max_wind=max_wind,
        min_lon=min_lon,
        max_lon=max_lon,
        min_lat=min_lat,
        max_lat=max_lat,
    ).head(row_limit)

    csv_text = dataframe_to_csv(frame)
    filename = f"{regional_model.lower()}_{tracker.lower()}_filtered.csv"

    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )