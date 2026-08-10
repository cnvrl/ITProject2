
"""
TC-Explorer 2.0 - Repository Analysis Runner
==================================================

This standalone script is for validating graphs and written interpretation
BEFORE integrating the logic into the main GitHub/FastAPI project.

For each selected dataset + tracker combination, it creates:

1. Frequency
2. Intensity
3. Duration / longevity
4. Track-density heat map

It also creates:
- comparison_frequency.png
- comparison_intensity.png
- comparison_longevity.png
- comparison_heatmaps.png
- comparison_summary.csv
- tc_interpretation_report.txt

NO CARTOPY REQUIRED.

Expected repository layout:

    ITPROJECT2/
    ├── app/
    ├── data/
    │   ├── barpa_cdd_all_ssp370.csv
    │   ├── barpa_te_all_ssp370.csv
    │   ├── ccam_cdd_all_ssp370.csv
    │   └── ccam_te_all_ssp370.csv
    └── analysis_tester/
        ├── tc_explorer_repo_analysis.py
        └── au_coastline_background.png

The analysis folder may have a different name. It only needs to sit directly
inside the repository root beside /data.

Run:
    python analysis_tester/tc_explorer_repo_analysis.py

or open this file in Spyder and press Run.
"""

from pathlib import Path
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# ============================================================
# USER SETTINGS
# ============================================================

SELECTED_DATASETS = ["BARPA", "CCAM"]
SELECTED_TRACKERS = ["CDD", "TE"]

# Optional filter using the CSV "Model" column.
# None = use all driving models.
# Example:
# SELECTED_DRIVING_MODELS = ["ACCESS-ESM1-5"]
SELECTED_DRIVING_MODELS = None

# Optional season filter.
# None = use the full available range.
START_SEASON = None
END_SEASON = None

# Heat-map grid resolution.
LON_BINS = 40
LAT_BINS = 30

# Geographic area represented by the coastline background.
# [west, east, south, north]
MAP_EXTENT = [100, 180, -60, 0]

COASTLINE_IMAGE = "au_coastline_background.png"

SAVE_FIGURES = True
SHOW_FIGURES = True


# ============================================================
# FILE CONFIGURATION
# ============================================================

FILES = {
    ("BARPA", "CDD"): "barpa_cdd_all_ssp370.csv",
    ("BARPA", "TE"): "barpa_te_all_ssp370.csv",
    ("CCAM", "CDD"): "ccam_cdd_all_ssp370.csv",
    ("CCAM", "TE"): "ccam_te_all_ssp370.csv",
}

# Final four GWL boolean columns are intentionally ignored.
USE_COLUMNS = [
    "Model",
    "Tracker",
    "TrackID",
    "Season",
    "Time",
    "Year",
    "Month",
    "Day",
    "Hour",
    "Lon",
    "Lat",
    "Wspd",
    "Pres",
]


# ============================================================
# GENERAL HELPERS
# ============================================================

def safe_filename(label):
    return (
        label.lower()
        .replace(" + ", "_")
        .replace(" ", "_")
        .replace("/", "_")
    )


def apply_clean_axis_style(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, alpha=0.18, linewidth=0.7)


def add_footer(fig, text):
    fig.text(
        0.5,
        0.02,
        text,
        ha="center",
        va="bottom",
        fontsize=9,
        alpha=0.7,
    )


# ============================================================
# DATA LOADING
# ============================================================

def load_csv(path):
    df = pd.read_csv(
        path,
        usecols=lambda c: c in USE_COLUMNS,
        low_memory=False,
    )

    required = {
        "Model",
        "TrackID",
        "Season",
        "Time",
        "Lon",
        "Lat",
        "Wspd",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"{Path(path).name} missing required columns: {sorted(missing)}"
        )

    df["Time"] = pd.to_datetime(
        df["Time"],
        errors="coerce",
        utc=True,
    )

    for col in ["Season", "Lon", "Lat", "Wspd", "Pres"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            )

    df = df.dropna(
        subset=[
            "Model",
            "TrackID",
            "Season",
            "Time",
            "Lon",
            "Lat",
            "Wspd",
        ]
    )

    df["Season"] = df["Season"].astype(int)

    return df


def apply_filters(df):
    out = df.copy()

    if SELECTED_DRIVING_MODELS is not None:
        out = out[
            out["Model"].isin(
                SELECTED_DRIVING_MODELS
            )
        ]

    if START_SEASON is not None:
        out = out[
            out["Season"] >= START_SEASON
        ]

    if END_SEASON is not None:
        out = out[
            out["Season"] <= END_SEASON
        ]

    return out


def track_keys():
    """
    Safer than TrackID alone because TrackID may repeat
    between driving models.
    """
    return ["Model", "TrackID"]


# ============================================================
# CORE CALCULATIONS
# ============================================================

def calculate_frequency(df):
    """
    Frequency = number of unique cyclone tracks per season.
    """

    unique_tracks = (
        df[
            track_keys() + ["Season"]
        ]
        .drop_duplicates()
    )

    return (
        unique_tracks
        .groupby(
            "Season",
            as_index=False,
        )
        .size()
        .rename(
            columns={
                "size": "Frequency"
            }
        )
        .sort_values("Season")
    )


def calculate_intensity(df):
    """
    Intensity = maximum Wspd reached by each cyclone track.
    """

    return (
        df
        .groupby(
            track_keys(),
            as_index=False,
        )["Wspd"]
        .max()
        .rename(
            columns={
                "Wspd": "MaxWind"
            }
        )
    )


