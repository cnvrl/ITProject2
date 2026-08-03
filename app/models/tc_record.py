from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


DataSource = Literal["simulated", "real"]
RegionalModel = Literal["BARPA", "CCAM"]
TrackerType = Literal["CDD", "TE"]
ScenarioType = Literal["historical", "future", "current", "nat", "2k", "4k"]


class TCPoint(BaseModel):
    time: datetime
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    wind_speed: Optional[float] = Field(default=None, description="Maximum sustained wind speed at this timestep.")
    pressure: Optional[float] = Field(default=None, description="Minimum central pressure at this timestep.")
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


class TCRecord(BaseModel):
    track_id: str
    dataset_id: str
    data_source: DataSource
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
            return value
        if value > 180:
            return value - 360
        if value < -180:
            return value + 360
        return value

    @model_validator(mode="after")
    def derive_summary_fields(self) -> "TCRecord":
        if self.points:
            ordered_points = sorted(self.points, key=lambda p: p.time)
            self.points = ordered_points
            first_point = ordered_points[0]
            last_point = ordered_points[-1]
            if self.genesis_time is None:
                self.genesis_time = first_point.time
            if self.genesis_lat is None:
                self.genesis_lat = first_point.lat
            if self.genesis_lon is None:
                self.genesis_lon = first_point.lon
            if self.year is None:
                self.year = first_point.time.year
            if self.lifetime_hours is None:
                self.lifetime_hours = (last_point.time - first_point.time).total_seconds() / 3600
            wind_values = [p.wind_speed for p in ordered_points if p.wind_speed is not None]
            if wind_values and self.max_wind_speed is None:
                self.max_wind_speed = max(wind_values)
            pressure_values = [p.pressure for p in ordered_points if p.pressure is not None]
            if pressure_values and self.min_pressure is None:
                self.min_pressure = min(pressure_values)
            category_values = [p.category for p in ordered_points if p.category is not None]
            if category_values and self.max_category is None:
                self.max_category = max(category_values)
            if self.landfall and self.landfall_time is None:
                land_points = [p for p in ordered_points if p.over_land]
                if land_points:
                    self.landfall_time = land_points[0].time
                    self.landfall_lat = land_points[0].lat
                    self.landfall_lon = land_points[0].lon
        return self