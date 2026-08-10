from __future__ import annotations

from datetime import datetime
from math import asin, cos, radians, sin, sqrt
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

DataSource = Literal["simulated", "real"]
RegionalModel = Literal["BARPA", "CCAM"]
TrackerType = Literal["CDD", "TE"]
ScenarioType = Literal["historical", "future", "current", "nat", "2k", "4k"]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0088
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    )
    return 2 * radius_km * asin(sqrt(a))


def category_from_wind_kmh(wind_speed: Optional[float]) -> Optional[int]:
    """
    Approximate Saffir-Simpson category from wind speed in km/h.

    The supplied BARPA/CCAM CSVs contain Wspd but no explicit category.
    This supplies categories for intensity maps, sliders and statistics.
    """
    if wind_speed is None:
        return None
    if wind_speed < 119:
        return 0
    if wind_speed < 154:
        return 1
    if wind_speed < 178:
        return 2
    if wind_speed < 209:
        return 3
    if wind_speed < 252:
        return 4
    return 5


class TCPoint(BaseModel):
    time: datetime
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)

    wind_speed: Optional[float] = Field(default=None, ge=0)
    pressure: Optional[float] = Field(default=None, ge=0)
    category: Optional[int] = Field(default=None, ge=0, le=5)
    over_land: Optional[bool] = None

    @field_validator("lon")
    @classmethod
    def normalize_longitude(cls, value: float) -> float:
        if value > 180:
            return value - 360
        if value < -180:
            return value + 360
        return value

    @model_validator(mode="after")
    def derive_point_category(self) -> "TCPoint":
        if self.category is None:
            self.category = category_from_wind_kmh(self.wind_speed)
        return self


class TCRecord(BaseModel):
    track_id: str
    dataset_id: str
    data_source: DataSource = "simulated"

    model: Optional[RegionalModel] = None
    tracker: Optional[TrackerType] = None
    scenario: Optional[ScenarioType] = None
    ensemble: Optional[int] = Field(default=None, ge=1)
    driving_gcm: Optional[str] = None
    region: Optional[str] = None

    points: list[TCPoint] = Field(default_factory=list)

    genesis_time: Optional[datetime] = None
    genesis_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    genesis_lon: Optional[float] = Field(default=None, ge=-180, le=180)

    landfall_time: Optional[datetime] = None
    landfall_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    landfall_lon: Optional[float] = Field(default=None, ge=-180, le=180)
    landfall: bool = False

    lifetime_hours: Optional[float] = Field(default=None, ge=0)
    max_wind_speed: Optional[float] = Field(default=None, ge=0)
    min_pressure: Optional[float] = Field(default=None, ge=0)
    max_category: Optional[int] = Field(default=None, ge=0, le=5)
    translation_speed_mean: Optional[float] = Field(default=None, ge=0)

    year: Optional[int] = Field(default=None, ge=1800, le=2200)
    source_file: Optional[str] = None
    metadata: dict = Field(default_factory=dict)

    @field_validator("genesis_lon", "landfall_lon")
    @classmethod
    def normalize_event_longitude(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        if value > 180:
            return value - 360
        if value < -180:
            return value + 360
        return value

    @model_validator(mode="after")
    def derive_summary_fields(self) -> "TCRecord":
        if not self.points:
            return self

        self.points = sorted(self.points, key=lambda point: point.time)
        first = self.points[0]
        last = self.points[-1]

        if self.genesis_time is None:
            self.genesis_time = first.time
        if self.genesis_lat is None:
            self.genesis_lat = first.lat
        if self.genesis_lon is None:
            self.genesis_lon = first.lon
        if self.year is None:
            self.year = first.time.year

        if self.lifetime_hours is None:
            self.lifetime_hours = max(
                0.0,
                (last.time - first.time).total_seconds() / 3600,
            )

        wind_values = [p.wind_speed for p in self.points if p.wind_speed is not None]
        pressure_values = [p.pressure for p in self.points if p.pressure is not None]
        categories = [p.category for p in self.points if p.category is not None]

        if self.max_wind_speed is None and wind_values:
            self.max_wind_speed = max(wind_values)
        if self.min_pressure is None and pressure_values:
            self.min_pressure = min(pressure_values)
        if self.max_category is None and categories:
            self.max_category = max(categories)

        if self.translation_speed_mean is None and len(self.points) > 1:
            segment_speeds = []
            for previous, current in zip(self.points, self.points[1:]):
                hours = (current.time - previous.time).total_seconds() / 3600
                if hours > 0:
                    distance_km = haversine_km(
                        previous.lat,
                        previous.lon,
                        current.lat,
                        current.lon,
                    )
                    segment_speeds.append(distance_km / hours)
            if segment_speeds:
                self.translation_speed_mean = sum(segment_speeds) / len(segment_speeds)

        land_points = [point for point in self.points if point.over_land is True]
        if land_points:
            self.landfall = True
            if self.landfall_time is None:
                first_land_point = land_points[0]
                self.landfall_time = first_land_point.time
                self.landfall_lat = first_land_point.lat
                self.landfall_lon = first_land_point.lon

        return self