def calculate_longevity(df):
    """
    Longevity = last observation time - first observation time.
    """

    result = (
        df
        .groupby(
            track_keys(),
            as_index=False,
        )["Time"]
        .agg(
            StartTime="min",
            EndTime="max",
        )
    )

    result["DurationDays"] = (
        result["EndTime"]
        -
        result["StartTime"]
    ).dt.total_seconds() / 86400.0

    return result


def calculate_density(df):
    """
    Track-point density using one common geographic grid.
    """

    west, east, south, north = MAP_EXTENT

    map_df = df[
        df["Lon"].between(
            west,
            east,
        )
        &
        df["Lat"].between(
            south,
            north,
        )
    ]

    lon_edges = np.linspace(
        west,
        east,
        LON_BINS + 1,
    )

    lat_edges = np.linspace(
        south,
        north,
        LAT_BINS + 1,
    )

    density, _, _ = np.histogram2d(
        map_df["Lat"].to_numpy(),
        map_df["Lon"].to_numpy(),
        bins=[
            lat_edges,
            lon_edges,
        ],
    )

    return density, lon_edges, lat_edges


# ============================================================
# COMPARISON CALCULATIONS
# ============================================================

def linear_trend(x, y):
    if len(x) < 2:
        return np.nan

    x = np.asarray(
        x,
        dtype=float,
    )

    y = np.asarray(
        y,
        dtype=float,
    )

    if np.all(x == x[0]):
        return np.nan

    slope, _ = np.polyfit(
        x,
        y,
        1,
    )

    return float(slope)


def percent_difference(value, reference):
    if (
        pd.isna(value)
        or
        pd.isna(reference)
        or
        reference == 0
    ):
        return np.nan

    return (
        (value - reference)
        /
        reference
        *
        100.0
    )


def hotspot_from_density(
    density,
    lon_edges,
    lat_edges,
):
    if (
        density.size == 0
        or
        density.max() <= 0
    ):
        return np.nan, np.nan, 0.0

    row, col = np.unravel_index(
        np.argmax(density),
        density.shape,
    )

    lon = (
        lon_edges[col]
        +
        lon_edges[col + 1]
    ) / 2

    lat = (
        lat_edges[row]
        +
        lat_edges[row + 1]
    ) / 2

    return (
        float(lon),
        float(lat),
        float(density[row, col]),
    )


def density_weighted_centre(
    density,
    lon_edges,
    lat_edges,
):
    total = density.sum()

    if total <= 0:
        return np.nan, np.nan

    lon_centres = (
        lon_edges[:-1]
        +
        lon_edges[1:]
    ) / 2

    lat_centres = (
        lat_edges[:-1]
        +
        lat_edges[1:]
    ) / 2

    lon_grid, lat_grid = np.meshgrid(
        lon_centres,
        lat_centres,
    )

    mean_lon = float(
        (density * lon_grid).sum()
        /
        total
    )

    mean_lat = float(
        (density * lat_grid).sum()
        /
        total
    )

    return mean_lon, mean_lat


def build_metrics(label, df):
    frequency = calculate_frequency(df)
    intensity = calculate_intensity(df)
    longevity = calculate_longevity(df)

    density, lon_edges, lat_edges = calculate_density(df)

    hot_lon, hot_lat, hot_count = hotspot_from_density(
        density,
        lon_edges,
        lat_edges,
    )

    centre_lon, centre_lat = density_weighted_centre(
        density,
        lon_edges,
        lat_edges,
    )

    return {
        "Combination": label,

        "Rows": int(
            len(df)
        ),

        "CycloneTracks": int(
            len(intensity)
        ),

        "SeasonMin": int(
            df["Season"].min()
        ),

        "SeasonMax": int(
            df["Season"].max()
        ),

        "MeanFrequency": float(
            frequency["Frequency"].mean()
        ),

        "MedianFrequency": float(
            frequency["Frequency"].median()
        ),

        "MaxFrequency": float(
            frequency["Frequency"].max()
        ),

        "FrequencyTrendPerSeason": linear_trend(
            frequency["Season"],
            frequency["Frequency"],
        ),

        "MeanMaxWind": float(
            intensity["MaxWind"].mean()
        ),

        "MedianMaxWind": float(
            intensity["MaxWind"].median()
        ),

        "P90MaxWind": float(
            intensity["MaxWind"].quantile(
                0.90
            )
        ),

        "StrongestTrackWind": float(
            intensity["MaxWind"].max()
        ),

        "MeanDurationDays": float(
            longevity["DurationDays"].mean()
        ),

        "MedianDurationDays": float(
            longevity["DurationDays"].median()
        ),

        "P90DurationDays": float(
            longevity["DurationDays"].quantile(
                0.90
            )
        ),

        "LongestDurationDays": float(
            longevity["DurationDays"].max()
        ),

        "HotspotLon": hot_lon,
        "HotspotLat": hot_lat,
        "HotspotCount": hot_count,

        "DensityCentreLon": centre_lon,
        "DensityCentreLat": centre_lat,
    }


# ============================================================
# GRAPH 1 — FREQUENCY
# ============================================================

