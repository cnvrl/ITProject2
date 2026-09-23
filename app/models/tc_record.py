from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Optional
from app.config import SETTINGS

def coerce_datetime(value: object) -> Optional[datetime]:
    """Convert common timestamp values to datetime."""
    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        return value

    text = str(value).strip()
    if not text:
        return None

    normalised = text.replace("Z", "+00:00")

    try:
        return datetime.fromisoformat(normalised)
    except ValueError:
        pass

    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y%m%d%H",
        "%Y%m%d",
    )

    for timestamp_format in formats:
        try:
            return datetime.strptime(text, timestamp_format)
        except ValueError:
            continue

    return None


def optional_float(value: object) -> Optional[float]:
    if value is None or value == "":
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def optional_int(value: object) -> Optional[int]:
    if value is None or value == "":
        return None

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def is_australia_landfall(lat: float, lon: float) -> bool:
    """Check if latitude/longitude falls within Australian land boundaries."""
    return (
        (SETTINGS.aus_landfall_min_lat <= lat <= SETTINGS.aus_landfall_max_lat)
        and (SETTINGS.aus_landfall_min_lon <= lon <= SETTINGS.aus_landfall_max_lon)
    )

@dataclass
class TrackPoint:
    """One observation along a tropical cyclone track."""

    lat: float
    lon: float
    timestamp: Optional[datetime] = None
    wind_speed: Optional[float] = None
    pressure: Optional[float] = None
    category: Optional[int] = None
    step: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> TrackPoint:
        clean_map = {
            str(k).strip().lower(): v
            for k, v in values.items()
            if v is not None and str(v).strip() != "" and str(v).strip().lower() != "nan"
        }

        latitude = clean_map.get("lat") or clean_map.get("latitude")
        longitude = clean_map.get("lon") or clean_map.get("longitude") or clean_map.get("lng")

        if latitude is None or longitude is None:
            raise ValueError("Track points require latitude and longitude.")

        timestamp = (
            clean_map.get("timestamp")
            or clean_map.get("datetime")
            or clean_map.get("time")
            or clean_map.get("date")
        )

        wind_speed_raw = (
            clean_map.get("wspd")
            or clean_map.get("wind_speed")
            or clean_map.get("wind")
            or clean_map.get("vmax")
        )

        pressure_raw = (
            clean_map.get("pres")
            or clean_map.get("pressure")
            or clean_map.get("central_pressure")
        )

        return cls(
            lat=float(latitude),
            lon=float(longitude),
            timestamp=coerce_datetime(timestamp),
            wind_speed=optional_float(wind_speed_raw),
            pressure=optional_float(pressure_raw),
            category=optional_int(clean_map.get("category")),
            step=optional_int(clean_map.get("step")),
            metadata=dict(values),
        )


TCPoint = TrackPoint


@dataclass
class TCRecord:
    """Canonical tropical cyclone domain record."""

    dataset_id: str
    track_id: str
    model: str

    driving_model: Optional[str] = None
    tracker: str = "unknown"
    scenario: str = "unknown"
    region: str = "unknown"

    season: Optional[int] = None
    year: Optional[int] = None

    points: list[TrackPoint] = field(default_factory=list)

    max_category: Optional[int] = None
    max_wind_speed: Optional[float] = None
    lifetime_hours: Optional[float] = None
    landfall: bool = False

    genesis_lat: Optional[float] = None
    genesis_lon: Optional[float] = None
    genesis_time: Optional[datetime] = None

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def dataset(self) -> str:
        return str(
            self.model
            or self.metadata.get("dataset")
            or self.dataset_id
            or "unknown"
        ).strip().upper()

    @property
    def source_model(self) -> str:
        return str(
            self.driving_model
            or self.metadata.get("source_model_value")
            or self.metadata.get("driving_model")
            or "unknown"
        ).strip()

    @property
    def identity(self) -> tuple[str, str, str, int, str]:
        return (
            self.dataset,
            self.source_model,
            str(self.tracker).strip().upper(),
            int(self.season or self.year or 0),
            str(self.metadata.get("raw_track_id") or self.track_id).strip(),
        )

    @property
    def final_point(self) -> Optional[TrackPoint]:
        return self.points[-1] if self.points else None

    @property
    def display_name(self) -> str:
        raw_track_id = self.metadata.get("raw_track_id") or self.track_id
        display_year = self.season or self.year or "unknown"
        return f"Cyclone {raw_track_id} ({display_year})"

    def refresh_derived_fields(self) -> None:
        if not self.points:
            self.max_category = int(self.max_category or 0)
            self.max_wind_speed = float(self.max_wind_speed or 0.0)
            self.lifetime_hours = float(self.lifetime_hours or 0.0)
            return

        genesis = self.points[0]
        self.genesis_lat = genesis.lat
        self.genesis_lon = genesis.lon
        self.genesis_time = genesis.timestamp

        # Extract max wind speed directly from points (already in km/h)
        wind_speeds = [p.wind_speed for p in self.points if p.wind_speed is not None]
        self.max_wind_speed = max(wind_speeds) if wind_speeds else 0.0

        # Australian TC Category scale (km/h)
        wind = self.max_wind_speed
        if wind >= 200:
            self.max_category = 5
        elif wind >= 160:
            self.max_category = 4
        elif wind >= 118:
            self.max_category = 3
        elif wind >= 89:
            self.max_category = 2
        elif wind >= 63:
            self.max_category = 1
        else:
            self.max_category = 0

        self.landfall = any(
            bool(p.metadata.get("landfall", False)) or is_australia_landfall(p.lat, p.lon)
            for p in self.points
        )

        timestamps = sorted(p.timestamp for p in self.points if p.timestamp is not None)
        if len(timestamps) >= 2:
            duration = timestamps[-1] - timestamps[0]
            self.lifetime_hours = duration.total_seconds() / 3600.0
        else:
            self.lifetime_hours = float(self.lifetime_hours or 0.0)

        if self.year is None and self.genesis_time:
            self.year = self.genesis_time.year

        if self.season is None:
            self.season = self.year