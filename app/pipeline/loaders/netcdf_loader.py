"""

netcdf_loader.py
The NetCDFLoader class is responsible for loading cyclone track data from NetCDF files into TCRecord objects. It handles parsing of timestamps, grouping of points into tracks, and conversion of wind speed and pressure units. The loader also derives metadata such as model, tracker, season, and segment number for each track.

Class: NetCDFLoader(BaseTCLoader)
    - Inherits from BaseTCLoader and implements the load() method to read NetCDF files.
    - Parses timestamps, normalizes row data, and converts values to appropriate types.
    - Groups points by track ID and segments tracks based on time gaps.
    - Returns a list of TCRecord objects representing the cyclone tracks.

"""
from __future__ import annotations

import math
from collections import defaultdict

import xarray as xr

from app.models.tc_record import TCPoint
from app.pipeline.loaders.base import BaseTCLoader


class NetCDFLoader(BaseTCLoader):
    def load(self) -> list:
        ds = xr.open_dataset(self.source_file)
        grouped: dict[str, list[TCPoint]] = defaultdict(list)

        try:
            track_var = next((v for v in ('track_id', 'trackid', 'storm_id') if v in ds.variables), None)
            time_var = next((v for v in ('time', 'iso_time') if v in ds.variables), None)
            lat_var = next((v for v in ('lat', 'latitude') if v in ds.variables), None)
            lon_var = next((v for v in ('lon', 'longitude') if v in ds.variables), None)
            wind_var = next((v for v in ('wind_speed', 'wind', 'wspd', 'vmax') if v in ds.variables), None)
            pressure_var = next((v for v in ('pressure', 'pres', 'pmin') if v in ds.variables), None)
            category_var = 'category' if 'category' in ds.variables else None

            if not all([track_var, time_var, lat_var, lon_var]):
                missing = [
                    name for name, var in [
                        ('track_id', track_var), ('time', time_var),
                        ('lat', lat_var), ('lon', lon_var),
                    ] if var is None
                ]
                raise ValueError(f"NetCDF file missing required variables: {missing}")

            columns = [v for v in [track_var, time_var, lat_var, lon_var, wind_var, pressure_var, category_var] if v]
            frame = ds[columns].to_dataframe().reset_index()

            for _, row in frame.iterrows():
                track_id_value = row.get(track_var)
                if self._is_missing(track_id_value):
                    continue
                track_id = str(track_id_value)

                time_value = row.get(time_var)
                lat_value = row.get(lat_var)
                lon_value = row.get(lon_var)

                if self._is_missing(time_value) or self._is_missing(lat_value) or self._is_missing(lon_value):
                    continue

                try:
                    parsed_time = (
                        time_value.to_pydatetime()
                        if hasattr(time_value, 'to_pydatetime')
                        else time_value
                    )
                    lat = float(lat_value)
                    lon = float(lon_value)
                except (ValueError, TypeError):
                    continue

                grouped[track_id].append(
                    TCPoint(
                        time=parsed_time,
                        lat=lat,
                        lon=lon,
                        wind_speed=self.to_float(row.get(wind_var)) if wind_var else None,
                        pressure=self.to_float(row.get(pressure_var)) if pressure_var else None,
                        category=self.to_int(row.get(category_var)) if category_var else None,
                    )
                )
        finally:
            ds.close()

        return [
            self.build_record(track_id=track_id, points=points, data_source='real')
            for track_id, points in grouped.items()
            if points
        ]