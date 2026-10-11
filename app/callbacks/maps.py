"""
This file manages the map callbacks for TC Explorer 2.0.

The main function register_map_callbacks() connects the cyclone map
and summary section to the Dash application. It updates the map and
cyclone information when users select a cyclone from the dropdown menu.

The file includes two main functions:
- _coordinate() converts the latitude and longitude into a readable
  location format. It returns "Unknown" if the coordinates are missing.
- update_selected_map() gets the selected cyclone's track and observation
  data, then updates the map and displays its summary information.

The summary includes cyclone intensity, peak wind speed, minimum pressure,
lifetime, genesis location and whether the cyclone made landfall.

The code uses Dash and DashboardData classes to manage the application
and access cyclone records. It also uses Input and Output to update the
map when users select a different cyclone. Pandas is used to check missing
values and calculate the minimum recorded pressure.

Supporting functions include selected_track_figure() to display the
cyclone track, empty_figure() to show an empty map when data is unavailable,
and summary_chip() to display the cyclone information in separate sections.

If no cyclone is selected or the track data is missing, the function
displays an empty map with a message to inform the user.

Overall, this file allows users to view individual cyclone tracks
and their main information through an interactive map.
"""
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
