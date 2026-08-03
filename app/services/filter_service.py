"""Reusable backend filtering for prepared cyclone records."""

from __future__ import annotations

import pandas as pd


def apply_filters(
    frame: pd.DataFrame,
    *,
    driving_model: str | None = None,
    start_season: int | None = None,
    end_season: int | None = None,
    min_wind: float | None = None,
    max_wind: float | None = None,
    min_lon: float | None = None,
    max_lon: float | None = None,
    min_lat: float | None = None,
    max_lat: float | None = None,
) -> pd.DataFrame:
    """Return rows matching the requested API filters.

    ``Model`` in the supplied CSVs is the driving model (ERA5 or a CMIP6
    model). BARPA/CCAM is carried separately as ``RegionalModel``.
    """
    if (
        start_season is not None
        and end_season is not None
        and start_season > end_season
    ):
        raise ValueError("start_season must not be greater than end_season.")

    if min_wind is not None and max_wind is not None and min_wind > max_wind:
        raise ValueError("min_wind must not be greater than max_wind.")

    if min_lon is not None and max_lon is not None and min_lon > max_lon:
        raise ValueError("min_lon must not be greater than max_lon.")

    if min_lat is not None and max_lat is not None and min_lat > max_lat:
        raise ValueError("min_lat must not be greater than max_lat.")

    mask = pd.Series(True, index=frame.index)

    if driving_model:
        mask &= frame["Model"].astype(str).str.casefold() == driving_model.casefold()

    if start_season is not None:
        mask &= frame["Season"] >= start_season

    if end_season is not None:
        mask &= frame["Season"] <= end_season

    if min_wind is not None:
        mask &= frame["Wspd"] >= min_wind

    if max_wind is not None:
        mask &= frame["Wspd"] <= max_wind

    if min_lon is not None:
        mask &= frame["Lon"] >= min_lon

    if max_lon is not None:
        mask &= frame["Lon"] <= max_lon

    if min_lat is not None:
        mask &= frame["Lat"] >= min_lat

    if max_lat is not None:
        mask &= frame["Lat"] <= max_lat

    return frame.loc[mask].copy()