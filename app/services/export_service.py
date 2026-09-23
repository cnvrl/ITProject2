from __future__ import annotations

import pandas as pd

from app.services.analysis_service import comparison_summary
from app.services.report_service import build_interpretation_report


EXPORT_COLUMNS = [
    "track_id",
    "name",
    "dataset",
    "driving_model",
    "raw_track_id",
    "season",
    "scenario",
    "region",
    "tracker",
    "year",
    "analysis_year",
    "max_category",
    "max_wind_speed",
    "lifetime_hours",
    "landfall",
    "genesis_date",
]


def filtered_export_frame(tracks: pd.DataFrame) -> pd.DataFrame:
    columns = [column for column in EXPORT_COLUMNS if column in tracks.columns]
    return tracks[columns].copy()


def interpretation_report(tracks: pd.DataFrame) -> str:
    return build_interpretation_report(comparison_summary(tracks))