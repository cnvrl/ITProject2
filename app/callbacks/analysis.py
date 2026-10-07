from __future__ import annotations

from dataclasses import replace

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
from app.figures.density_ttest import welch_pvalue_map_figure
from app.figures.theme import model_colour_map
from app.services.analysis_service import (
    strongest_tracks,
    summary_metrics,
)
from app.services.dashboard_data_service import DashboardData
from app.services.density_ttest_service import (
    compute_density_welch_p_grid,
    density_colour_max,
    track_density_grid,
)
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
        Output("welch-ttest-map", "figure"),
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
                empty,
                records_table(selected),
                [],
                None,
            )

        # One colour per model for every chart, table and map below.
        colours = model_colour_map(available_models(data.tracks, dataset, tracker) + list(models))

        selected_points = points_for_tracks(data.points, selected)
        metrics = summary_metrics(selected)
        strongest = strongest_tracks(selected)

        # Seasons each model covers under the active filters, ignoring the
        # minimum category, so a strict intensity filter that leaves some
        # seasons without tracks still divides by every season in range.
        coverage = filter_tracks(
            data.tracks,
            replace(criteria, minimum_category=0),
        )

        density_maps = []
        for model in models:
            model_tracks = selected[selected["driving_model"].eq(model)]
            model_points = points_for_tracks(selected_points, model_tracks)
            model_seasons = coverage.loc[
                coverage["driving_model"].eq(model),
                "season",
            ].nunique()

            grid, lon_centers, lat_centers = track_density_grid(
                model_points,
                n_seasons=model_seasons,
                cell_degrees=SETTINGS.density_cell_degrees,
                lon_range=(SETTINGS.density_min_longitude, SETTINGS.density_max_longitude),
                lat_range=(SETTINGS.density_min_latitude, SETTINGS.density_max_latitude),
            )
            density_maps.append((model, model_tracks, model_points, grid, lon_centers, lat_centers))

        # One colour scale for every model, so the maps can be compared.
        shared_max = density_colour_max([grid for _, _, _, grid, _, _ in density_maps])

        # Smaller tiles when more models share the row.
        tile_height = {1: 560, 2: 470}.get(len(density_maps), 400)

        density_cards = [
            density_card(
                model,
                model_tracks["track_id"].nunique(),
                len(model_points),
                density_figure(
                    grid,
                    lon_centers,
                    lat_centers,
                    model,
                    zmax=shared_max,
                    height=tile_height,
                ),
                colour=colours.get(model),
                height=tile_height,
            )
            for model, model_tracks, model_points, grid, lon_centers, lat_centers in density_maps
        ]

        hist_points = selected_points[selected_points["season"] <= SETTINGS.historical_end_year]
        fut_points = selected_points[selected_points["season"] > SETTINGS.historical_end_year]

        welch_res = compute_density_welch_p_grid(
            hist_points,
            fut_points,
        )
        welch_fig = welch_pvalue_map_figure(welch_res)

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
            frequency_figure(selected, colours),
            intensity_figure(selected, colours),
            longevity_figure(selected, colours),
            model_distribution_table(selected, colours),
            density_cards,
            welch_fig,
            records_table(strongest, colours),
            selector_options,
            cyclone_value,
        )