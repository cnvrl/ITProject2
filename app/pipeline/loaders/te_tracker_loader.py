"""

te_tracker_loader.py
The TETrackerLoader class is a specialized loader for cyclone track data from the TE dataset. It determines whether to use the BARPALoader or CCAMLoader based on the source file name, and then loads the data accordingly. After loading, it sets the tracker attribute of each TCRecord to "TE".

Class: TETrackerLoader(BaseTCLoader)
    - Inherits from BaseTCLoader and implements the load() method to read TE CSV files.
    - Determines the appropriate loader (BARPALoader or CCAMLoader) based on the source file name.
    - Loads the data using the selected loader and sets the tracker attribute of each TCRecord to "TE".
    - Returns a list of TCRecord objects representing the cyclone tracks.

"""
from __future__ import annotations

from app.pipeline.loaders.barpa_loader import BARPALoader
from app.pipeline.loaders.ccam_loader import CCAMLoader
from app.pipeline.loaders.base import BaseTCLoader


class TETrackerLoader(BaseTCLoader):
    def load(self):
        filename = self.source_file.name.lower()
        loader_class = CCAMLoader if "ccam" in filename else BARPALoader

        loader = loader_class(
            dataset_id=self.dataset_id,
            source_file=self.source_file,
            **self.context,
        )
        records = loader.load()

        for record in records:
            record.tracker = "TE"

        return records