def plot_frequency_individual(
    df,
    label,
    output_dir,
):
    freq = calculate_frequency(df)

    fig, ax = plt.subplots(
        figsize=(11.5, 6.2)
    )

    ax.plot(
        freq["Season"],
        freq["Frequency"],
        linewidth=1.2,
        marker="o",
        markersize=3.0,
        alpha=0.65,
        label="Seasonal frequency",
    )

    if len(freq) >= 5:

        rolling = (
            freq["Frequency"]
            .rolling(
                window=5,
                center=True,
                min_periods=1,
            )
            .mean()
        )

        ax.plot(
            freq["Season"],
            rolling,
            linewidth=2.8,
            alpha=0.95,
            label="5-season running mean",
        )

    apply_clean_axis_style(ax)

    ax.set_title(
        f"{label} - Tropical Cyclone Frequency",
        fontsize=15,
        pad=14,
    )

    ax.set_xlabel(
        "Season",
        labelpad=8,
    )

    ax.set_ylabel(
        "Unique cyclone tracks"
    )

    mean_freq = float(
        freq["Frequency"].mean()
    )

    slope = linear_trend(
        freq["Season"],
        freq["Frequency"],
    )

    ax.legend(
        loc="upper right",
        frameon=False,
        fontsize=9,
    )

    # Keep stats on the LEFT so they do not cross the legend.
    ax.text(
        0.02,
        0.97,
        f"Mean frequency: {mean_freq:.1f} cyclones/season\n"
        f"Linear trend: {slope:+.3f} tracks/season",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        bbox=dict(
            boxstyle="round,pad=0.45",
            facecolor="white",
            alpha=0.88,
            edgecolor="0.82",
        ),
    )

    fig.subplots_adjust(
        left=0.09,
        right=0.97,
        top=0.90,
        bottom=0.16,
    )

    add_footer(
        fig,
        "Frequency counts unique cyclone tracks per season.",
    )

    if SAVE_FIGURES:
        fig.savefig(
            output_dir
            /
            f"{safe_filename(label)}_frequency.png",
            dpi=300,
            bbox_inches="tight",
        )

    return fig


# ============================================================
# GRAPH 2 — INTENSITY
# ============================================================

def plot_intensity_individual(
    df,
    label,
    output_dir,
):
    intensity = calculate_intensity(df)

    values = (
        intensity["MaxWind"]
        .dropna()
    )

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(14.5, 5.8),
        constrained_layout=True,
    )

    mean_value = float(
        values.mean()
    )

    median_value = float(
        values.median()
    )

    p90_value = float(
        values.quantile(0.90)
    )

    axes[0].hist(
        values,
        bins=24,
        alpha=0.82,
        edgecolor="white",
        linewidth=0.7,
    )

    axes[0].axvline(
        mean_value,
        linestyle="--",
        linewidth=2,
        label=f"Mean {mean_value:.1f}",
    )

    axes[0].axvline(
        median_value,
        linestyle=":",
        linewidth=2,
        label=f"Median {median_value:.1f}",
    )

    axes[0].legend(
        frameon=False
    )

    apply_clean_axis_style(
        axes[0]
    )

    axes[0].set_title(
        "Maximum-wind distribution"
    )

    axes[0].set_xlabel(
        "Maximum Wspd per cyclone"
    )

    axes[0].set_ylabel(
        "Number of cyclone tracks"
    )

    # labels= supports the older Matplotlib in Spyder.
    axes[1].boxplot(
        [values.to_numpy()],
        labels=[label],
        showmeans=True,
        widths=0.45,
        patch_artist=True,
    )

    apply_clean_axis_style(
        axes[1]
    )

    axes[1].set_title(
        "Intensity spread"
    )

    axes[1].set_ylabel(
        "Maximum Wspd per cyclone"
    )

    axes[1].text(
        1.08,
        mean_value,
        f"Mean {mean_value:.1f}",
        va="center",
        fontsize=9,
    )

    axes[1].text(
        1.08,
        median_value,
        f"Median {median_value:.1f}",
        va="center",
        fontsize=9,
    )

    axes[1].text(
        1.08,
        p90_value,
        f"90th %ile {p90_value:.1f}",
        va="center",
        fontsize=9,
    )

    fig.suptitle(
        f"{label} - Tropical Cyclone Intensity",
        fontsize=15,
    )

    if SAVE_FIGURES:
        fig.savefig(
            output_dir
            /
            f"{safe_filename(label)}_intensity.png",
            dpi=300,
            bbox_inches="tight",
        )

    return fig


# ============================================================
# GRAPH 3 — LONGEVITY
# ============================================================

def plot_longevity_individual(
    df,
    label,
    output_dir,
):
    longevity = calculate_longevity(df)

    duration = (
        longevity["DurationDays"]
        .dropna()
    )

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(14.5, 5.8),
        constrained_layout=True,
    )

    mean_days = float(
        duration.mean()
    )

    median_days = float(
        duration.median()
    )

    p90_days = float(
        duration.quantile(0.90)
    )

    axes[0].hist(
        duration,
        bins=24,
        alpha=0.82,
        edgecolor="white",
        linewidth=0.7,
    )

    axes[0].axvline(
        mean_days,
        linestyle="--",
        linewidth=2,
        label=f"Mean {mean_days:.1f} d",
    )

    axes[0].axvline(
        median_days,
        linestyle=":",
        linewidth=2,
        label=f"Median {median_days:.1f} d",
    )

    axes[0].legend(
        frameon=False
    )

    apply_clean_axis_style(
        axes[0]
    )

    axes[0].set_title(
        "Track longevity distribution"
    )

    axes[0].set_xlabel(
        "Duration (days)"
    )

    axes[0].set_ylabel(
        "Number of cyclone tracks"
    )

    axes[1].boxplot(
        [duration.to_numpy()],
        labels=[label],
        showmeans=True,
        widths=0.45,
        patch_artist=True,
    )

    apply_clean_axis_style(
        axes[1]
    )

    axes[1].set_title(
        "Longevity spread"
    )

    axes[1].set_ylabel(
        "Duration (days)"
    )

    axes[1].text(
        1.08,
        mean_days,
        f"Mean {mean_days:.1f} d",
        va="center",
        fontsize=9,
    )

    axes[1].text(
        1.08,
        median_days,
        f"Median {median_days:.1f} d",
        va="center",
        fontsize=9,
    )

    axes[1].text(
        1.08,
        p90_days,
        f"90th %ile {p90_days:.1f} d",
        va="center",
        fontsize=9,
    )

    fig.suptitle(
        f"{label} - Tropical Cyclone Longevity",
        fontsize=15,
    )

    if SAVE_FIGURES:
        fig.savefig(
            output_dir
            /
            f"{safe_filename(label)}_longevity.png",
            dpi=300,
            bbox_inches="tight",
        )

    return fig


