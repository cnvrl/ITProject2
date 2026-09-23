from __future__ import annotations

import math
from typing import Any

from app.models.tc_record import TCRecord


def haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Calculate Great Circle distance in kilometers using the Haversine formula."""
    r = 6371.0  # Earth radius in kilometers

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return r * c


def audit_track(
    record: TCRecord,
    speed_threshold_kmh: float = 80.0,
    tail_wind_threshold_ms: float = 17.0,
    tail_duration_days: float = 20.0,
    min_points: int = 4,
) -> dict[str, Any]:
    """Audit a cyclone record for synthetic tracking artifacts and speed anomalies."""
    n_points = len(record.points)
    very_few_points = n_points <= min_points

    max_speed_kmh = 0.0
    step_speeds: list[float] = []

    if n_points >= 2:
        for p1, p2 in zip(record.points[:-1], record.points[1:]):
            dist_km = haversine_km(p1.lat, p1.lon, p2.lat, p2.lon)
            if p1.timestamp is not None and p2.timestamp is not None:
                dt_hours = (p2.timestamp - p1.timestamp).total_seconds() / 3600.0
                if dt_hours > 0:
                    step_speeds.append(dist_km / dt_hours)

    if step_speeds:
        max_speed_kmh = max(step_speeds)

    suspicious_jump = max_speed_kmh > speed_threshold_kmh

    lifetime_days = (record.lifetime_hours or 0.0) / 24.0
    tail_wind_threshold_kmh = tail_wind_threshold_ms * 3.6

    weak_long_lived_tail = False
    if lifetime_days >= tail_duration_days and n_points >= 4:
        tail_slice = record.points[-max(1, n_points // 4):]
        tail_winds = [pt.wind_speed for pt in tail_slice if pt.wind_speed is not None]
        if tail_winds:
            avg_tail_wind = sum(tail_winds) / len(tail_winds)
            weak_long_lived_tail = avg_tail_wind < tail_wind_threshold_kmh

    is_flagged = suspicious_jump or weak_long_lived_tail or very_few_points

    return {
        "track_id": record.track_id,
        "n_points": n_points,
        "lifetime_days": lifetime_days,
        "max_translation_speed_kmh": max_speed_kmh,
        "suspicious_jump": suspicious_jump,
        "weak_long_lived_tail": weak_long_lived_tail,
        "very_few_points": very_few_points,
        "is_flagged": is_flagged,
    }