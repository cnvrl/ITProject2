from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def build_density_grid(
    points_df: pd.DataFrame,
    lon_bins: int = 51,
    lat_bins: int = 21,
    lon_range: tuple[float, float] = (100.0, 180.0),
    lat_range: tuple[float, float] = (-60.0, 0.0),
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute 2D spatial histogram observation density."""
    if points_df.empty:
        grid = np.zeros((lat_bins, lon_bins))
        lon_edges = np.linspace(lon_range[0], lon_range[1], lon_bins + 1)
        lat_edges = np.linspace(lat_range[0], lat_range[1], lat_bins + 1)
        return grid, lon_edges, lat_edges

    grid, lat_edges, lon_edges = np.histogram2d(
        points_df["lat"],
        points_df["lon"],
        bins=[lat_bins, lon_bins],
        range=[lat_range, lon_range],
    )

    return grid, lon_edges, lat_edges


def track_density_grid(
    points_df: pd.DataFrame,
    n_seasons: int,
    cell_degrees: float = 2.0,
    lon_range: tuple[float, float] = (100.0, 176.0),
    lat_range: tuple[float, float] = (-46.0, 4.0),
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Mean number of distinct tracks entering each grid cell per season.

    A track counts once per cell it passes through, however many of its
    observations fall inside that cell. Cells over land are included, so
    landfalling and coast-crossing cyclones show up inland.
    Returns (grid[lat, lon], lon_centers, lat_centers).
    """
    nx = int(round((lon_range[1] - lon_range[0]) / cell_degrees))
    ny = int(round((lat_range[1] - lat_range[0]) / cell_degrees))
    lon_centers = lon_range[0] + cell_degrees * (np.arange(nx) + 0.5)
    lat_centers = lat_range[0] + cell_degrees * (np.arange(ny) + 0.5)
    grid = np.zeros((ny, nx))

    if points_df.empty or n_seasons <= 0:
        return grid, lon_centers, lat_centers

    lon = pd.to_numeric(points_df["lon"], errors="coerce").to_numpy(dtype=float)
    lat = pd.to_numeric(points_df["lat"], errors="coerce").to_numpy(dtype=float)
    ix = np.floor((lon - lon_range[0]) / cell_degrees)
    iy = np.floor((lat - lat_range[0]) / cell_degrees)
    inside = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)

    if not inside.any():
        return grid, lon_centers, lat_centers

    cells = pd.DataFrame(
        {
            "track_id": points_df["track_id"].to_numpy()[inside],
            "cell": (iy[inside] * nx + ix[inside]).astype(int),
        }
    ).drop_duplicates()

    counts = np.bincount(cells["cell"].to_numpy(), minlength=nx * ny)
    grid = counts.reshape(ny, nx) / float(n_seasons)

    return grid, lon_centers, lat_centers


def density_colour_max(
    grids: list[np.ndarray],
    quantile: float = 0.98,
) -> float | None:
    """Shared colour-scale maximum, so every model's density map uses the same scale."""
    positive = [grid[grid > 0] for grid in grids if grid.size]
    positive = [values for values in positive if values.size]

    if not positive:
        return None

    return float(np.quantile(np.concatenate(positive), quantile))


def compute_density_welch_p_grid(
    hist_points: pd.DataFrame,
    fut_points: pd.DataFrame,
    lon_bins: int = 51,
    lat_bins: int = 21,
    lon_range: tuple[float, float] = (100.0, 180.0),
    lat_range: tuple[float, float] = (-60.0, 0.0),
) -> dict[str, np.ndarray]:
    """
    Cell-by-cell Welch's t-test (equal_var=False) comparing seasonal density 
    between historical and future projections using fast groupby lookups.
    """
    hist_seasons = hist_points["season"].dropna().unique() if not hist_points.empty else []
    fut_seasons = fut_points["season"].dropna().unique() if not fut_points.empty else []

    # Fast DataFrame grouping to prevent linear re-scanning
    hist_grouped = dict(list(hist_points.groupby("season"))) if not hist_points.empty else {}
    fut_grouped = dict(list(fut_points.groupby("season"))) if not fut_points.empty else {}

    hist_season_grids = [
        build_density_grid(hist_grouped[s], lon_bins, lat_bins, lon_range, lat_range)[0]
        for s in hist_seasons if s in hist_grouped
    ]

    fut_season_grids = [
        build_density_grid(fut_grouped[s], lon_bins, lat_bins, lon_range, lat_range)[0]
        for s in fut_seasons if s in fut_grouped
    ]

    lon_edges = np.linspace(lon_range[0], lon_range[1], lon_bins + 1)
    lat_edges = np.linspace(lat_range[0], lat_range[1], lat_bins + 1)
    lon_centers = 0.5 * (lon_edges[:-1] + lon_edges[1:])
    lat_centers = 0.5 * (lat_edges[:-1] + lat_edges[1:])

    if not hist_season_grids or not fut_season_grids:
        empty_grid = np.zeros((lat_bins, lon_bins))
        empty_p = np.full((lat_bins, lon_bins), np.nan)
        return {
            "p_values": empty_p,
            "t_stats": empty_grid,
            "mean_diff": empty_grid,
            "lon_centers": lon_centers,
            "lat_centers": lat_centers,
        }

    hist_stack = np.stack(hist_season_grids, axis=0)
    fut_stack = np.stack(fut_season_grids, axis=0)

    t_stats, p_values = stats.ttest_ind(
        fut_stack,
        hist_stack,
        axis=0,
        equal_var=False,
        nan_policy="omit",
    )

    mean_diff = np.mean(fut_stack, axis=0) - np.mean(hist_stack, axis=0)

    return {
        "p_values": p_values,
        "t_stats": t_stats,
        "mean_diff": mean_diff,
        "lon_centers": lon_centers,
        "lat_centers": lat_centers,
    }