# ============================================================
# GRAPH 4 — HEAT MAP
# ============================================================

def plot_heatmap_individual(
    df,
    label,
    output_dir,
    base_dir,
):
    coastline_path = (
        base_dir
        /
        COASTLINE_IMAGE
    )

    if not coastline_path.exists():
        raise FileNotFoundError(
            f"Missing coastline background: {coastline_path}"
        )

    density, lon_edges, lat_edges = calculate_density(
        df
    )

    west, east, south, north = MAP_EXTENT

    background = plt.imread(
        coastline_path
    )

    masked_density = np.ma.masked_where(
        density <= 0,
        density,
    )

    fig, ax = plt.subplots(
        figsize=(10.2, 7.1)
    )

    ax.imshow(
        background,
        extent=[
            west,
            east,
            south,
            north,
        ],
        origin="upper",
        aspect="auto",
        zorder=0,
    )

    mesh = ax.pcolormesh(
        lon_edges,
        lat_edges,
        masked_density,
        shading="auto",
        cmap="YlOrRd",
        alpha=0.86,
        zorder=2,
    )

    ax.set_xlim(
        west,
        east,
    )

    ax.set_ylim(
        south,
        north,
    )

    x_ticks = [
        110,
        120,
        130,
        140,
        150,
        160,
        170,
    ]

    y_ticks = [
        -10,
        -20,
        -30,
        -40,
        -50,
    ]

    ax.set_xticks(
        x_ticks
    )

    ax.set_yticks(
        y_ticks
    )

    ax.set_xticklabels(
        [
            f"{x}°E"
            for x in x_ticks
        ]
    )

    ax.set_yticklabels(
        [
            f"{abs(y)}°S"
            for y in y_ticks
        ]
    )

    ax.set_title(
        f"{label} - Cyclone Track Density",
        fontsize=15,
        pad=12,
    )

    ax.set_xlabel(
        "Longitude"
    )

    ax.set_ylabel(
        "Latitude"
    )

    hot_lon, hot_lat, hot_count = hotspot_from_density(
        density,
        lon_edges,
        lat_edges,
    )

    if not np.isnan(
        hot_lon
    ):
        ax.scatter(
            [hot_lon],
            [hot_lat],
            s=70,
            marker="x",
            linewidths=2,
            zorder=5,
        )

        ax.annotate(
            f"Peak cell\n{hot_count:.0f} points",
            xy=(
                hot_lon,
                hot_lat,
            ),
            xytext=(
                12,
                12,
            ),
            textcoords="offset points",
            fontsize=8,
            bbox=dict(
                boxstyle="round,pad=0.35",
                facecolor="white",
                alpha=0.82,
                edgecolor="0.8",
            ),
        )

    colorbar = fig.colorbar(
        mesh,
        ax=ax,
        shrink=0.82,
        pad=0.025,
    )

    colorbar.set_label(
        "Track-point count"
    )

    add_footer(
        fig,
        "Yellow to red indicates increasing track-point density; zero-density cells are transparent.",
    )

    fig.tight_layout(
        rect=[
            0,
            0.04,
            1,
            1,
        ]
    )

    if SAVE_FIGURES:
        fig.savefig(
            output_dir
            /
            f"{safe_filename(label)}_heatmap.png",
            dpi=300,
            bbox_inches="tight",
        )

    return fig


# ============================================================
# COMPARISON FIGURE — FREQUENCY
# ============================================================

def plot_frequency_comparison(
    frames,
    output_dir,
):
    fig, ax = plt.subplots(
        figsize=(12, 6.2)
    )

    for label, df in frames.items():

        freq = calculate_frequency(
            df
        )

        if len(freq) >= 5:

            rolling = (
                freq["Frequency"]
                .rolling(
                    5,
                    center=True,
                    min_periods=1,
                )
                .mean()
            )

            ax.plot(
                freq["Season"],
                rolling,
                linewidth=2.4,
                label=label,
            )

        else:

            ax.plot(
                freq["Season"],
                freq["Frequency"],
                linewidth=2.0,
                label=label,
            )

    apply_clean_axis_style(
        ax
    )

    ax.set_title(
        "Frequency Comparison",
        fontsize=15,
        pad=12,
    )

    ax.set_xlabel(
        "Season"
    )

    ax.set_ylabel(
        "Unique cyclone tracks"
    )

    ax.legend(
        frameon=False,
        ncol=2,
    )

    fig.tight_layout()

    if SAVE_FIGURES:
        fig.savefig(
            output_dir
            /
            "comparison_frequency.png",
            dpi=300,
            bbox_inches="tight",
        )

    return fig


