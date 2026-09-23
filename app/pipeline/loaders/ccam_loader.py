from __future__ import annotations

from app.pipeline.loaders.base import BaseCSVTrackLoader


class CCAMLoader(BaseCSVTrackLoader):
    """
    Load CCAM tropical-cyclone track CSV files.

    CDD and TE are treated as tracker values within the CCAM dataset rather
    than separate input formats.
    """

    dataset_type = "ccam"
    dataset_label = "CCAM"
    filename_tokens = ("ccam",)

    def __init__(
        self,
        *,
        default_region: str = "Australia",
        default_wind_unit: str = "m/s",  # Explicitly set CCAM raw unit to m/s
    ) -> None:
        super().__init__(
            default_region=default_region,
            default_wind_unit=default_wind_unit,
        )