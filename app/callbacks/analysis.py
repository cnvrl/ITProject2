from __future__ import annotations

from dash import (
    Dash,
    Input,
    Output,
    State,
    ctx,
    html,
)

from app.config import SETTINGS
from app.figures import (
    density_figure,
    empty_figure,
    frequency_figure,
    intensity_figure,
    longevity_figure,
)
from app.services.analysis_service import (
    strongest_tracks,
    summary_metrics,
)
from app.services.dashboard_data_service import DashboardData
from app.services.filter_service import (
    clean_selection,
    create_criteria,
    filter_tracks,
    points_for_tracks,
)
from app.services.model_service import available_models
from app.ui.components import (
    density_card,
    model_distribution_table,
    records_table,
)


def register_analysis_callbacks(
    app: Dash,
    data: DashboardData,
) -> None:
    @app.callback(
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
        Output("model-stats-table", "children"),
        Output("density-heatmaps", "children"),
        Output("records-table", "children"),
        Output("selected-cyclone", "options"),
        Output("selected-cyclone", "value"),
        Input("apply-filters", "n_clicks"),
        Input("reset-filters", "n_clicks"),
        State("dataset-filter", "value"),
        State("region-filter", "value"),
        State("scenario-filter", "value"),
        State("tracker-filter", "value"),
        State("selected-models-store", "data"),
        State("year-filter", "value"),
        State("category-filter", "value"),
        State("selected-cyclone", "value"),
    )
    def update_analysis(
        _apply,
        _reset,
        dataset,
        regions,
        scenarios,
        tracker,
        models,
        years,
        minimum_category,
        current_cyclone,
    ):
        if ctx.triggered_id == "reset-filters":
            datasets = data.unique_values("dataset")
            trackers = data.unique_values("tracker")

            dataset = datasets[0] if datasets else None
            tracker = trackers[0] if trackers else None
            regions = data.unique_values("region")
            scenarios = data.unique_values("scenario")
            years = [data.year_min, data.year_max]
            minimum_category = 0
            models = available_models(data.tracks, dataset, tracker)[:SETTINGS.default_model_count]

        models = clean_selection(models)

        if not models:
            models = available_models(data.tracks, dataset, tracker)[:1]

        criteria = create_criteria(
            dataset,
            tracker,
            models,
            regions,
            scenarios,
            years,
            minimum_category,
        )

        selected = filter_tracks(data.tracks, criteria)

        if selected.empty:
            empty = empty_figure("No data match the active filters.")

            return (
                [],
                "0",
                "No matching records",
                "0",
                "0% of selection",
                "—",
                "No data",
                "—",
                "No data",
                "No records found",
                empty,
                empty,
                empty,
                html.Div("No matching data", className="empty-state"),
                [html.Div("No cyclone observations match the active filters.", className="empty-state")],
                records_table(selected),
                [],
                None,
            )

        selected_points = points_for_tracks(data.points, selected)
        metrics = summary_metrics(selected)
        strongest = strongest_tracks(selected)

        density_cards = []
        for model in models:
            model_tracks = selected[selected["driving_model"].eq(model)]
            model_points = points_for_tracks(selected_points, model_tracks)

            density_cards.append(
                density_card(
                    model,
                    model_tracks["track_id"].nunique(),
                    len(model_points),
                    density_figure(model_points, model),
                )
            )

        # Simplified cyclone selection label format
        selector_options = [
            {
                "label": (
                    f"Cyclone {row['raw_track_id']} ({row['season']}) · "
                    f"{row['driving_model']} · "
                    f"Cat {int(row['max_category'])} · "
                    f"{row['max_wind_speed']:.0f} km/h"
                ),
                "value": row["track_id"],
            }
            for _, row in strongest.iterrows()
        ]

        valid_values = {option["value"] for option in selector_options}

        cyclone_value = (
            current_cyclone
            if current_cyclone in valid_values
            else (selector_options[0]["value"] if selector_options else None)
        )

        model_text = ", ".join(models)

        return (
            selected["track_id"].tolist(),
            f"{metrics.cyclone_count:,}",
            f"{dataset} · {tracker} · {len(models)} model(s)",
            f"{metrics.landfall_count:,}",
            f"{metrics.landfall_rate:.1f}% of selection",
            f"{metrics.average_wind:.0f} km/h",
            f"Peak {metrics.peak_wind:.0f} km/h",
            f"{metrics.average_lifetime_hours:.0f} h",
            f"Median {metrics.median_lifetime_hours:.0f} h",
            f"Showing {len(selected):,} records · {years[0]}–{years[1]} · {model_text}",
            frequency_figure(selected),
            intensity_figure(selected),
            longevity_figure(selected),
            model_distribution_table(selected),
            density_cards,
            records_table(strongest),
            selector_options,
            cyclone_value,
        )