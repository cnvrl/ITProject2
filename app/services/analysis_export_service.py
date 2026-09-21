"""
analysis_export_service.py
The 

"""
from __future__ import annotations

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from app.services.analysis_service import (
    LONGEVITY_DISPLAY_LIMIT_DAYS,
    build_summary,
    calculate_frequency,
    density_grid,
)
from app.services.report_service import build_report


def _safe(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def _png(fig) -> bytes:
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    return buffer.getvalue()


def _individual_pngs(label: str, tracks: pd.DataFrame, points: pd.DataFrame) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    stem = _safe(label)
    frequency = calculate_frequency(tracks)
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.plot(frequency["season"], frequency["frequency"], marker="o", markersize=3, alpha=.55)
    ax.plot(frequency["season"], frequency["frequency"].rolling(5, center=True, min_periods=1).mean(), linewidth=2.5)
    ax.set(title=f"{label} - Tropical Cyclone Frequency", xlabel="Season", ylabel="Unique cyclone tracks")
    ax.grid(alpha=.2); fig.tight_layout()
    files[f"individual/{stem}_frequency.png"] = _png(fig)

    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.hist(tracks["max_wind_speed"].dropna(), bins=24, edgecolor="white")
    ax.set(title=f"{label} - Tropical Cyclone Intensity", xlabel="Maximum wind per cyclone (km/h)", ylabel="Tracks")
    ax.grid(alpha=.2); fig.tight_layout()
    files[f"individual/{stem}_intensity.png"] = _png(fig)

    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.hist((tracks["lifetime_hours"] / 24).dropna(), bins=24, edgecolor="white")
    ax.set(title=f"{label} - Tropical Cyclone Longevity", xlabel="Duration (days)", ylabel="Tracks")
    ax.grid(alpha=.2); fig.tight_layout()
    files[f"individual/{stem}_longevity.png"] = _png(fig)

    density, lon_edges, lat_edges = density_grid(points)
    fig, ax = plt.subplots(figsize=(10, 6.5))
    mesh = ax.pcolormesh(lon_edges, lat_edges, np.ma.masked_where(density <= 0, density), cmap="YlOrRd", shading="auto")
    fig.colorbar(mesh, ax=ax, label="Track-point count")
    ax.set(title=f"{label} - Cyclone Track Density", xlabel="Longitude", ylabel="Latitude", xlim=(100, 180), ylim=(-60, 0))
    fig.tight_layout()
    files[f"individual/{stem}_heatmap.png"] = _png(fig)
    return files


def build_analysis_zip(tracks: pd.DataFrame, points: pd.DataFrame) -> bytes:
    summary = build_summary(tracks, points)
    labels = list(summary["Combination"])
    archive = BytesIO()
    with ZipFile(archive, "w", ZIP_DEFLATED) as zf:
        zf.writestr("comparison_summary.csv", summary.to_csv(index=False))
        zf.writestr("tc_interpretation_report.txt", build_report(summary))
        for label in labels:
            label_tracks = tracks[tracks["analysis_label"] == label]
            label_points = points[points["analysis_label"] == label]
            for name, content in _individual_pngs(label, label_tracks, label_points).items():
                zf.writestr(name, content)

        fig, ax = plt.subplots(figsize=(11, 6))
        for label in labels:
            freq = calculate_frequency(tracks[tracks["analysis_label"] == label])
            ax.plot(freq["season"], freq["frequency"].rolling(5, center=True, min_periods=1).mean(), linewidth=2, label=label)
        ax.set(title="Frequency Comparison", xlabel="Season", ylabel="Unique cyclone tracks"); ax.grid(alpha=.2); ax.legend(fontsize=8); fig.tight_layout()
        zf.writestr("comparison_frequency.png", _png(fig))

        fig, ax = plt.subplots(figsize=(11, 6))
        ax.boxplot([tracks.loc[tracks["analysis_label"] == label, "max_wind_speed"].dropna() for label in labels], labels=labels, showmeans=True)
        ax.set(title="Intensity Comparison", ylabel="Maximum wind per cyclone (km/h)"); ax.tick_params(axis="x", rotation=15); ax.grid(alpha=.2); fig.tight_layout()
        zf.writestr("comparison_intensity.png", _png(fig))

        fig, ax = plt.subplots(figsize=(11, 6))
        ax.boxplot([(tracks.loc[tracks["analysis_label"] == label, "lifetime_hours"] / 24).dropna() for label in labels], labels=labels, showmeans=True)
        ax.set(title="Longevity Comparison", ylabel="Duration (days)", ylim=(0, LONGEVITY_DISPLAY_LIMIT_DAYS)); ax.tick_params(axis="x", rotation=15); ax.grid(alpha=.2); fig.tight_layout()
        zf.writestr("comparison_longevity.png", _png(fig))

        cols = 2 if len(labels) > 1 else 1
        rows = int(np.ceil(len(labels) / cols))
        fig, axes = plt.subplots(rows, cols, figsize=(13, 5.2 * rows), squeeze=False)
        grids = [density_grid(points[points["analysis_label"] == label]) for label in labels]
        vmax = max((grid[0].max() for grid in grids), default=0)
        mesh = None
        for index, (label, (density, lon_edges, lat_edges)) in enumerate(zip(labels, grids)):
            row, col = divmod(index, cols); ax = axes[row][col]
            mesh = ax.pcolormesh(lon_edges, lat_edges, np.ma.masked_where(density <= 0, density), cmap="YlOrRd", shading="auto", vmin=0, vmax=vmax or None)
            ax.set(title=label, xlabel="Longitude", ylabel="Latitude", xlim=(100, 180), ylim=(-60, 0))
        for index in range(len(labels), rows * cols):
            row, col = divmod(index, cols); axes[row][col].axis("off")
        if mesh is not None:
            fig.colorbar(mesh, ax=axes.ravel().tolist(), label="Track-point count", shrink=.8)
        fig.suptitle("Track-Density Comparison - Common Grid and Colour Scale"); fig.subplots_adjust(top=.92, wspace=.25, hspace=.28)
        zf.writestr("comparison_heatmaps.png", _png(fig))
    return archive.getvalue()