# ============================================================
# COMPARISON FIGURE — INTENSITY
# ============================================================

def plot_intensity_comparison(
    frames,
    output_dir,
):
    labels = []
    values = []

    for label, df in frames.items():

        intensity = calculate_intensity(
            df
        )

        labels.append(
            label
        )

        values.append(
            intensity["MaxWind"]
            .dropna()
            .to_numpy()
        )

    fig, ax = plt.subplots(
        figsize=(11, 6.4)
    )

    ax.boxplot(
        values,
        labels=labels,
        showmeans=True,
        patch_artist=True,
        widths=0.55,
    )

    apply_clean_axis_style(
        ax
    )

    ax.set_title(
        "Intensity Comparison",
        fontsize=15,
        pad=12,
    )

    ax.set_ylabel(
        "Maximum Wspd per cyclone"
    )

    ax.tick_params(
        axis="x",
        rotation=12,
    )

    fig.tight_layout()

    if SAVE_FIGURES:
        fig.savefig(
            output_dir
            /
            "comparison_intensity.png",
            dpi=300,
            bbox_inches="tight",
        )

    return fig


# ============================================================
# COMPARISON FIGURE — LONGEVITY
# ============================================================

def plot_longevity_comparison(
    frames,
    output_dir,
):
    labels = []
    values = []

    for label, df in frames.items():

        longevity = calculate_longevity(
            df
        )

        labels.append(
            label
        )

        values.append(
            longevity["DurationDays"]
            .dropna()
            .to_numpy()
        )

    fig, ax = plt.subplots(
        figsize=(11, 6.4)
    )

    ax.boxplot(
        values,
        labels=labels,
        showmeans=True,
        patch_artist=True,
        widths=0.55,
    )

    # Keep the comparison readable.
    # This changes only the displayed axis and does NOT delete any data.
    ax.set_ylim(
        0,
        100,
    )

    ax.set_yticks(
        np.arange(
            0,
            101,
            10,
        )
    )

    apply_clean_axis_style(
        ax
    )

    ax.set_title(
        "Longevity Comparison",
        fontsize=15,
        pad=12,
    )

    ax.set_ylabel(
        "Duration (days)"
    )

    ax.tick_params(
        axis="x",
        rotation=12,
    )

    ax.text(
        0.99,
        0.97,
        "Display limited to 100 days\nExtreme outliers may exceed axis range",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8,
        bbox=dict(
            boxstyle="round,pad=0.35",
            facecolor="white",
            alpha=0.88,
            edgecolor="0.82",
        ),
    )

    fig.tight_layout()

    if SAVE_FIGURES:
        fig.savefig(
            output_dir
            /
            "comparison_longevity.png",
            dpi=300,
            bbox_inches="tight",
        )

    return fig


# ============================================================
# COMPARISON FIGURE — HEAT MAPS
# ============================================================

def plot_heatmap_comparison(
    frames,
    output_dir,
    base_dir,
):
    coastline_path = (
        base_dir
        /
        COASTLINE_IMAGE
    )

    if not coastline_path.exists():
        raise FileNotFoundError(
            f"Missing coastline background: {coastline_path}"
        )

    background = plt.imread(
        coastline_path
    )

    densities = {}

    lon_edges = None
    lat_edges = None
    common_max = 0.0

    for label, df in frames.items():

        density, lon_edges, lat_edges = calculate_density(
            df
        )

        densities[label] = density

        common_max = max(
            common_max,
            float(
                density.max()
            ),
        )

    labels = list(
        frames.keys()
    )

    count = len(
        labels
    )

    ncols = 2

    nrows = math.ceil(
        count
        /
        ncols
    )

    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(
            13.5,
            5.7 * nrows,
        ),
        squeeze=False,
        constrained_layout=True,
    )

    west, east, south, north = MAP_EXTENT

    last_mesh = None

    for idx, label in enumerate(
        labels
    ):

        row, col = divmod(
            idx,
            ncols,
        )

        ax = axes[
            row,
            col,
        ]

        density = densities[
            label
        ]

        masked = np.ma.masked_where(
            density <= 0,
            density,
        )

        ax.imshow(
            background,
            extent=[
                west,
                east,
                south,
                north,
            ],
            origin="upper",
            aspect="auto",
            zorder=0,
        )

        last_mesh = ax.pcolormesh(
            lon_edges,
            lat_edges,
            masked,
            shading="auto",
            cmap="YlOrRd",
            alpha=0.86,
            vmin=0,
            vmax=(
                common_max
                if common_max > 0
                else None
            ),
            zorder=2,
        )

        ax.set_xlim(
            west,
            east,
        )

        ax.set_ylim(
            south,
            north,
        )

        ax.set_title(
            label
        )

        ax.set_xlabel(
            "Longitude"
        )

        ax.set_ylabel(
            "Latitude"
        )

        x_ticks = [
            110,
            130,
            150,
            170,
        ]

        y_ticks = [
            -10,
            -20,
            -30,
            -40,
            -50,
        ]

        ax.set_xticks(
            x_ticks
        )

        ax.set_yticks(
            y_ticks
        )

        ax.set_xticklabels(
            [
                f"{x}°E"
                for x in x_ticks
            ]
        )

        ax.set_yticklabels(
            [
                f"{abs(y)}°S"
                for y in y_ticks
            ]
        )

    for idx in range(
        count,
        nrows * ncols,
    ):

        row, col = divmod(
            idx,
            ncols,
        )

        axes[
            row,
            col,
        ].axis(
            "off"
        )

    if last_mesh is not None:

        colorbar = fig.colorbar(
            last_mesh,
            ax=axes.ravel().tolist(),
            shrink=0.82,
            pad=0.02,
        )

        colorbar.set_label(
            "Track-point count"
        )

    fig.suptitle(
        "Track-Density Comparison - Common Grid and Colour Scale",
        fontsize=15,
    )

    if SAVE_FIGURES:
        fig.savefig(
            output_dir
            /
            "comparison_heatmaps.png",
            dpi=300,
            bbox_inches="tight",
        )

    return fig


