#Backend data access for prepared TC-Explorer CSV tables.


from __future__ import annotations
import os
from io import StringIO
from pathlib import Path
import pandas as pd
from app.services.cache_manager import cache_manager


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR = Path(os.getenv("TC_DATA_DIR", DEFAULT_DATA_DIR))

SOURCE_FILES: dict[tuple[str, str], str] = {
    ("BARPA", "CDD"): "barpa_cdd_all_ssp370.csv",
    ("BARPA", "TE"): "barpa_te_all_ssp370.csv",
    ("CCAM", "CDD"): "ccam_cdd_all_ssp370.csv",
    ("CCAM", "TE"): "ccam_te_all_ssp370.csv",
}

REQUIRED_COLUMNS = {
    "Model",
    "Tracker",
    "TrackID",
    "Season",
    "Time",
    "Lon",
    "Lat",
    "Wspd",
    "Pres",
}


def available_sources() -> list[dict[str, str | bool]]:
    """Describe configured regional-model and tracker sources."""
    result: list[dict[str, str | bool]] = []

    for (regional_model, tracker), filename in SOURCE_FILES.items():
        path = DATA_DIR / filename
        result.append(
            {
                "regional_model": regional_model,
                "tracker": tracker,
                "filename": filename,
                "available": path.is_file(),
            }
        )

    return result


def _source_key(regional_model: str, tracker: str) -> tuple[str, str]:
    regional_model = regional_model.upper()
    tracker = tracker.upper()
    key = (regional_model, tracker)

    if key not in SOURCE_FILES:
        raise ValueError(
            "Unsupported source. regional_model must be BARPA or CCAM and "
            "tracker must be CDD or TE."
        )

    return key


def _read_prepared_csv(path: Path, regional_model: str) -> pd.DataFrame:
    """Read one prepared flat table without model-specific transformations."""
    if not path.is_file():
        raise FileNotFoundError(
            f"Prepared dataset not found: {path}. "
            "Place the CSV in data or set TC_DATA_DIR."
        )

    frame = pd.read_csv(path, low_memory=False)
    missing = sorted(REQUIRED_COLUMNS.difference(frame.columns))

    if missing:
        raise ValueError(
            f"{path.name} is missing required prepared columns: {missing}"
        )

    # This is source metadata, not a replacement for the shared DB schema.
    frame["RegionalModel"] = regional_model
    return frame


def get_dataset(regional_model: str, tracker: str) -> pd.DataFrame:
    """Return one prepared dataset, using the in-memory cache when possible."""
    key = _source_key(regional_model, tracker)
    cache_key = f"dataset:{key[0]}:{key[1]}"

    cached = cache_manager.get(cache_key)
    if cached is not None:
        return cached

    filename = SOURCE_FILES[key]
    frame = _read_prepared_csv(DATA_DIR / filename, key[0])
    cache_manager.set(cache_key, frame)
    return frame


def dataframe_to_csv(frame: pd.DataFrame) -> str:
    """Serialise a filtered table for the export endpoint."""
    buffer = StringIO()
    frame.to_csv(buffer, index=False)
    return buffer.getvalue()
