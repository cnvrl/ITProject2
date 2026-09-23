from __future__ import annotations

from dash import dcc, html

from app.config import SETTINGS
from app.services.dashboard_data_service import DashboardData
from app.ui.components import (
    chart_panel,
    dropdown_options,
    stat_card,
)


def create_layout(dashboard_data: DashboardData) -> html.Div:
    datasets = dashboard_data.unique_values("dataset")
    trackers = dashboard_data.unique_values("tracker")
    regions = dashboard_data.unique_values("region")
    scenarios = dashboard_data.unique_values("scenario")

    year_min = dashboard_data.year_min
    year_max = dashboard_data.year_max

    default_dataset = datasets[0] if datasets else None
    default_tracker = trackers[0] if trackers else None

    return html.Div(
        className="app-shell",
        children=[
            dcc.Store(id="filtered-track-ids", data=[]),
            dcc.Store(id="selected-models-store", data=[]),
            dcc.Download(id="download-csv"),
            dcc.Download(id="download-summary"),
            dcc.Download(id="download-report"),

            html.Header(
                className="topbar",
                children=[
                    html.Div(
                        className="brand",
                        children=[
                            html.Div("TC", className="brand-mark"),
                            html.Div([
                                html.H1(SETTINGS.app_name),
                                html.P(SETTINGS.app_description),
                            ]),
                        ],
                    ),
                    html.Div(
                        className="topbar-actions",
                        children=[
                            html.Div(
                                [
                                    html.Span(className="status-dot"),
                                    html.Span(
                                        "Real data loaded"
                                        if dashboard_data.is_loaded
                                        else "Data unavailable"
                                    ),
                                ],
                                className="data-status",
                            ),
                            html.Button("Download CSV", id="export-button", className="button button-secondary"),
                            html.Button("Summary CSV", id="summary-button", className="button button-secondary"),
                            html.Button("Report", id="report-button", className="button button-secondary"),
                        ],
                    ),
                ],
            ),

            html.Div(
                className="dashboard-grid",
                children=[
                    html.Aside(
                        className="sidebar",
                        children=[
                            html.Div(
                                [
                                    html.H2("Filters"),
                                    html.P("Refine the analysis."),
                                ],
                                className="sidebar-heading",
                            ),

                            html.Label("Dataset"),
                            dcc.Dropdown(
                                id="dataset-filter",
                                options=dropdown_options(datasets),
                                value=default_dataset,
                                clearable=False,
                                searchable=False,
                                className="filter-dropdown",
                            ),

                            html.Label("Region"),
                            dcc.Dropdown(
                                id="region-filter",
                                options=dropdown_options(regions),
                                value=regions,
                                multi=True,
                                clearable=False,
                                className="filter-dropdown",
                            ),

                            html.Label("Scenario"),
                            dcc.Dropdown(
                                id="scenario-filter",
                                options=dropdown_options(scenarios),
                                value=scenarios,
                                multi=True,
                                clearable=False,
                                className="filter-dropdown",
                            ),

                            html.Label("Cyclone tracker"),
                            dcc.Dropdown(
                                id="tracker-filter",
                                options=dropdown_options(trackers),
                                value=default_tracker,
                                clearable=False,
                                searchable=False,
                                className="filter-dropdown",
                            ),

                            html.Label("Number of models"),
                            dcc.Dropdown(
                                id="model-count-filter",
                                options=[{"label": "1 model", "value": 1}],
                                value=1,
                                clearable=False,
                                searchable=False,
                                className="filter-dropdown",
                            ),

                            html.Div(
                                id="model-selectors-container",
                                className="model-selector-container",
                            ),

                            html.Div(
                                id="model-availability-message",
                                className="filter-message",
                                role="status",
                                **{"aria-live": "polite"},
                            ),

                            html.Div(
                                [
                                    html.Label("Year range"),
                                    html.Span(id="year-label"),
                                ],
                                className="label-row",
                            ),

                            dcc.RangeSlider(
                                id="year-filter",
                                min=year_min,
                                max=year_max,
                                value=[year_min, year_max],
                                step=1,
                                marks={year_min: str(year_min), year_max: str(year_max)},
                            ),

                            html.Label("Minimum category"),
                            dcc.Slider(
                                id="category-filter",
                                min=0,
                                max=5,
                                value=0,
                                step=1,
                                marks={v: str(v) for v in range(6)},
                            ),

                            html.Div(
                                className="sidebar-buttons",
                                children=[
                                    html.Button("Apply filters", id="apply-filters", className="button button-primary"),
                                    html.Button("Reset", id="reset-filters", className="button button-ghost"),
                                ],
                            ),

                            html.Div(
                                className="sidebar-footnote",
                                children=[
                                    html.Strong("Data source & benchmarks"),
                                    html.P(
                                        f"{len(dashboard_data.tracks):,} tracks loaded. "
                                        f"In CORDEX/CMIP6 simulations, historical runs end in {SETTINGS.historical_end_year}, "
                                        f"and future scenario projections begin in {SETTINGS.historical_end_year + 1}."
                                    ),
                                ],
                            ),
                        ],
                    ),

                    html.Main(
                        className="main-content",
                        children=[
                            html.Section(
                                className="page-heading",
                                children=[
                                    html.Div([
                                        html.P("OVERVIEW", className="eyebrow"),
                                        html.H2("Cyclone activity dashboard"),
                                    ]),
                                    html.P(id="result-summary", className="result-summary"),
                                ],
                            ),

                            html.Section(
                                className="stat-grid",
                                children=[
                                    stat_card("Total cyclones", "total-cyclones", "total-note", "◉"),
                                    stat_card("Landfalls", "total-landfalls", "landfall-note", "⌖"),
                                    stat_card("Average wind", "average-wind", "wind-note", "↗"),
                                    stat_card("Average lifetime", "average-lifetime", "lifetime-note", "◷"),
                                ],
                            ),

                            html.Section(
                                className="chart-grid",
                                children=[
                                    chart_panel("Frequency comparison", "Unique tracks per season", "frequency-chart", wide=True),
                                    chart_panel("Intensity comparison", "Peak wind by model", "intensity-chart"),
                                    chart_panel("Longevity comparison", "Duration by model", "longevity-chart"),
                                ],
                            ),

                            html.Section(
                                className="panel",
                                children=[
                                    html.Div(
                                        [
                                            html.H3("Model statistics summary"),
                                            html.P("Intensity (Wind speed km/h) & Longevity (Duration in days) quantiles"),
                                        ],
                                        className="panel-heading compact",
                                    ),
                                    html.Div(id="model-stats-table", className="table-wrap"),
                                ],
                            ),

                            html.Section(
                                className="panel heatmap-panel",
                                children=[
                                    html.Div(
                                        [
                                            html.H3("Filtered track density"),
                                            html.P("One filtered Australia map per model."),
                                        ],
                                        className="panel-heading",
                                    ),
                                    dcc.Loading(
                                        html.Div(id="density-heatmaps", className="heatmap-comparison-grid"),
                                        type="circle",
                                    ),
                                ],
                            ),

                            html.Section(
                                className="panel table-panel",
                                children=[
                                    html.Div(
                                        className="panel-heading",
                                        children=[
                                            html.Div([
                                                html.H3("Strongest cyclones"),
                                                html.P("Select a track to map it."),
                                            ]),
                                            dcc.Dropdown(
                                                id="selected-cyclone",
                                                placeholder="Select a cyclone...",
                                                clearable=True,
                                                className="cyclone-selector",
                                            ),
                                        ],
                                    ),
                                    html.Div(id="records-table", className="table-wrap"),
                                ],
                            ),

                            html.Section(
                                className="panel selected-map-panel",
                                children=[
                                    html.Div(
                                        className="panel-heading",
                                        children=[
                                            html.Div([
                                                html.H3("Selected cyclone track"),
                                                html.P("Australia reference map"),
                                            ]),
                                            html.Div(id="selected-cyclone-summary", className="selected-summary"),
                                        ],
                                    ),
                                    dcc.Loading(
                                        dcc.Graph(
                                            id="cyclone-map",
                                            config={"displaylogo": False, "responsive": True},
                                            style={"height": "430px"},
                                        ),
                                        type="circle",
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )