from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Optional


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
            return datetime.strptime(
                text,
                timestamp_format,
            )
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
    def from_mapping(
        cls,
        values: Mapping[str, Any],
    ) -> "TrackPoint":
        latitude = (
            values.get("lat")
            if values.get("lat") is not None
            else values.get("latitude")
        )

        longitude = (
            values.get("lon")
            if values.get("lon") is not None
            else values.get("longitude")
        )

        if latitude is None or longitude is None:
            raise ValueError(
                "Track points require latitude and longitude."
            )

        timestamp = (
            values.get("timestamp")
            or values.get("datetime")
            or values.get("time")
            or values.get("date")
        )

        wind_speed = (
            values.get("wind_speed")
            if values.get("wind_speed") is not None
            else values.get("wind")
        )

        pressure = (
            values.get("pressure")
            if values.get("pressure") is not None
            else values.get("central_pressure")
        )

        known_fields = {
            "lat",
            "latitude",
            "lon",
            "longitude",
            "timestamp",
            "datetime",
            "time",
            "date",
            "wind_speed",
            "wind",
            "pressure",
            "central_pressure",
            "category",
            "step",
        }

        metadata = {
            key: value
            for key, value in values.items()
            if key not in known_fields
        }

        return cls(
            lat=float(latitude),
            lon=float(longitude),
            timestamp=coerce_datetime(timestamp),
            wind_speed=optional_float(wind_speed),
            pressure=optional_float(pressure),
            category=optional_int(values.get("category")),
            step=optional_int(values.get("step")),
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "lat": self.lat,
            "lon": self.lon,
            "timestamp": (
                self.timestamp.isoformat()
                if self.timestamp
                else None
            ),
            "wind_speed": self.wind_speed,
            "pressure": self.pressure,
            "category": self.category,
            "step": self.step,
            "metadata": dict(self.metadata),
        }


TCPoint = TrackPoint


@dataclass
class TCRecord:
    """
    Canonical tropical cyclone domain record.

    `model` stores the regional dataset family, normally BARPA or CCAM.
    `driving_model` stores ACCESS-CM2, ERA5, CESM2, and similar model names.
    """

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
        """Return the regional dataset family."""

        return str(
            self.model
            or self.metadata.get("dataset")
            or self.dataset_id
            or "unknown"
        ).strip().upper()

    @property
    def source_model(self) -> str:
        """Return the driving climate model."""

        return str(
            self.driving_model
            or self.metadata.get("source_model_value")
            or self.metadata.get("driving_model")
            or "unknown"
        ).strip()

    @property
    def identity(self) -> tuple[str, str, str, int, str]:
        """Composite identity used to prevent track collisions."""

        return (
            self.dataset,
            self.source_model,
            str(self.tracker).strip().upper(),
            int(self.season or self.year or 0),
            str(
                self.metadata.get("raw_track_id")
                or self.track_id
            ).strip(),
        )

    @property
    def uid(self) -> str:
        """Stable dashboard identifier."""

        return "|".join(
            str(value)
            for value in self.identity
        )

    @property
    def genesis_point(self) -> Optional[TrackPoint]:
        return self.points[0] if self.points else None

    @property
    def final_point(self) -> Optional[TrackPoint]:
        return self.points[-1] if self.points else None

    @property
    def display_name(self) -> str:
        raw_track_id = (
            self.metadata.get("raw_track_id")
            or self.track_id
        )

        display_year = self.season or self.year or "unknown"

        return f"Cyclone {raw_track_id} ({display_year})"

    def refresh_derived_fields(self) -> None:
        """Recalculate metrics that can be derived from track points."""

        if not self.points:
            self.max_category = int(self.max_category or 0)
            self.max_wind_speed = float(
                self.max_wind_speed or 0.0
            )
            self.lifetime_hours = float(
                self.lifetime_hours or 0.0
            )
            return

        genesis = self.points[0]

        self.genesis_lat = genesis.lat
        self.genesis_lon = genesis.lon
        self.genesis_time = genesis.timestamp

        categories = [
            point.category
            for point in self.points
            if point.category is not None
        ]

        wind_speeds = [
            point.wind_speed
            for point in self.points
            if point.wind_speed is not None
        ]

        if categories:
            self.max_category = max(categories)
        else:
            self.max_category = int(
                self.max_category or 0
            )

        if wind_speeds:
            self.max_wind_speed = max(wind_speeds)
        else:
            self.max_wind_speed = float(
                self.max_wind_speed or 0.0
            )

        timestamps = sorted(
            point.timestamp
            for point in self.points
            if point.timestamp is not None
        )

        if len(timestamps) >= 2:
            duration = timestamps[-1] - timestamps[0]

            self.lifetime_hours = (
                duration.total_seconds() / 3600.0
            )
        else:
            self.lifetime_hours = float(
                self.lifetime_hours or 0.0
            )

        if self.year is None and self.genesis_time:
            self.year = self.genesis_time.year

        if self.season is None:
            self.season = self.year

    def to_dict(
        self,
        include_points: bool = True,
    ) -> dict[str, Any]:
        output = {
            "dataset_id": self.dataset_id,
            "track_id": self.track_id,
            "uid": self.uid,
            "model": self.model,
            "dataset": self.dataset,
            "driving_model": self.source_model,
            "tracker": self.tracker,
            "scenario": self.scenario,
            "region": self.region,
            "season": self.season,
            "year": self.year,
            "max_category": self.max_category,
            "max_wind_speed": self.max_wind_speed,
            "lifetime_hours": self.lifetime_hours,
            "landfall": self.landfall,
            "genesis_lat": self.genesis_lat,
            "genesis_lon": self.genesis_lon,
            "genesis_time": (
                self.genesis_time.isoformat()
                if self.genesis_time
                else None
            ),
            "metadata": dict(self.metadata),
        }

        if include_points:
            output["points"] = [
                point.to_dict()
                for point in self.points
            ]

        return output