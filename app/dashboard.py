from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import (
    ALL,
    Dash,
    Input,
    Output,
    State,
    callback,
    ctx,
    dcc,
    html,
    no_update,
)

from app.services.data_manager import DataManager


# =============================================================================
# PATHS AND DATA CONFIGURATION
# =============================================================================

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"


DATASET_TYPE_BY_FILE = {
    "barpa_cdd_all_ssp370.csv": "barpa",
    "barpa_te_all_ssp370.csv": "barpa",
    "ccam_cdd_all_ssp370.csv": "ccam",
    "ccam_te_all_ssp370.csv": "ccam",
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


ALL_MODELS = list(
    dict.fromkeys(
        model
        for model_list in MODEL_GUIDE.values()
        for model in model_list
    )
)


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


data_manager = DataManager(data_dir=DATA_DIR)


# =============================================================================
# DATA LOADING AND NORMALISATION
# =============================================================================

def resolve_scenario(
    driving_model: object,
    season: object,
    source_scenario: object = None,
) -> str:
    """
    Correct historical/future scenario labels.

    ERA5 is treated as historical/reanalysis data. For climate-model records,
    seasons up to and including 2014 are historical and seasons from 2015
    onward are future scenario records.
    """

    model = str(driving_model or "").strip().upper()

    try:
        season_year = int(float(season))
    except (TypeError, ValueError):
        source = str(source_scenario or "").strip().lower()
        return source if source else "unknown"

    if model == "ERA5":
        return "historical"

    return "historical" if season_year <= 2014 else "future"


def load_real_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load all dataset files through DataManager and flatten TCRecord objects
    into track-level and point-level DataFrames.
    """

    track_rows: list[dict] = []
    point_rows: list[dict] = []

    filenames = data_manager.list_datasets()
    csv_filenames = [
        filename
        for filename in filenames
        if filename.lower().endswith(".csv")
    ]

    for filename in csv_filenames:
        dataset_type = DATASET_TYPE_BY_FILE.get(filename.lower())

        try:
            result = data_manager.load_dataset(
                filename,
                dataset_type=dataset_type,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[dashboard] Skipping {filename}: {exc}")
            continue

        records = result.get("records", [])

        for record in records:
            metadata = record.metadata or {}

            dataset_name = str(
                record.model
                or record.dataset_id
                or dataset_type
                or "unknown"
            ).strip().upper()

            driving_model = str(
                metadata.get("source_model_value")
                or metadata.get("driving_model")
                or record.model
                or "unknown"
            ).strip()

            raw_track_id = str(
                metadata.get("raw_track_id")
                or record.track_id
            ).strip()

            season = str(
                metadata.get("season")
                or record.year
                or "unknown"
            ).strip()

            tracker = str(
                record.tracker
                or metadata.get("tracker")
                or "unknown"
            ).strip().upper()

            dashboard_track_id = (
                f"{record.dataset_id}:"
                f"{dataset_name}:"
                f"{tracker}:"
                f"{driving_model}:"
                f"{season}:"
                f"{record.track_id}"
            )

            corrected_scenario = resolve_scenario(
                driving_model,
                season,
                record.scenario,
            )

            track_rows.append(
                {
                    "track_id": dashboard_track_id,
                    "name": record.track_id,
                    "dataset": dataset_name,
                    "driving_model": driving_model,
                    "raw_track_id": raw_track_id,
                    "season": season,
                    "scenario": corrected_scenario,
                    "region": str(
                        record.region or "unknown"
                    ).strip(),
                    "tracker": tracker,
                    "year": record.year,
                    "max_category": record.max_category or 0,
                    "max_wind_speed": record.max_wind_speed or 0.0,
                    "lifetime_hours": record.lifetime_hours or 0.0,
                    "landfall": bool(record.landfall),
                    "genesis_lat": record.genesis_lat,
                    "genesis_lon": record.genesis_lon,
                    "last_lat": (
                        record.points[-1].lat
                        if record.points
                        else record.genesis_lat
                    ),
                    "last_lon": (
                        record.points[-1].lon
                        if record.points
                        else record.genesis_lon
                    ),
                    "genesis_date": (
                        record.genesis_time.date().isoformat()
                        if record.genesis_time
                        else None
                    ),
                }
            )

            for step, point in enumerate(record.points):
                point_rows.append(
                    {
                        "track_id": dashboard_track_id,
                        "dataset": dataset_name,
                        "driving_model": driving_model,
                        "tracker": tracker,
                        "season": season,
                        "scenario": corrected_scenario,
                        "region": str(
                            record.region or "unknown"
                        ).strip(),
                        "step": step,
                        "lat": point.lat,
                        "lon": point.lon,
                        "wind_speed": (
                            point.wind_speed
                            if point.wind_speed is not None
                            else 0.0
                        ),
                        "category": (
                            point.category
                            if point.category is not None
                            else 0
                        ),
                    }
                )

    tracks_df = pd.DataFrame(track_rows)
    points_df = pd.DataFrame(point_rows)

    if tracks_df.empty:
        raise RuntimeError(
            "No cyclone records were loaded from data/. "
            "Check the loaders and CSV headers."
        )

    tracks_df["season_numeric"] = pd.to_numeric(
        tracks_df["season"],
        errors="coerce",
    )

    tracks_df["year"] = pd.to_numeric(
        tracks_df["year"],
        errors="coerce",
    )

    tracks_df["analysis_year"] = tracks_df[
        "season_numeric"
    ].fillna(tracks_df["year"])

    tracks_df["analysis_year"] = pd.to_numeric(
        tracks_df["analysis_year"],
        errors="coerce",
    )

    tracks_df["max_category"] = pd.to_numeric(
        tracks_df["max_category"],
        errors="coerce",
    ).fillna(0).clip(lower=0, upper=5).astype(int)

    tracks_df["max_wind_speed"] = pd.to_numeric(
        tracks_df["max_wind_speed"],
        errors="coerce",
    ).fillna(0.0)

    tracks_df["lifetime_hours"] = pd.to_numeric(
        tracks_df["lifetime_hours"],
        errors="coerce",
    ).fillna(0.0)

    tracks_df["scenario"] = tracks_df.apply(
        lambda row: resolve_scenario(
            row["driving_model"],
            row["analysis_year"],
            row["scenario"],
        ),
        axis=1,
    )

    tracks_df["_track_uid"] = (
        tracks_df[
            [
                "dataset",
                "driving_model",
                "tracker",
                "season",
                "raw_track_id",
                "track_id",
            ]
        ]
        .astype(str)
        .agg("|".join, axis=1)
    )

    if not points_df.empty:
        points_df["lat"] = pd.to_numeric(
            points_df["lat"],
            errors="coerce",
        )

        points_df["lon"] = pd.to_numeric(
            points_df["lon"],
            errors="coerce",
        )

        points_df["wind_speed"] = pd.to_numeric(
            points_df["wind_speed"],
            errors="coerce",
        ).fillna(0.0)

        points_df["category"] = pd.to_numeric(
            points_df["category"],
            errors="coerce",
        ).fillna(0)

        points_df["scenario"] = points_df.apply(
            lambda row: resolve_scenario(
                row["driving_model"],
                row["season"],
                row["scenario"],
            ),
            axis=1,
        )

        track_uid_lookup = tracks_df[
            ["track_id", "_track_uid"]
        ].drop_duplicates()

        points_df = points_df.merge(
            track_uid_lookup,
            on="track_id",
            how="left",
            validate="many_to_one",
        )

    return tracks_df, points_df


DATA_LOAD_ERROR: Optional[str] = None

try:
    TRACKS, POINTS = load_real_data()
except Exception as exc:  # noqa: BLE001
    DATA_LOAD_ERROR = str(exc)

    TRACKS = pd.DataFrame(
        columns=[
            "track_id",
            "name",
            "dataset",
            "driving_model",
            "raw_track_id",
            "season",
            "season_numeric",
            "analysis_year",
            "scenario",
            "region",
            "tracker",
            "year",
            "max_category",
            "max_wind_speed",
            "lifetime_hours",
            "landfall",
            "genesis_lat",
            "genesis_lon",
            "last_lat",
            "last_lon",
            "genesis_date",
            "_track_uid",
        ]
    )

    POINTS = pd.DataFrame(
        columns=[
            "track_id",
            "dataset",
            "driving_model",
            "tracker",
            "season",
            "scenario",
            "region",
            "step",
            "lat",
            "lon",
            "wind_speed",
            "category",
            "_track_uid",
        ]
    )


if not TRACKS.empty:
    valid_years = TRACKS.loc[
        TRACKS["analysis_year"].notna(),
        "analysis_year",
    ]

    YEAR_MIN = int(valid_years.min()) if not valid_years.empty else 1980
    YEAR_MAX = int(valid_years.max()) if not valid_years.empty else 2025
else:
    YEAR_MIN = 1980
    YEAR_MAX = 2025


SOURCE_MODELS = (
    sorted(
        TRACKS["driving_model"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )
    if not TRACKS.empty
    else []
)

for source_model in SOURCE_MODELS:
    if source_model not in ALL_MODELS:
        ALL_MODELS.append(source_model)


# =============================================================================
# GENERAL HELPERS
# =============================================================================

def options(values: list[str]) -> list[dict[str, str]]:
    return [
        {
            "label": value,
            "value": value,
        }
        for value in values
    ]


def unique_sorted(column: str) -> list[str]:
    if TRACKS.empty or column not in TRACKS.columns:
        return []

    return sorted(
        TRACKS[column]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )


def clean_selected_models(models: object) -> list[str]:
    if not models:
        return []

    if isinstance(models, str):
        models = [models]

    cleaned: list[str] = []
    seen: set[str] = set()

    for model in models:
        if model is None:
            continue

        value = str(model).strip()

        if value and value not in seen:
            cleaned.append(value)
            seen.add(value)

    return cleaned


def models_present_in_data(
    dataset: Optional[str],
    tracker: Optional[str],
) -> list[str]:
    if not dataset or not tracker or TRACKS.empty:
        return []

    selected = TRACKS[
        TRACKS["dataset"].eq(str(dataset).upper())
        & TRACKS["tracker"].eq(str(tracker).upper())
    ]

    return sorted(
        selected["driving_model"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )


def configured_models(
    dataset: Optional[str],
    tracker: Optional[str],
) -> list[str]:
    key = (
        str(dataset or "").upper(),
        str(tracker or "").upper(),
    )

    return MODEL_GUIDE.get(key, [])


def available_models(
    dataset: Optional[str],
    tracker: Optional[str],
) -> list[str]:
    configured = configured_models(dataset, tracker)
    loaded = set(models_present_in_data(dataset, tracker))

    return [
        model
        for model in configured
        if model in loaded
    ]


def build_model_options(
    dataset: Optional[str],
    tracker: Optional[str],
    selected_elsewhere: Optional[set[str]] = None,
    current_value: Optional[str] = None,
) -> list[dict]:
    selected_elsewhere = selected_elsewhere or set()

    configured = set(configured_models(dataset, tracker))
    loaded = set(models_present_in_data(dataset, tracker))
    valid = configured & loaded

    model_options: list[dict] = []

    for model in ALL_MODELS:
        number = MODEL_NUMBER_GUIDE.get(
            (
                str(dataset or "").upper(),
                str(tracker or "").upper(),
                model,
            )
        )

        number_prefix = f"{number}. " if number is not None else ""

        if model not in configured:
            label = (
                f"{number_prefix}{model} — unavailable for "
                f"{dataset} + {tracker}"
            )
            unavailable = True
        elif model not in loaded:
            label = (
                f"{number_prefix}{model} — not found in loaded data"
            )
            unavailable = True
        else:
            label = f"{number_prefix}{model}"
            unavailable = False

        duplicate = (
            model in selected_elsewhere
            and model != current_value
        )

        model_options.append(
            {
                "label": label,
                "value": model,
                "disabled": unavailable or duplicate,
            }
        )

    return model_options


def stat_card(
    title: str,
    value_id: str,
    note_id: str,
    icon: str,
) -> html.Div:
    return html.Div(
        className="stat-card",
        children=[
            html.Div(
                icon,
                className="stat-icon",
                **{"aria-hidden": "true"},
            ),
            html.Div(
                [
                    html.P(title, className="stat-title"),
                    html.H2(id=value_id, className="stat-value"),
                    html.P(id=note_id, className="stat-note"),
                ]
            ),
        ],
    )


def empty_figure(
    message: str,
    height: int = 340,
) -> go.Figure:
    figure = go.Figure()

    figure.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={
            "size": 15,
            "color": "#64748b",
        },
    )

    figure.update_layout(
        template="plotly_white",
        height=height,
        autosize=True,
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return figure


# =============================================================================
# FILTERING
# =============================================================================

def filter_tracks(
    dataset: Optional[str],
    regions: object,
    scenarios: object,
    tracker: Optional[str],
    models: object,
    years: list[int],
    minimum_category: int,
) -> pd.DataFrame:
    if TRACKS.empty:
        return TRACKS.copy()

    selected = TRACKS.copy()
    selected_models = clean_selected_models(models)

    if dataset:
        selected = selected[
            selected["dataset"].eq(str(dataset).upper())
        ]

    if tracker:
        selected = selected[
            selected["tracker"].eq(str(tracker).upper())
        ]

    if regions:
        if isinstance(regions, str):
            regions = [regions]

        selected = selected[
            selected["region"].isin(regions)
        ]

    if scenarios:
        if isinstance(scenarios, str):
            scenarios = [scenarios]

        normalised_scenarios = [
            str(scenario).strip().lower()
            for scenario in scenarios
        ]

        selected = selected[
            selected["scenario"]
            .astype(str)
            .str.lower()
            .isin(normalised_scenarios)
        ]

    if selected_models:
        selected = selected[
            selected["driving_model"].isin(selected_models)
        ]
    else:
        return selected.iloc[0:0].copy()

    if years and len(years) == 2:
        start_year, end_year = years

        selected = selected[
            selected["analysis_year"].between(
                start_year,
                end_year,
                inclusive="both",
            )
        ]

    selected = selected[
        selected["max_category"].ge(
            int(minimum_category or 0)
        )
    ]

    return selected.copy()


def points_for_tracks(
    selected_tracks: pd.DataFrame,
) -> pd.DataFrame:
    """
    Return only point observations belonging to the filtered track records.

    This ensures that the density heat maps use the active filters instead of
    the complete unfiltered POINTS DataFrame.
    """

    if selected_tracks.empty or POINTS.empty:
        return POINTS.iloc[0:0].copy()

    selected_ids = selected_tracks[
        "track_id"
    ].dropna().unique()

    return POINTS[
        POINTS["track_id"].isin(selected_ids)
    ].copy()


# =============================================================================
# ANALYTICAL FIGURES
# =============================================================================

def create_frequency_figure(
    selected: pd.DataFrame,
) -> go.Figure:
    if selected.empty:
        return empty_figure("No frequency data match the filters")

    frequency = (
        selected
        .dropna(
            subset=[
                "analysis_year",
                "driving_model",
                "track_id",
            ]
        )
        .groupby(
            [
                "driving_model",
                "analysis_year",
            ],
            as_index=False,
        )["track_id"]
        .nunique()
        .rename(
            columns={
                "analysis_year": "season",
                "track_id": "cyclones",
            }
        )
    )

    if frequency.empty:
        return empty_figure("No frequency data match the filters")

    figure = px.line(
        frequency,
        x="season",
        y="cyclones",
        color="driving_model",
        markers=True,
        color_discrete_sequence=MODEL_COLOURS,
        labels={
            "season": "Season",
            "cyclones": "Cyclone tracks",
            "driving_model": "Driving model",
        },
    )

    figure.update_traces(
        line={"width": 2.4},
        marker={"size": 6},
    )

    figure.update_layout(
        template="plotly_white",
        height=390,
        autosize=True,
        margin={
            "l": 55,
            "r": 25,
            "t": 20,
            "b": 50,
        },
        xaxis_title="Season",
        yaxis_title="Unique cyclone tracks",
        hovermode="x unified",
        legend_title_text="Driving model",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    figure.update_yaxes(
        rangemode="tozero",
        dtick=1,
    )

    return figure


def create_intensity_figure(
    selected: pd.DataFrame,
) -> go.Figure:
    if selected.empty:
        return empty_figure("No intensity data match the filters")

    intensity = (
        selected[
            [
                "track_id",
                "driving_model",
                "max_wind_speed",
            ]
        ]
        .drop_duplicates(subset=["track_id"])
        .copy()
    )

    intensity["max_wind_speed"] = pd.to_numeric(
        intensity["max_wind_speed"],
        errors="coerce",
    )

    intensity = intensity.dropna(
        subset=[
            "driving_model",
            "max_wind_speed",
        ]
    )

    if intensity.empty:
        return empty_figure("No intensity data match the filters")

    figure = px.box(
        intensity,
        x="driving_model",
        y="max_wind_speed",
        color="driving_model",
        points="outliers",
        color_discrete_sequence=MODEL_COLOURS,
        labels={
            "driving_model": "Driving model",
            "max_wind_speed": "Peak wind speed (km/h)",
        },
    )

    figure.update_layout(
        template="plotly_white",
        height=390,
        autosize=True,
        margin={
            "l": 60,
            "r": 25,
            "t": 20,
            "b": 95,
        },
        xaxis_title=None,
        yaxis_title="Peak wind speed (km/h)",
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    figure.update_yaxes(rangemode="tozero")

    return figure


def create_longevity_figure(
    selected: pd.DataFrame,
) -> go.Figure:
    if selected.empty:
        return empty_figure("No longevity data match the filters")

    longevity = (
        selected[
            [
                "track_id",
                "driving_model",
                "lifetime_hours",
            ]
        ]
        .drop_duplicates(subset=["track_id"])
        .copy()
    )

    longevity["lifetime_hours"] = pd.to_numeric(
        longevity["lifetime_hours"],
        errors="coerce",
    )

    longevity = longevity[
        longevity["lifetime_hours"].notna()
        & longevity["lifetime_hours"].ge(0)
    ]

    longevity["lifetime_days"] = (
        longevity["lifetime_hours"] / 24.0
    )

    if longevity.empty:
        return empty_figure("No longevity data match the filters")

    figure = px.box(
        longevity,
        x="driving_model",
        y="lifetime_days",
        color="driving_model",
        points="outliers",
        color_discrete_sequence=MODEL_COLOURS,
        labels={
            "driving_model": "Driving model",
            "lifetime_days": "Duration (days)",
        },
    )

    figure.update_layout(
        template="plotly_white",
        height=390,
        autosize=True,
        margin={
            "l": 60,
            "r": 25,
            "t": 20,
            "b": 95,
        },
        xaxis_title=None,
        yaxis_title="Cyclone duration (days)",
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    figure.update_yaxes(rangemode="tozero")

    return figure


def create_density_figure(
    density_points: pd.DataFrame,
    model: str,
) -> go.Figure:
    if density_points.empty:
        return empty_figure(
            f"No mapped observations match the filters for {model}",
            height=500,
        )

    mapped = density_points[
        density_points["lat"].between(-48, 2)
        & density_points["lon"].between(105, 165)
    ].copy()

    mapped = mapped.dropna(
        subset=[
            "lat",
            "lon",
        ]
    )

    if mapped.empty:
        return empty_figure(
            f"No Australian-region observations are available for {model}",
            height=500,
        )

    max_points = 75_000

    if len(mapped) > max_points:
        mapped = mapped.sample(
            max_points,
            random_state=42,
        )

    try:
        figure = px.density_map(
            mapped,
            lat="lat",
            lon="lon",
            radius=9,
            center={
                "lat": -24.5,
                "lon": 134.5,
            },
            zoom=2.65,
            map_style="carto-positron",
            color_continuous_scale=[
                [0.0, "rgba(23,105,170,0.00)"],
                [0.20, "#8ecae6"],
                [0.50, "#219ebc"],
                [0.75, "#ffb703"],
                [1.0, "#d62828"],
            ],
        )
    except (AttributeError, TypeError):
        figure = px.density_mapbox(
            mapped,
            lat="lat",
            lon="lon",
            radius=9,
            center={
                "lat": -24.5,
                "lon": 134.5,
            },
            zoom=2.65,
            mapbox_style="carto-positron",
            color_continuous_scale=[
                [0.0, "rgba(23,105,170,0.00)"],
                [0.20, "#8ecae6"],
                [0.50, "#219ebc"],
                [0.75, "#ffb703"],
                [1.0, "#d62828"],
            ],
        )

    figure.update_layout(
        height=500,
        autosize=True,
        margin={
            "l": 0,
            "r": 0,
            "t": 0,
            "b": 0,
        },
        paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar={
            "title": "Density",
            "thickness": 14,
        },
        uirevision=f"australia-density-map-{model}",
    )

    return figure


# =============================================================================
# DASH APPLICATION
# =============================================================================

app = Dash(
    __name__,
    title="TC Explorer 2.0",
    suppress_callback_exceptions=True,
    assets_folder=str(ASSETS_DIR),
)

server = app.server


# =============================================================================
# LAYOUT
# =============================================================================

app.layout = html.Div(
    className="app-shell",
    children=[
        dcc.Store(
            id="filtered-track-ids",
            data=[],
        ),
        dcc.Store(
            id="selected-models-store",
            data=[],
        ),
        dcc.Download(id="download-csv"),

        html.Header(
            className="topbar",
            children=[
                html.Div(
                    className="brand",
                    children=[
                        html.Div(
                            "TC",
                            className="brand-mark",
                        ),
                        html.Div(
                            [
                                html.H1("TC Explorer 2.0"),
                                html.P(
                                    "Tropical cyclone analysis dashboard"
                                ),
                            ]
                        ),
                    ],
                ),
                html.Div(
                    className="topbar-actions",
                    children=[
                        html.Div(
                            [
                                html.Span(className="status-dot"),
                                html.Span(
                                    "Real data loaded"
                                    if DATA_LOAD_ERROR is None
                                    else "Data load failed — see console"
                                ),
                            ],
                            className="data-status",
                        ),
                        html.Button(
                            "Download CSV",
                            id="export-button",
                            className="button button-secondary",
                        ),
                    ],
                ),
            ],
        ),

        html.Div(
            className="dashboard-grid",
            children=[
                html.Aside(
                    className="sidebar",
                    children=[
                        html.Div(
                            [
                                html.H2("Filters"),
                                html.P(
                                    "Refine the dashboard using the controls below."
                                ),
                            ],
                            className="sidebar-heading",
                        ),

                        html.Label("Dataset"),
                        dcc.Dropdown(
                            id="dataset-filter",
                            options=options(
                                unique_sorted("dataset")
                            ),
                            value=(
                                unique_sorted("dataset")[0]
                                if unique_sorted("dataset")
                                else None
                            ),
                            multi=False,
                            searchable=False,
                            clearable=False,
                            placeholder="Select dataset",
                            className="filter-dropdown",
                        ),

                        html.Label("Region"),
                        dcc.Dropdown(
                            id="region-filter",
                            options=options(
                                unique_sorted("region")
                            ),
                            value=unique_sorted("region"),
                            multi=True,
                            clearable=False,
                            className="filter-dropdown",
                        ),

                        html.Label("Scenario"),
                        dcc.Dropdown(
                            id="scenario-filter",
                            options=options(
                                unique_sorted("scenario")
                            ),
                            value=unique_sorted("scenario"),
                            multi=True,
                            clearable=False,
                            className="filter-dropdown",
                        ),

                        html.Label("Cyclone tracker"),
                        dcc.Dropdown(
                            id="tracker-filter",
                            options=options(
                                unique_sorted("tracker")
                            ),
                            value=(
                                unique_sorted("tracker")[0]
                                if unique_sorted("tracker")
                                else None
                            ),
                            multi=False,
                            searchable=False,
                            clearable=False,
                            placeholder="Select tracker",
                            className="filter-dropdown",
                        ),

                        html.Label("Number of models"),
                        dcc.Dropdown(
                            id="model-count-filter",
                            options=[
                                {
                                    "label": "1 model",
                                    "value": 1,
                                },
                            ],
                            value=1,
                            multi=False,
                            searchable=False,
                            clearable=False,
                            className="filter-dropdown",
                        ),

                        html.Div(
                            id="model-selectors-container",
                            style={
                                "display": "grid",
                                "gap": "14px",
                                "marginTop": "14px",
                            },
                        ),

                        html.Div(
                            id="model-availability-message",
                            className="filter-message",
                            role="status",
                            **{"aria-live": "polite"},
                        ),

                        html.Div(
                            [
                                html.Label("Year range"),
                                html.Span(id="year-label"),
                            ],
                            className="label-row",
                        ),

                        dcc.RangeSlider(
                            id="year-filter",
                            min=YEAR_MIN,
                            max=YEAR_MAX,
                            value=[
                                YEAR_MIN,
                                YEAR_MAX,
                            ],
                            step=1,
                            marks={
                                YEAR_MIN: str(YEAR_MIN),
                                YEAR_MAX: str(YEAR_MAX),
                            },
                        ),

                        html.Label("Minimum category"),
                        dcc.Slider(
                            id="category-filter",
                            min=0,
                            max=5,
                            value=0,
                            step=1,
                            marks={
                                category: str(category)
                                for category in range(6)
                            },
                        ),

                        html.Div(
                            className="sidebar-buttons",
                            children=[
                                html.Button(
                                    "Apply filters",
                                    id="apply-filters",
                                    className="button button-primary",
                                ),
                                html.Button(
                                    "Reset",
                                    id="reset-filters",
                                    className="button button-ghost",
                                ),
                            ],
                        ),

                        html.Div(
                            className="sidebar-footnote",
                            children=[
                                html.Strong("Data source"),
                                html.P(
                                    (
                                        "Tracks are loaded from CSV files in "
                                        "data/ through DataManager → Ingestor "
                                        "→ loaders → TCRecord."
                                    )
                                    if DATA_LOAD_ERROR is None
                                    else (
                                        f"Data load error: "
                                        f"{DATA_LOAD_ERROR}"
                                    )
                                ),
                            ],
                        ),
                    ],
                ),

                html.Main(
                    className="main-content",
                    children=[
                        html.Section(
                            className="page-heading",
                            children=[
                                html.Div(
                                    [
                                        html.P(
                                            "OVERVIEW",
                                            className="eyebrow",
                                        ),
                                        html.H2(
                                            "Cyclone activity dashboard"
                                        ),
                                    ]
                                ),
                                html.P(
                                    id="result-summary",
                                    className="result-summary",
                                ),
                            ],
                        ),

                        html.Section(
                            className="stat-grid",
                            children=[
                                stat_card(
                                    "Total cyclones",
                                    "total-cyclones",
                                    "total-note",
                                    "\u25c9",
                                ),
                                stat_card(
                                    "Landfalls",
                                    "total-landfalls",
                                    "landfall-note",
                                    "\u2316",
                                ),
                                stat_card(
                                    "Average wind",
                                    "average-wind",
                                    "wind-note",
                                    "\u2197",
                                ),
                                stat_card(
                                    "Average lifetime",
                                    "average-lifetime",
                                    "lifetime-note",
                                    "\u25f7",
                                ),
                            ],
                        ),

                        html.Section(
                            className="chart-grid",
                            children=[
                                html.Div(
                                    className="panel chart-panel",
                                    style={
                                        "gridColumn": "1 / -1",
                                    },
                                    children=[
                                        html.Div(
                                            [
                                                html.H3(
                                                    "Frequency comparison"
                                                ),
                                                html.P(
                                                    "Unique cyclone tracks "
                                                    "per season for each model"
                                                ),
                                            ],
                                            className="panel-heading compact",
                                        ),
                                        dcc.Loading(
                                            dcc.Graph(
                                                id="frequency-chart",
                                                config={
                                                    "displaylogo": False,
                                                    "responsive": True,
                                                },
                                                style={
                                                    "height": "390px",
                                                },
                                            ),
                                            type="circle",
                                        ),
                                    ],
                                ),

                                html.Div(
                                    className="panel chart-panel",
                                    children=[
                                        html.Div(
                                            [
                                                html.H3(
                                                    "Intensity comparison"
                                                ),
                                                html.P(
                                                    "Peak wind-speed "
                                                    "distribution by model"
                                                ),
                                            ],
                                            className="panel-heading compact",
                                        ),
                                        dcc.Loading(
                                            dcc.Graph(
                                                id="intensity-chart",
                                                config={
                                                    "displaylogo": False,
                                                    "responsive": True,
                                                },
                                                style={
                                                    "height": "390px",
                                                },
                                            ),
                                            type="circle",
                                        ),
                                    ],
                                ),

                                html.Div(
                                    className="panel chart-panel",
                                    children=[
                                        html.Div(
                                            [
                                                html.H3(
                                                    "Longevity comparison"
                                                ),
                                                html.P(
                                                    "Cyclone duration "
                                                    "distribution by model"
                                                ),
                                            ],
                                            className="panel-heading compact",
                                        ),
                                        dcc.Loading(
                                            dcc.Graph(
                                                id="longevity-chart",
                                                config={
                                                    "displaylogo": False,
                                                    "responsive": True,
                                                },
                                                style={
                                                    "height": "390px",
                                                },
                                            ),
                                            type="circle",
                                        ),
                                    ],
                                ),
                            ],
                        ),

                        html.Section(
                            className="panel heatmap-panel",
                            children=[
                                html.Div(
                                    className="panel-heading",
                                    children=[
                                        html.Div(
                                            [
                                                html.H3(
                                                    "Filtered track-density "
                                                    "comparison"
                                                ),
                                                html.P(
                                                    "Each map uses only the "
                                                    "cyclone observations "
                                                    "matching the active "
                                                    "filters."
                                                ),
                                            ]
                                        ),
                                    ],
                                ),
                                dcc.Loading(
                                    html.Div(
                                        id="density-heatmaps",
                                        style={
                                            "display": "grid",
                                            "gridTemplateColumns": (
                                                "repeat("
                                                "auto-fit, "
                                                "minmax("
                                                "min(520px, 100%), "
                                                "1fr"
                                                ")"
                                                ")"
                                            ),
                                            "gap": "20px",
                                        },
                                    ),
                                    type="circle",
                                ),
                            ],
                        ),

                        html.Section(
                            className="panel table-panel",
                            children=[
                                html.Div(
                                    className="panel-heading",
                                    children=[
                                        html.Div(
                                            [
                                                html.H3(
                                                    "Strongest cyclone records"
                                                ),
                                                html.P(
                                                    "Select one cyclone to "
                                                    "display its track below."
                                                ),
                                            ]
                                        ),
                                        dcc.Dropdown(
                                            id="selected-cyclone",
                                            placeholder=(
                                                "Select a cyclone..."
                                            ),
                                            clearable=True,
                                            className=(
                                                "cyclone-selector"
                                            ),
                                        ),
                                    ],
                                ),
                                html.Div(
                                    id="records-table",
                                    className="table-wrap",
                                ),
                            ],
                        ),

                        html.Section(
                            className="panel selected-map-panel",
                            children=[
                                html.Div(
                                    className="panel-heading",
                                    children=[
                                        html.Div(
                                            [
                                                html.H3(
                                                    "Selected cyclone track"
                                                ),
                                                html.P(
                                                    "Track shown over an "
                                                    "Australia reference map"
                                                ),
                                            ]
                                        ),
                                        html.Div(
                                            id=(
                                                "selected-cyclone-summary"
                                            ),
                                            className="selected-summary",
                                        ),
                                    ],
                                ),
                                dcc.Loading(
                                    dcc.Graph(
                                        id="cyclone-map",
                                        config={
                                            "displaylogo": False,
                                            "responsive": True,
                                        },
                                        style={
                                            "height": "430px",
                                        },
                                    ),
                                    type="circle",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
    ],
)


# =============================================================================
# BASIC FILTER CALLBACKS
# =============================================================================

@callback(
    Output("year-label", "children"),
    Input("year-filter", "value"),
)
def show_year_range(years):
    if not years or len(years) != 2:
        return ""

    return f"{years[0]}\u2013{years[1]}"


@callback(
    Output("model-count-filter", "options"),
    Output("model-count-filter", "value"),
    Input("dataset-filter", "value"),
    Input("tracker-filter", "value"),
    Input("reset-filters", "n_clicks"),
    State("model-count-filter", "value"),
)
def update_model_count_options(
    dataset,
    tracker,
    _reset_clicks,
    current_count,
):
    available = available_models(dataset, tracker)
    maximum = max(1, len(available))

    count_options = [
        {
            "label": (
                f"{number} model"
                if number == 1
                else f"{number} models"
            ),
            "value": number,
        }
        for number in range(1, maximum + 1)
    ]

    if ctx.triggered_id == "reset-filters":
        desired_count = min(2, maximum)
    else:
        desired_count = int(current_count or 1)
        desired_count = min(
            max(desired_count, 1),
            maximum,
        )

    return count_options, desired_count


@callback(
    Output("model-selectors-container", "children"),
    Output("model-availability-message", "children"),
    Input("model-count-filter", "value"),
    Input("dataset-filter", "value"),
    Input("tracker-filter", "value"),
    State(
        {
            "type": "comparison-model-selector",
            "index": ALL,
        },
        "value",
    ),
)
def render_model_selectors(
    model_count,
    dataset,
    tracker,
    existing_values,
):
    requested_count = int(model_count or 1)
    configured = configured_models(dataset, tracker)
    loaded = set(models_present_in_data(dataset, tracker))
    available = available_models(dataset, tracker)

    if not dataset or not tracker:
        return (
            [],
            "Choose a dataset and tracker to view available models.",
        )

    if not configured:
        return (
            [],
            (
                f"No model guide is configured for "
                f"{dataset} + {tracker}."
            ),
        )

    if not available:
        return (
            [],
            (
                f"No configured models are present in the loaded "
                f"data for {dataset} + {tracker}."
            ),
        )

    requested_count = min(
        requested_count,
        len(available),
    )

    preserved = [
        model
        for model in clean_selected_models(existing_values)
        if model in available
    ][:requested_count]

    for model in available:
        if len(preserved) >= requested_count:
            break

        if model not in preserved:
            preserved.append(model)

    selectors = []

    for index in range(requested_count):
        current_value = preserved[index]
        selected_elsewhere = set(preserved)
        selected_elsewhere.discard(current_value)

        selectors.append(
            html.Div(
                [
                    html.Label(
                        f"Model {index + 1}",
                    ),
                    dcc.Dropdown(
                        id={
                            "type": (
                                "comparison-model-selector"
                            ),
                            "index": index,
                        },
                        options=build_model_options(
                            dataset,
                            tracker,
                            selected_elsewhere=selected_elsewhere,
                            current_value=current_value,
                        ),
                        value=current_value,
                        multi=False,
                        searchable=True,
                        clearable=False,
                        placeholder=(
                            f"Select model {index + 1}"
                        ),
                        className=(
                            "filter-dropdown model-dropdown"
                        ),
                    ),
                ],
                style={
                    "display": "grid",
                    "gap": "7px",
                },
            )
        )

    unavailable = [
        model
        for model in configured
        if model not in loaded
    ]

    message = (
        f"{len(available)} models available for "
        f"{dataset} + {tracker}."
    )

    if unavailable:
        message += (
            " Not found in the loaded data: "
            + ", ".join(unavailable)
            + "."
        )

    return selectors, message


@callback(
    Output(
        {
            "type": "comparison-model-selector",
            "index": ALL,
        },
        "options",
    ),
    Input(
        {
            "type": "comparison-model-selector",
            "index": ALL,
        },
        "value",
    ),
    State("dataset-filter", "value"),
    State("tracker-filter", "value"),
    prevent_initial_call=True,
)
def disable_duplicate_model_options(
    selected_values,
    dataset,
    tracker,
):
    selected_values = selected_values or []
    selected_models = clean_selected_models(
        selected_values
    )

    output_options = []

    for current_value in selected_values:
        selected_elsewhere = set(selected_models)
        selected_elsewhere.discard(current_value)

        output_options.append(
            build_model_options(
                dataset,
                tracker,
                selected_elsewhere=selected_elsewhere,
                current_value=current_value,
            )
        )

    return output_options


@callback(
    Output("selected-models-store", "data"),
    Input(
        {
            "type": "comparison-model-selector",
            "index": ALL,
        },
        "value",
    ),
)
def store_selected_models(selected_values):
    return clean_selected_models(selected_values)


@callback(
    Output("dataset-filter", "value"),
    Output("region-filter", "value"),
    Output("scenario-filter", "value"),
    Output("tracker-filter", "value"),
    Output("year-filter", "value"),
    Output("category-filter", "value"),
    Input("reset-filters", "n_clicks"),
    prevent_initial_call=True,
)
def reset_filters(_):
    datasets = unique_sorted("dataset")
    trackers = unique_sorted("tracker")

    return (
        datasets[0] if datasets else None,
        unique_sorted("region"),
        unique_sorted("scenario"),
        trackers[0] if trackers else None,
        [
            YEAR_MIN,
            YEAR_MAX,
        ],
        0,
    )


# =============================================================================
# MAIN DASHBOARD CALLBACK
# =============================================================================

@callback(
    Output("filtered-track-ids", "data"),
    Output("total-cyclones", "children"),
    Output("total-note", "children"),
    Output("total-landfalls", "children"),
    Output("landfall-note", "children"),
    Output("average-wind", "children"),
    Output("wind-note", "children"),
    Output("average-lifetime", "children"),
    Output("lifetime-note", "children"),
    Output("result-summary", "children"),
    Output("frequency-chart", "figure"),
    Output("intensity-chart", "figure"),
    Output("longevity-chart", "figure"),
    Output("records-table", "children"),
    Output("selected-cyclone", "options"),
    Output("selected-cyclone", "value"),
    Input("apply-filters", "n_clicks"),
    Input("reset-filters", "n_clicks"),
    Input("dataset-filter", "value"),
    Input("region-filter", "value"),
    Input("scenario-filter", "value"),
    Input("tracker-filter", "value"),
    Input("selected-models-store", "data"),
    Input("year-filter", "value"),
    Input("category-filter", "value"),
    State("selected-cyclone", "value"),
)
def update_dashboard(
    _apply_clicks,
    _reset_clicks,
    dataset,
    regions,
    scenarios,
    tracker,
    models,
    years,
    minimum_category,
    current_cyclone,
):
    selected_models = clean_selected_models(models)

    selected = filter_tracks(
        dataset=dataset,
        regions=regions,
        scenarios=scenarios,
        tracker=tracker,
        models=selected_models,
        years=years,
        minimum_category=minimum_category,
    )

    ids = selected["track_id"].tolist()

    if selected.empty:
        message = (
            "No cyclone records match the selected filters."
            if DATA_LOAD_ERROR is None
            else f"No data loaded. {DATA_LOAD_ERROR}"
        )

        table = html.Div(
            message,
            className="empty-state",
        )

        return (
            [],
            "0",
            "No matching records",
            "0",
            "0% of selection",
            "\u2014",
            "No data",
            "\u2014",
            "No data",
            "No records found",
            empty_figure("No frequency data"),
            empty_figure("No intensity data"),
            empty_figure("No longevity data"),
            table,
            [],
            None,
        )

    count = len(selected)
    landfalls = int(selected["landfall"].sum())
    landfall_rate = (
        landfalls / count * 100
        if count
        else 0
    )

    average_wind = selected[
        "max_wind_speed"
    ].mean()

    average_lifetime = selected[
        "lifetime_hours"
    ].mean()

    frequency_figure = create_frequency_figure(
        selected
    )

    intensity_figure = create_intensity_figure(
        selected
    )

    longevity_figure = create_longevity_figure(
        selected
    )

    top = selected.sort_values(
        [
            "max_category",
            "max_wind_speed",
        ],
        ascending=False,
    ).head(12)

    rows = []

    for _, row in top.iterrows():
        cyclone_name = (
            f"Cyclone {row['raw_track_id']} "
            f"({row['season']})"
        )

        category = int(row["max_category"])

        rows.append(
            html.Tr(
                [
                    html.Td(
                        [
                            html.Strong(cyclone_name),
                            html.Small(
                                (
                                    f"{row['dataset']} · "
                                    f"{row['tracker']} · "
                                    f"{row['driving_model']}"
                                ),
                                className="track-meta",
                            ),
                        ],
                        title=row["track_id"],
                    ),
                    html.Td(row["dataset"]),
                    html.Td(row["driving_model"]),
                    html.Td(row["tracker"]),
                    html.Td(row["region"]),
                    html.Td(str(row["season"])),
                    html.Td(
                        html.Span(
                            f"Category {category}",
                            className=(
                                f"category-pill "
                                f"category-{category}"
                            ),
                        )
                    ),
                    html.Td(
                        f"{row['max_wind_speed']:.0f} km/h"
                    ),
                    html.Td(
                        f"{row['lifetime_hours']:.0f} h"
                    ),
                    html.Td(
                        "Yes"
                        if row["landfall"]
                        else "No"
                    ),
                ]
            )
        )

    table = html.Table(
        [
            html.Thead(
                html.Tr(
                    [
                        html.Th("Track"),
                        html.Th("Dataset"),
                        html.Th("Model"),
                        html.Th("Tracker"),
                        html.Th("Region"),
                        html.Th("Season"),
                        html.Th("Intensity"),
                        html.Th("Peak wind"),
                        html.Th("Lifetime"),
                        html.Th("Landfall"),
                    ]
                )
            ),
            html.Tbody(rows),
        ]
    )

    selector_options = [
        {
            "label": (
                f"Cyclone {row['raw_track_id']} "
                f"({row['season']}) — "
                f"{row['dataset']} / "
                f"{row['tracker']} / "
                f"{row['driving_model']} — "
                f"Category {int(row['max_category'])} — "
                f"{row['max_wind_speed']:.0f} km/h"
            ),
            "value": row["track_id"],
        }
        for _, row in top.iterrows()
    ]

    available_selector_ids = {
        item["value"]
        for item in selector_options
    }

    if current_cyclone in available_selector_ids:
        selected_cyclone_value = current_cyclone
    elif selector_options:
        selected_cyclone_value = (
            selector_options[0]["value"]
        )
    else:
        selected_cyclone_value = None

    model_text = ", ".join(
        selected["driving_model"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    return (
        ids,
        f"{count:,}",
        (
            f"{dataset} · {tracker} · "
            f"{selected['driving_model'].nunique()} model(s)"
        ),
        f"{landfalls:,}",
        f"{landfall_rate:.1f}% of selection",
        f"{average_wind:.0f} km/h",
        (
            f"Peak "
            f"{selected['max_wind_speed'].max():.0f} km/h"
        ),
        f"{average_lifetime:.0f} h",
        (
            f"Median "
            f"{selected['lifetime_hours'].median():.0f} hours"
        ),
        (
            f"Showing {count:,} records from "
            f"{years[0]} to {years[1]} · "
            f"{model_text}"
        ),
        frequency_figure,
        intensity_figure,
        longevity_figure,
        table,
        selector_options,
        selected_cyclone_value,
    )


# =============================================================================
# FILTERED DENSITY MAPS
# =============================================================================

@callback(
    Output("density-heatmaps", "children"),
    Input("filtered-track-ids", "data"),
    Input("selected-models-store", "data"),
)
def update_density_heatmaps(
    track_ids,
    selected_models,
):
    models = clean_selected_models(selected_models)

    if not track_ids or not models:
        return [
            html.Div(
                "Select at least one model and apply the filters.",
                className="empty-state",
            )
        ]

    filtered_tracks = TRACKS[
        TRACKS["track_id"].isin(track_ids)
    ].copy()

    filtered_points = points_for_tracks(
        filtered_tracks
    )

    heatmap_cards = []

    for model in models:
        model_track_ids = filtered_tracks.loc[
            filtered_tracks[
                "driving_model"
            ].eq(model),
            "track_id",
        ].unique()

        model_points = filtered_points[
            filtered_points["track_id"].isin(
                model_track_ids
            )
        ].copy()

        card = html.Div(
            className="panel chart-panel",
            children=[
                html.Div(
                    [
                        html.H3(
                            f"{model} track density"
                        ),
                        html.P(
                            (
                                f"{len(model_track_ids):,} filtered "
                                f"cyclone tracks · "
                                f"{len(model_points):,} observations"
                            )
                        ),
                    ],
                    className="panel-heading compact",
                ),
                dcc.Graph(
                    figure=create_density_figure(
                        model_points,
                        model,
                    ),
                    config={
                        "displaylogo": False,
                        "responsive": True,
                    },
                    style={
                        "height": "500px",
                    },
                ),
            ],
        )

        heatmap_cards.append(card)

    return heatmap_cards


# =============================================================================
# SELECTED CYCLONE MAP
# =============================================================================

@callback(
    Output("cyclone-map", "figure"),
    Output("selected-cyclone-summary", "children"),
    Input("selected-cyclone", "value"),
)
def update_selected_map(selected_cyclone):
    if not selected_cyclone:
        return (
            empty_figure(
                "Select one cyclone above to display its track",
                height=430,
            ),
            "No cyclone selected",
        )

    record_frame = TRACKS[
        TRACKS["track_id"].eq(selected_cyclone)
    ]

    cyclone_points = POINTS[
        POINTS["track_id"].eq(selected_cyclone)
    ].sort_values("step")

    if record_frame.empty or cyclone_points.empty:
        return (
            empty_figure(
                "Selected cyclone data is unavailable",
                height=430,
            ),
            "Data unavailable",
        )

    record = record_frame.iloc[0]

    category = int(
        max(
            0,
            min(
                5,
                record["max_category"],
            ),
        )
    )

    cyclone_name = (
        f"Cyclone {record['raw_track_id']} "
        f"({record['season']})"
    )

    figure = go.Figure()

    figure.add_trace(
        go.Scattergeo(
            lon=cyclone_points["lon"],
            lat=cyclone_points["lat"],
            mode="lines+markers",
            line={
                "width": 3,
                "color": CATEGORY_COLOURS[category],
            },
            marker={
                "size": 5,
                "color": CATEGORY_COLOURS[category],
            },
            name=cyclone_name,
            customdata=cyclone_points[
                [
                    "wind_speed",
                    "category",
                ]
            ],
            hovertemplate=(
                f"<b>{cyclone_name}</b>"
                "<br>Wind: %{customdata[0]:.0f} km/h"
                "<br>Category: %{customdata[1]}"
                "<extra></extra>"
            ),
        )
    )

    if pd.notna(record["genesis_lon"]) and pd.notna(
        record["genesis_lat"]
    ):
        figure.add_trace(
            go.Scattergeo(
                lon=[record["genesis_lon"]],
                lat=[record["genesis_lat"]],
                mode="markers",
                marker={
                    "size": 11,
                    "color": "#0f172a",
                    "line": {
                        "width": 2,
                        "color": "white",
                    },
                },
                name="Genesis",
                hovertemplate=(
                    "<b>Genesis point</b>"
                    "<extra></extra>"
                ),
            )
        )

    if (
        bool(record["landfall"])
        and pd.notna(record["last_lon"])
        and pd.notna(record["last_lat"])
    ):
        figure.add_trace(
            go.Scattergeo(
                lon=[record["last_lon"]],
                lat=[record["last_lat"]],
                mode="markers",
                marker={
                    "size": 12,
                    "symbol": "x",
                    "color": "#7c3aed",
                    "line": {
                        "width": 2,
                    },
                },
                name="Landfall endpoint",
                hovertemplate=(
                    "<b>Landfall endpoint</b>"
                    "<extra></extra>"
                ),
            )
        )

    figure.update_geos(
        projection_type="mercator",
        lonaxis_range=[
            105,
            165,
        ],
        lataxis_range=[
            -48,
            2,
        ],
        showland=True,
        landcolor="#e9eef3",
        showocean=True,
        oceancolor="#eaf7fb",
        showcoastlines=True,
        coastlinecolor="#94a3b8",
        showcountries=True,
        countrycolor="#cbd5e1",
        resolution=50,
    )

    figure.update_layout(
        height=430,
        autosize=True,
        margin={
            "l": 0,
            "r": 0,
            "t": 0,
            "b": 0,
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend={
            "orientation": "h",
            "y": 0.01,
            "x": 0.01,
            "bgcolor": "rgba(255,255,255,0.88)",
        },
        uirevision="selected-cyclone-map",
    )

    summary = (
        f"{cyclone_name} · "
        f"{record['dataset']} / "
        f"{record['tracker']} / "
        f"{record['driving_model']} · "
        f"Category {category} · "
        f"{record['max_wind_speed']:.0f} km/h"
    )

    return figure, summary


# =============================================================================
# EXPORT
# =============================================================================

@callback(
    Output("download-csv", "data"),
    Input("export-button", "n_clicks"),
    State("filtered-track-ids", "data"),
    prevent_initial_call=True,
)
def export_filtered_data(
    _clicks,
    ids,
):
    if not ids:
        return no_update

    export_columns = [
        "track_id",
        "name",
        "dataset",
        "driving_model",
        "raw_track_id",
        "season",
        "scenario",
        "region",
        "tracker",
        "year",
        "analysis_year",
        "max_category",
        "max_wind_speed",
        "lifetime_hours",
        "landfall",
        "genesis_date",
    ]

    available_columns = [
        column
        for column in export_columns
        if column in TRACKS.columns
    ]

    output = TRACKS[
        TRACKS["track_id"].isin(ids)
    ][available_columns].copy()

    return dcc.send_data_frame(
        output.to_csv,
        "tc_explorer_filtered_records.csv",
        index=False,
    )


# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    app.run(
        debug=False,
        host="0.0.0.0",
        port=8050,
    )