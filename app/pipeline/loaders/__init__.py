"""Dataset loaders used by the TC Explorer ingestion pipeline."""

from app.pipeline.loaders.barpa_loader import BARPALoader
from app.pipeline.loaders.base import (
    BaseCSVTrackLoader,
    LoaderError,
    LoaderResult,
)
from app.pipeline.loaders.ccam_loader import CCAMLoader

__all__ = [
    "BARPALoader",
    "BaseCSVTrackLoader",
    "CCAMLoader",
    "LoaderError",
    "LoaderResult",
]


def create_default_loaders() -> list[BaseCSVTrackLoader]:
    """Create the production loader collection."""

    return [
        BARPALoader(),
        CCAMLoader(),
    ]