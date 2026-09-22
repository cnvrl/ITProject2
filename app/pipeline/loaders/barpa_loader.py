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
    filename_tokens = (
        "barpa",
    )