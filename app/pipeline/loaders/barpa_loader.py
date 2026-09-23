from __future__ import annotations

from app.pipeline.loaders.base import BaseCSVTrackLoader


class BARPALoader(BaseCSVTrackLoader):
    """
    Load BARPA tropical-cyclone track CSV files.

    CDD and TE are treated as tracker values within the BARPA dataset rather
    than separate input formats.
    """

    dataset_type = "barpa"
    dataset_label = "BARPA"
    filename_tokens = ("barpa",)

    def __init__(
        self,
        *,
        default_region: str = "Australia",
        default_wind_unit: str = "km/h",  # Explicitly set BARPA raw unit to km/h
    ) -> None:
        super().__init__(
            default_region=default_region,
            default_wind_unit=default_wind_unit,
        )
