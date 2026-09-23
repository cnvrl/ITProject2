from __future__ import annotations

from typing import Sequence

import pandas as pd

from app.models.tc_record import TCRecord
from app.services.audit_service import audit_track


def build_track_longevity(records: Sequence[TCRecord]) -> pd.DataFrame:
    """Extract detailed longevity, pressure, and audit summary metrics per track."""
    rows: list[dict] = []

    for record in records:
        winds = [p.wind_speed for p in record.points if p.wind_speed is not None]
        pressures = [p.pressure for p in record.points if p.pressure is not None]

        audit_res = audit_track(record)
        duration_hours = record.lifetime_hours or 0.0

        rows.append({
            "track_id": record.track_id,
            "raw_track_id": record.metadata.get("raw_track_id", record.track_id),
            "dataset": record.dataset,
            "driving_model": record.source_model,
            "tracker": record.tracker,
            "scenario": record.scenario,
            "season": record.season,
            "n_points": len(record.points),
            "duration_hours": duration_hours,
            "duration_days": duration_hours / 24.0,
            "max_wind_speed_kmh": max(winds) if winds else 0.0,
            "mean_wind_speed_kmh": sum(winds) / len(winds) if winds else 0.0,
            "min_pressure_hpa": min(pressures) if pressures else None,
            "mean_pressure_hpa": sum(pressures) / len(pressures) if pressures else None,
            "max_translation_speed_kmh": audit_res["max_translation_speed_kmh"],
            "suspicious_jump": audit_res["suspicious_jump"],
            "weak_tail": audit_res["weak_long_lived_tail"],
            "very_few_points": audit_res["very_few_points"],
            "is_flagged": audit_res["is_flagged"],
        })

    return pd.DataFrame(rows)


def summarize_longevity(longevity_df: pd.DataFrame) -> pd.DataFrame:
    """Group track longevity metrics by driving model."""
    if longevity_df.empty:
        return pd.DataFrame()

    return longevity_df.groupby("driving_model").agg(
        track_count=("track_id", "count"),
        mean_duration_days=("duration_days", "mean"),
        median_duration_days=("duration_days", "median"),
        max_duration_days=("duration_days", "max"),
        mean_wind_kmh=("mean_wind_speed_kmh", "mean"),
        max_wind_kmh=("max_wind_speed_kmh", "max"),
        min_pressure_hpa=("min_pressure_hpa", "min"),
        flagged_tracks=("is_flagged", "sum"),
    ).reset_index()