# ============================================================
# TXT INTERPRETATION HELPERS
# ============================================================

def trend_word(slope):

    if pd.isna(
        slope
    ):
        return "could not be determined"

    if slope > 0.05:
        return "shows an increasing trend"

    if slope < -0.05:
        return "shows a decreasing trend"

    return "is broadly stable"


def format_percent(value):

    if pd.isna(
        value
    ):
        return "not available"

    sign = (
        "+"
        if value > 0
        else ""
    )

    return (
        f"{sign}{value:.1f}%"
    )


def comparison_word(value):

    if pd.isna(
        value
    ):
        return "not comparable"

    if value > 5:
        return "higher"

    if value < -5:
        return "lower"

    return "similar"


# ============================================================
# TXT REPORT GENERATOR
# ============================================================

def generate_txt_report(
    summary
):
    lines = []

    lines.append(
        "TC-EXPLORER 2.0 ANALYSIS REPORT"
    )

    lines.append(
        "=" * 72
    )

    lines.append("")

    lines.append(
        "This report is generated automatically from the selected tropical "
        "cyclone datasets using built-in Python calculations. The results are "
        "descriptive and should not be treated as proof of causation."
    )

    lines.append("")
    lines.append("")

    # --------------------------------------------------------
    # EACH COMBINATION
    # --------------------------------------------------------

    for _, row in summary.iterrows():

        label = row[
            "Combination"
        ]

        lines.append(
            label.upper()
        )

        lines.append(
            "-" * 72
        )

        lines.append("")
        lines.append(
            "Frequency"
        )

        lines.append(
            f"{label} contains {int(row['CycloneTracks'])} unique cyclone "
            f"tracks over seasons {int(row['SeasonMin'])} to "
            f"{int(row['SeasonMax'])}. The average cyclone frequency is "
            f"{row['MeanFrequency']:.2f} tracks per season and the median "
            f"frequency is {row['MedianFrequency']:.2f}. The maximum observed "
            f"seasonal frequency is {row['MaxFrequency']:.0f} tracks."
        )

        lines.append(
            f"The fitted linear frequency trend is "
            f"{row['FrequencyTrendPerSeason']:+.3f} tracks per season. "
            f"This {trend_word(row['FrequencyTrendPerSeason'])} across the "
            f"analysed period."
        )

        lines.append("")
        lines.append(
            "Intensity"
        )

        lines.append(
            f"The average maximum wind reached by each cyclone track is "
            f"{row['MeanMaxWind']:.2f}. The median track-maximum wind is "
            f"{row['MedianMaxWind']:.2f}, while the 90th percentile is "
            f"{row['P90MaxWind']:.2f}. The strongest cyclone track in this "
            f"selection reaches a maximum Wspd of "
            f"{row['StrongestTrackWind']:.2f}."
        )

        lines.append("")
        lines.append(
            "Longevity"
        )

        lines.append(
            f"The average cyclone lifetime is "
            f"{row['MeanDurationDays']:.2f} days and the median lifetime is "
            f"{row['MedianDurationDays']:.2f} days. The 90th percentile "
            f"duration is {row['P90DurationDays']:.2f} days, while the "
            f"longest track lasts {row['LongestDurationDays']:.2f} days."
        )

        lines.append("")
        lines.append(
            "Spatial density"
        )

        lines.append(
            f"The highest track-point density occurs near "
            f"{row['HotspotLon']:.1f} degrees East and "
            f"{abs(row['HotspotLat']):.1f} degrees South, with approximately "
            f"{row['HotspotCount']:.0f} track points in the highest-density "
            f"grid cell."
        )

        lines.append(
            f"The density-weighted centre of cyclone activity is located near "
            f"{row['DensityCentreLon']:.1f} degrees East and "
            f"{abs(row['DensityCentreLat']):.1f} degrees South."
        )

        lines.append("")
        lines.append("")

    # --------------------------------------------------------
    # OVERALL RANKINGS
    # --------------------------------------------------------

    lines.append(
        "OVERALL COMPARISON"
    )

    lines.append(
        "=" * 72
    )

    lines.append("")

    highest_frequency = summary.loc[
        summary["MeanFrequency"].idxmax()
    ]

    lowest_frequency = summary.loc[
        summary["MeanFrequency"].idxmin()
    ]

    highest_intensity = summary.loc[
        summary["MeanMaxWind"].idxmax()
    ]

    lowest_intensity = summary.loc[
        summary["MeanMaxWind"].idxmin()
    ]

    longest = summary.loc[
        summary["MeanDurationDays"].idxmax()
    ]

    shortest = summary.loc[
        summary["MeanDurationDays"].idxmin()
    ]

    lines.append(
        "Frequency comparison"
    )

    lines.append(
        f"{highest_frequency['Combination']} has the highest average cyclone "
        f"frequency at {highest_frequency['MeanFrequency']:.2f} tracks per "
        f"season. {lowest_frequency['Combination']} has the lowest average "
        f"frequency at {lowest_frequency['MeanFrequency']:.2f} tracks per "
        f"season."
    )

    lines.append("")
    lines.append(
        "Intensity comparison"
    )

    lines.append(
        f"{highest_intensity['Combination']} has the highest average cyclone "
        f"track-maximum wind at {highest_intensity['MeanMaxWind']:.2f}. "
        f"{lowest_intensity['Combination']} has the lowest average "
        f"track-maximum wind at {lowest_intensity['MeanMaxWind']:.2f}."
    )

    lines.append("")
    lines.append(
        "Longevity comparison"
    )

    lines.append(
        f"{longest['Combination']} has the longest average cyclone lifetime "
        f"at {longest['MeanDurationDays']:.2f} days. "
        f"{shortest['Combination']} has the shortest average lifetime at "
        f"{shortest['MeanDurationDays']:.2f} days."
    )

    lines.append("")
    lines.append("")

    # --------------------------------------------------------
    # TRACKER COMPARISON
    # --------------------------------------------------------

    lines.append(
        "TRACKER COMPARISON: CDD VS TE"
    )

    lines.append(
        "=" * 72
    )

    lines.append("")

    lookup = summary.set_index(
        "Combination"
    )

    for regional_model in [
        "BARPA",
        "CCAM",
    ]:

        cdd_label = (
            f"{regional_model} + CDD"
        )

        te_label = (
            f"{regional_model} + TE"
        )

        if (
            cdd_label not in lookup.index
            or
            te_label not in lookup.index
        ):
            continue

        cdd = lookup.loc[
            cdd_label
        ]

        te = lookup.loc[
            te_label
        ]

        freq_change = percent_difference(
            te["MeanFrequency"],
            cdd["MeanFrequency"],
        )

        intensity_change = percent_difference(
            te["MeanMaxWind"],
            cdd["MeanMaxWind"],
        )

        longevity_change = percent_difference(
            te["MeanDurationDays"],
            cdd["MeanDurationDays"],
        )

        lines.append(
            regional_model
        )

        lines.append(
            f"When TE is used instead of CDD, average cyclone frequency changes "
            f"by {format_percent(freq_change)}. The TE frequency estimate is "
            f"{comparison_word(freq_change)} than the CDD estimate."
        )

        lines.append(
            f"Average cyclone track-maximum wind changes by "
            f"{format_percent(intensity_change)}. The TE intensity estimate is "
            f"{comparison_word(intensity_change)} than the CDD estimate."
        )

        lines.append(
            f"Average cyclone longevity changes by "
            f"{format_percent(longevity_change)}. The TE longevity estimate is "
            f"{comparison_word(longevity_change)} than the CDD estimate."
        )

        lines.append("")

    # --------------------------------------------------------
    # REGIONAL MODEL COMPARISON
    # --------------------------------------------------------

    lines.append(
        "REGIONAL MODEL COMPARISON: BARPA VS CCAM"
    )

    lines.append(
        "=" * 72
    )

    lines.append("")

    for tracker in [
        "CDD",
        "TE",
    ]:

        barpa_label = (
            f"BARPA + {tracker}"
        )

        ccam_label = (
            f"CCAM + {tracker}"
        )

        if (
            barpa_label not in lookup.index
            or
            ccam_label not in lookup.index
        ):
            continue

        barpa = lookup.loc[
            barpa_label
        ]

        ccam = lookup.loc[
            ccam_label
        ]

        freq_change = percent_difference(
            ccam["MeanFrequency"],
            barpa["MeanFrequency"],
        )

        intensity_change = percent_difference(
            ccam["MeanMaxWind"],
            barpa["MeanMaxWind"],
        )

        longevity_change = percent_difference(
            ccam["MeanDurationDays"],
            barpa["MeanDurationDays"],
        )

        lines.append(
            tracker
        )

        lines.append(
            f"Using {tracker}, CCAM's average cyclone frequency differs from "
            f"BARPA by {format_percent(freq_change)}."
        )

        lines.append(
            f"Using {tracker}, CCAM's average track-maximum wind differs from "
            f"BARPA by {format_percent(intensity_change)}."
        )

        lines.append(
            f"Using {tracker}, CCAM's average cyclone longevity differs from "
            f"BARPA by {format_percent(longevity_change)}."
        )

        lines.append("")

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    lines.append(
        "FINAL DESCRIPTIVE SUMMARY"
    )

    lines.append(
        "=" * 72
    )

    lines.append("")

    lines.append(
        f"The selected data show that {highest_frequency['Combination']} "
        f"produces the highest average tropical cyclone frequency, "
        f"{highest_intensity['Combination']} produces the highest average "
        f"track-maximum wind, and {longest['Combination']} produces the "
        f"longest average cyclone lifetime."
    )

    if (
        highest_frequency["Combination"]
        ==
        highest_intensity["Combination"]
        ==
        longest["Combination"]
    ):

        lines.append(
            f"The same combination, {highest_frequency['Combination']}, leads "
            f"all three main descriptive measures. This pattern should be "
            f"checked carefully against regional model, tracking algorithm, "
            f"driving-model composition and available period."
        )

    else:

        lines.append(
            "No single dataset/tracker combination dominates all three main "
            "characteristics. Frequency, intensity and longevity therefore "
            "show different patterns across the selected combinations."
        )

    lines.append("")

    lines.append(
        "The heat-map results should be interpreted spatially. A high-density "
        "grid cell means that many cyclone track observations pass through "
        "that location; it does not directly mean that cyclones are stronger "
        "there."
    )

    lines.append("")
    lines.append(
        "IMPORTANT NOTE"
    )

    lines.append(
        "-" * 72
    )

    lines.append(
        "These results describe patterns present in the selected data. They "
        "should not be interpreted as proof that BARPA, CCAM, CDD or TE causes "
        "a particular cyclone behaviour. Formal scientific conclusions may "
        "require significance testing, controlled period comparisons and "
        "additional climate-model analysis."
    )

    return "\n".join(
        lines
    )


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # REPOSITORY PATHS
    # --------------------------------------------------------
    #
    # Expected repository layout:
    #
    # ITPROJECT2/
    # ├── app/
    # ├── data/
    # │   ├── barpa_cdd_all_ssp370.csv
    # │   ├── barpa_te_all_ssp370.csv
    # │   ├── ccam_cdd_all_ssp370.csv
    # │   └── ccam_te_all_ssp370.csv
    # └── analysis_tester/             (folder name can be different)
    #     ├── tc_explorer_repo_analysis.py
    #     └── au_coastline_background.png
    #
    # The analysis folder may have any name. The code only assumes that
    # it sits directly inside the repository root, beside /data.
    #
    analysis_dir = (
        Path(__file__)
        .resolve()
        .parent
    )

    project_root = (
        analysis_dir
        .parent
    )

    data_dir = (
        project_root
        /
        "data"
    )

    coastline_path = (
        analysis_dir
        /
        COASTLINE_IMAGE
    )

    output_root = (
        analysis_dir
        /
        "tc_analysis_output"
    )

    if not data_dir.exists():
        raise FileNotFoundError(
            f"Repository data folder not found: {data_dir}\n"
            "Place this analysis folder directly inside ITPROJECT2, beside /data."
        )

    if not coastline_path.exists():
        raise FileNotFoundError(
            f"Australia coastline background not found: {coastline_path}\n"
            "Place au_coastline_background.png beside this Python file."
        )

    individual_dir = (
        output_root
        /
        "individual"
    )

    comparison_dir = (
        output_root
        /
        "comparison"
    )

    individual_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    comparison_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    combinations = [
        (
            dataset,
            tracker,
        )
        for dataset
        in SELECTED_DATASETS
        for tracker
        in SELECTED_TRACKERS
    ]

    frames = {}
    metric_rows = []

    print(
        "TC-Explorer 2.0 repository analysis runner"
    )

    print(
        f"Repository root: {project_root}"
    )

    print(
        f"Data folder: {data_dir}"
    )

    print(
        f"Analysis folder: {analysis_dir}"
    )

    print(
        f"Output folder: {output_root}"
    )

    for dataset, tracker in combinations:

        label = (
            f"{dataset} + {tracker}"
        )

        filename = FILES[
            (
                dataset,
                tracker,
            )
        ]

        path = (
            data_dir
            /
            filename
        )

        if not path.exists():

            print(
                f"SKIPPING {label}: "
                f"{filename} not found."
            )

            continue

        print(
            f"Loading {label} ..."
        )

        df = load_csv(
            path
        )

        df = apply_filters(
            df
        )

        if df.empty:

            print(
                f"SKIPPING {label}: no rows after filtering."
            )

            continue

        frames[
            label
        ] = df

        metric_rows.append(
            build_metrics(
                label,
                df,
            )
        )

        # Individual figures
        plot_frequency_individual(
            df,
            label,
            individual_dir,
        )

        plot_intensity_individual(
            df,
            label,
            individual_dir,
        )

        plot_longevity_individual(
            df,
            label,
            individual_dir,
        )

        plot_heatmap_individual(
            df,
            label,
            individual_dir,
            analysis_dir,
        )

    if not frames:
        raise FileNotFoundError(
            "No selected TC datasets were found beside this script."
        )

    # --------------------------------------------------------
    # SUMMARY TABLE
    # --------------------------------------------------------

    summary = pd.DataFrame(
        metric_rows
    )

    summary_path = (
        output_root
        /
        "comparison_summary.csv"
    )

    summary.to_csv(
        summary_path,
        index=False,
    )

    # --------------------------------------------------------
    # COMPARISON FIGURES
    # --------------------------------------------------------

    if len(
        frames
    ) >= 2:

        plot_frequency_comparison(
            frames,
            comparison_dir,
        )

        plot_intensity_comparison(
            frames,
            comparison_dir,
        )

        plot_longevity_comparison(
            frames,
            comparison_dir,
        )

        plot_heatmap_comparison(
            frames,
            comparison_dir,
            analysis_dir,
        )

    # --------------------------------------------------------
    # TXT REPORT
    # --------------------------------------------------------

    report = generate_txt_report(
        summary
    )

    report_path = (
        output_root
        /
        "tc_interpretation_report.txt"
    )

    with open(
        report_path,
        "w",
        encoding="utf-8",
    ) as file:

        file.write(
            report
        )

    # Also print the report in Spyder.
    print()
    print(
        report
    )

    print()
    print(
        "=" * 80
    )

    print(
        "ANALYSIS COMPLETE"
    )

    print(
        f"Individual graphs: {individual_dir}"
    )

    print(
        f"Comparison graphs: {comparison_dir}"
    )

    print(
        f"Comparison CSV: {summary_path}"
    )

    print(
        f"TXT interpretation: {report_path}"
    )

    print(
        "=" * 80
    )

    if SHOW_FIGURES:
        plt.show()
    else:
        plt.close(
            "all"
        )


if __name__ == "__main__":
    main()
