from __future__ import annotations

from dash import Dash, Input, Output

from app.figures import (
    empty_figure,
    selected_track_figure,
)
from app.services.dashboard_data_service import (
    DashboardData,
)


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
                "No cyclone selected",
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
                "Data unavailable",
            )

        record = records.iloc[0]

        summary = (
            f"Cyclone {record['raw_track_id']} "
            f"({record['season']}) · "
            f"{record['dataset']} / "
            f"{record['tracker']} / "
            f"{record['driving_model']} · "
            f"Category "
            f"{int(record['max_category'])} · "
            f"{record['max_wind_speed']:.0f} km/h"
        )

        return (
            selected_track_figure(
                record,
                points,
            ),
            summary,
        )