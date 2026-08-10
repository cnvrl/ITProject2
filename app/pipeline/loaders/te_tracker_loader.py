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