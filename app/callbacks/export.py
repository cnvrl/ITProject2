from __future__ import annotations

from dash import (
    Dash,
    Input,
    Output,
    State,
    dcc,
    no_update,
)

from app.services.dashboard_data_service import (
    DashboardData,
)
from app.services.export_service import (
    filtered_export_frame,
    interpretation_report,
    summary_export_frame,
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

        frame = summary_export_frame(tracks)

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