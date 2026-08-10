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

    @model_validator(mode="after")
    def derive_fields(self) -> "TCRecord":
        if not self.points:
            return self
        self.points = sorted(self.points, key=lambda p: p.time)
        first = self.points[0]
        last = self.points[-1]
        self.genesis_time = self.genesis_time or first.time
        self.genesis_lat = self.genesis_lat if self.genesis_lat is not None else first.lat
        self.genesis_lon = self.genesis_lon if self.genesis_lon is not None else first.lon
        self.year = self.year or first.time.year
        self.lifetime_hours = self.lifetime_hours if self.lifetime_hours is not None else (last.time - first.time).total_seconds() / 3600
        winds = [p.wind_speed for p in self.points if p.wind_speed is not None]
        pressures = [p.pressure for p in self.points if p.pressure is not None]
        cats = [p.category for p in self.points if p.category is not None]
        if winds and self.max_wind_speed is None:
            self.max_wind_speed = max(winds)
        if pressures and self.min_pressure is None:
            self.min_pressure = min(pressures)
        if cats and self.max_category is None:
            self.max_category = max(cats)
        if self.landfall and self.landfall_time is None:
            land_points = [p for p in self.points if p.over_land]
            if land_points:
                self.landfall_time = land_points[0].time
                self.landfall_lat = land_points[0].lat
                self.landfall_lon = land_points[0].lon
        return self