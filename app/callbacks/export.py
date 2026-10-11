"""
This file manages the export callbacks for TC Explorer 2.0.

The main function register_export_callbacks() connects the export buttons
to the Dash application. It allows users to download the filtered cyclone
records, model comparison summary and interpretation report.

The selected_tracks() function gets the cyclone records based on the
selected track IDs. If no tracks are selected, it returns an empty dataset.

The file includes three main callback functions:
- download_tracks() exports the filtered cyclone records as a CSV file.
- download_summary() uses comparison_summary() to generate and download
  the model comparison results as a CSV file.
- download_report() uses interpretation_report() to generate a text report
  based on the selected cyclone data.

The code uses the Dash and DashboardData classes to manage the application
and access cyclone data. It also uses Input, Output and State to handle
button clicks and get the selected records. The dcc component is used
to send the generated files to users.

If there are no matching cyclone records, no_update is returned to prevent
downloading an empty file.

Overall, this file allows users to export their analysis results into
different file formats for further use.
"""
from __future__ import annotations

from dash import (
    Dash,
    Input,
    Output,
    State,
    dcc,
    no_update,
)

from app.services.analysis_service import comparison_summary
from app.services.dashboard_data_service import DashboardData
from app.services.export_service import (
    filtered_export_frame,
    interpretation_report,
)


def register_export_callbacks(
    app: Dash,
    data: DashboardData,
) -> None:
    def selected_tracks(ids):
        if not ids:
            return data.tracks.iloc[0:0].copy()

        return data.tracks[
            data.tracks["track_id"].isin(ids)
        ].copy()

    @app.callback(
        Output("download-csv", "data"),
        Input("export-button", "n_clicks"),
        State("filtered-track-ids", "data"),
        prevent_initial_call=True,
    )
    def download_tracks(_clicks, ids):
        tracks = selected_tracks(ids)

        if tracks.empty:
            return no_update

        frame = filtered_export_frame(tracks)

        return dcc.send_data_frame(
            frame.to_csv,
            "tc_explorer_filtered_records.csv",
            index=False,
        )

    @app.callback(
        Output("download-summary", "data"),
        Input("summary-button", "n_clicks"),
        State("filtered-track-ids", "data"),
        prevent_initial_call=True,
    )
    def download_summary(_clicks, ids):
        tracks = selected_tracks(ids)

        if tracks.empty:
            return no_update

        frame = comparison_summary(tracks)

        return dcc.send_data_frame(
            frame.to_csv,
            "comparison_summary.csv",
            index=False,
        )

    @app.callback(
        Output("download-report", "data"),
        Input("report-button", "n_clicks"),
        State("filtered-track-ids", "data"),
        prevent_initial_call=True,
    )
    def download_report(_clicks, ids):
        tracks = selected_tracks(ids)

        if tracks.empty:
            return no_update

        return {
            "content": interpretation_report(tracks),
            "filename": "tc_interpretation_report.txt",
            "type": "text/plain",
        }