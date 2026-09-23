from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for TC Explorer."""

    app_name: str = "TC Explorer 2.0"
    app_description: str = "Tropical cyclone analysis dashboard"

    host: str = os.getenv("TC_EXPLORER_HOST", "0.0.0.0")
    port: int = int(os.getenv("TC_EXPLORER_PORT", "8050"))
    debug: bool = os.getenv(
        "TC_EXPLORER_DEBUG",
        "false",
    ).strip().lower() in {"1", "true", "yes"}

    data_dir: Path = Path(
        os.getenv(
            "TC_EXPLORER_DATA_DIR",
            str(PROJECT_DIR / "data"),
        )
    ).resolve()

    assets_dir: Path = Path(
        os.getenv(
            "TC_EXPLORER_ASSETS_DIR",
            str(APP_DIR / "assets"),
        )
    ).resolve()

    output_dir: Path = Path(
        os.getenv(
            "TC_EXPLORER_OUTPUT_DIR",
            str(PROJECT_DIR / "output"),
        )
    ).resolve()

    historical_end_year: int = 2014

    heatmap_min_longitude: float = 105.0
    heatmap_max_longitude: float = 165.0
    heatmap_min_latitude: float = -48.0
    heatmap_max_latitude: float = 2.0
    heatmap_max_points: int = 75_000

    default_region: str = "Australia"
    default_model_count: int = 2

    welch_min_longitude: float = 100.0
    welch_max_longitude: float = 180.0
    welch_min_latitude: float = -60.0
    welch_max_latitude: float = 0.0

    aus_landfall_min_lat: float = -44.0
    aus_landfall_max_lat: float = -10.5
    aus_landfall_min_lon: float = 113.0
    aus_landfall_max_lon: float = 153.8

SETTINGS = Settings()


DATASET_TYPE_BY_FILE = {
    "barpa_cdd_all_ssp370.csv": "barpa",
    "barpa_te_all_ssp370.csv": "barpa",
    "ccam_cdd_all_ssp370.csv": "ccam",
    "ccam_te_all_ssp370.csv": "ccam",
}


SUPPORTED_DATASET_TYPES = {
    "barpa",
    "ccam",
}


MODEL_GUIDE = {
    ("BARPA", "CDD"): [
        "ACCESS-CM2",
        "ACCESS-ESM1.5",
        "CESM2",
        "CMCC-ESM2",
        "EC-Earth3",
        "ERA5",
    ],
    ("BARPA", "TE"): [
        "ACCESS-CM2",
        "ACCESS-ESM1.5",
        "CESM2",
        "CMCC-ESM2",
        "EC-Earth3",
        "ERA5",
        "MPI-ESM1-2-HR",
        "NorESM2-MM",
    ],
    ("CCAM", "CDD"): [
        "ACCESS-CM",
        "ACCESS-CM2",
        "ERA5",
    ],
    ("CCAM", "TE"): [
        "ACCESS-CM2",
        "ACCESS-ESM1.5",
        "CESM2",
        "CMCC-ESM2",
        "EC-Earth3",
        "ERA5",
        "NorESM2-MM",
    ],
}


MODEL_NUMBER_GUIDE = {
    ("BARPA", "CDD", "ACCESS-CM2"): 1,
    ("BARPA", "CDD", "ACCESS-ESM1.5"): 2,
    ("BARPA", "CDD", "CESM2"): 3,
    ("BARPA", "CDD", "CMCC-ESM2"): 4,
    ("BARPA", "CDD", "EC-Earth3"): 5,
    ("BARPA", "CDD", "ERA5"): 6,

    ("BARPA", "TE", "ACCESS-CM2"): 7,
    ("BARPA", "TE", "ACCESS-ESM1.5"): 8,
    ("BARPA", "TE", "CESM2"): 9,
    ("BARPA", "TE", "CMCC-ESM2"): 10,
    ("BARPA", "TE", "EC-Earth3"): 11,
    ("BARPA", "TE", "ERA5"): 12,
    ("BARPA", "TE", "MPI-ESM1-2-HR"): 13,
    ("BARPA", "TE", "NorESM2-MM"): 14,

    ("CCAM", "CDD", "ACCESS-CM"): 15,
    ("CCAM", "CDD", "ACCESS-CM2"): 16,
    ("CCAM", "CDD", "ERA5"): 17,

    ("CCAM", "TE", "ACCESS-CM2"): 18,
    ("CCAM", "TE", "ACCESS-ESM1.5"): 19,
    ("CCAM", "TE", "CESM2"): 20,
    ("CCAM", "TE", "CMCC-ESM2"): 21,
    ("CCAM", "TE", "EC-Earth3"): 22,
    ("CCAM", "TE", "ERA5"): 23,
    ("CCAM", "TE", "NorESM2-MM"): 24,
}


CATEGORY_COLOURS = {
    0: "#94a3b8",
    1: "#38bdf8",
    2: "#22c55e",
    3: "#facc15",
    4: "#fb923c",
    5: "#ef4444",
}


MODEL_COLOURS = [
    "#1769aa",
    "#ef7d32",
    "#2f8f65",
    "#9b59b6",
    "#d4a017",
    "#c44536",
    "#377eb8",
    "#6a994e",
]



def ensure_runtime_directories() -> None:
    """Create application-owned output directories."""
    SETTINGS.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )