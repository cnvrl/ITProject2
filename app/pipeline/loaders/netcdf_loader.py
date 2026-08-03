from __future__ import annotations

from collections import defaultdict

import xarray as xr

from app.models.tc_record import TCPoint
from app.pipeline.loaders.base import BaseTCLoader


class NetCDFLoader(BaseTCLoader):
    def load(self) -> list:
        ds = xr.open_dataset(self.source_file)
        grouped: dict[str, list[TCPoint]] = defaultdict(list)

        track_var = 'track_id' if 'track_id' in ds.variables else 'storm_id'
        time_var = 'time'
        lat_var = 'lat' if 'lat' in ds.variables else 'latitude'
        lon_var = 'lon' if 'lon' in ds.variables else 'longitude'
        wind_var = 'wind_speed' if 'wind_speed' in ds.variables else ('wind' if 'wind' in ds.variables else None)
        pressure_var = 'pressure' if 'pressure' in ds.variables else ('pmin' if 'pmin' in ds.variables else None)
        category_var = 'category' if 'category' in ds.variables else None

        frame = ds[[v for v in [track_var, time_var, lat_var, lon_var, wind_var, pressure_var, category_var] if v]].to_dataframe().reset_index()

        for _, row in frame.iterrows():
            track_id = str(row[track_var])
            grouped[track_id].append(
                TCPoint(
                    time=row[time_var].to_pydatetime() if hasattr(row[time_var], 'to_pydatetime') else row[time_var],
                    lat=float(row[lat_var]),
                    lon=float(row[lon_var]),
                    wind_speed=self.to_float(row[wind_var]) if wind_var else None,
                    pressure=self.to_float(row[pressure_var]) if pressure_var else None,
                    category=self.to_int(row[category_var]) if category_var else None,
                )
            )

        ds.close()
        return [self.build_record(track_id=track_id, points=points) for track_id, points in grouped.items()]