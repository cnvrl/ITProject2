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
    filename_tokens = (
        "ccam",
    )