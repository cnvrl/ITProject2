from __future__ import annotations

import pandas as pd
from dash import Dash, Input, Output, html

from app.figures import (
    empty_figure,
    selected_track_figure,
)
from app.services.dashboard_data_service import (
    DashboardData,
)
from app.ui.components import summary_chip


def _coordinate(lat: float, lon: float) -> str:
    if pd.isna(lat) or pd.isna(lon):
        return "Unknown"
    hemisphere = "S" if lat < 0 else "N"
    return f"{abs(lat):.0f}°{hemisphere} {lon:.0f}°E"


def register_map_callbacks(
    app: Dash,
    data: DashboardData,
) -> None:
    @app.callback(
        Output("cyclone-map", "figure"),
        Output(
            "selected-cyclone-summary",
            "children",
        ),
        Input("selected-cyclone", "value"),
    )
    def update_selected_map(track_id):
        if not track_id:
            return (
                empty_figure(
                    (
                        "Select a cyclone to display "
                        "its track."
                    ),
                    height=430,
                ),
                html.P("No cyclone selected.", className="empty-state"),
            )

        records = data.tracks[
            data.tracks["track_id"].eq(
                track_id
            )
        ]

        points = data.points[
            data.points["track_id"].eq(
                track_id
            )
        ]

        if records.empty or points.empty:
            return (
                empty_figure(
                    "Cyclone data unavailable.",
                    height=430,
                ),
                html.P("Track data is unavailable for this cyclone.", className="empty-state"),
            )

        record = records.iloc[0]
        min_pressure = pd.to_numeric(points["pressure"], errors="coerce").min()

        summary = [
            summary_chip("Intensity", f"Category {int(record['max_category'])}"),
            summary_chip("Peak wind", f"{record['max_wind_speed']:.0f} km/h"),
            summary_chip(
                "Min pressure",
                f"{min_pressure:.0f} hPa" if pd.notna(min_pressure) else "Not recorded",
            ),
            summary_chip("Lifetime", f"{record['lifetime_hours'] / 24:.1f} days"),
            summary_chip("Genesis", _coordinate(record["genesis_lat"], record["genesis_lon"])),
            summary_chip("Landfall", "Yes" if record["landfall"] else "No"),
        ]

        return (
            selected_track_figure(
                record,
                points,
            ),
            summary,
        )
