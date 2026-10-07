from __future__ import annotations

from dash import dcc, html

from app.config import SETTINGS
from app.services.dashboard_data_service import DashboardData
from app.ui.components import (
    GRAPH_CONFIG,
    LOADING_COLOUR,
    card_heading,
    category_legend,
    chart_panel,
    dropdown_options,
    icon,
    stat_card,
)


def _field(label: str, control, *, label_row=None) -> html.Div:
    heading = label_row if label_row is not None else html.Label(label)
    return html.Div([heading, control], className="field")


def _chips(component_id: str, values: list[str]) -> dcc.Checklist:
    """Multi-select shown as toggle chips; the value is a list, like a multi dropdown."""
    return dcc.Checklist(
        id=component_id,
        options=dropdown_options(values),
        value=values,
        inline=True,
        className="chips",
        labelClassName="chip",
        inputClassName="chip-input",
    )


def _top_bar(dashboard_data: DashboardData) -> html.Header:
    return html.Header(
        className="appbar",
        children=[
            html.Div(
                className="brand",
                children=[
                    icon("cyclone", "brand-glyph"),
                    html.Div(
                        ["TC", html.Span(" Explorer"), " 2.0"],
                        className="brand-name",
                        title=SETTINGS.app_description,
                    ),
                ],
            ),
            html.Div(className="appbar-spacer"),
            html.Div(
                [
                    html.Span(className="status-dot"),
                    html.Span(
                        "Real data loaded"
                        if dashboard_data.is_loaded
                        else "Data unavailable",
                        className="status-text",
                    ),
                ],
                className="status-chip" + ("" if dashboard_data.is_loaded else " is-error"),
                role="status",
            ),
            html.Div(
                className="appbar-actions",
                children=[
                    html.Button(
                        [icon("download"), html.Span("Download CSV")],
                        id="export-button",
                        className="bar-btn",
                        title="Download the filtered tracks as CSV",
                    ),
                    html.Button(
                        [icon("sheet"), html.Span("Summary CSV")],
                        id="summary-button",
                        className="bar-btn",
                        title="Download the model comparison summary as CSV",
                    ),
                    html.Button(
                        [icon("report"), html.Span("Report")],
                        id="report-button",
                        className="bar-btn",
                        title="Download the interpretation report",
                    ),
                ],
            ),
        ],
    )


def _sidebar(dashboard_data: DashboardData) -> html.Aside:
    datasets = dashboard_data.unique_values("dataset")
    trackers = dashboard_data.unique_values("tracker")
    regions = dashboard_data.unique_values("region")
    scenarios = dashboard_data.unique_values("scenario")

    year_min = dashboard_data.year_min
    year_max = dashboard_data.year_max

    return html.Aside(
        className="sidebar",
        **{"aria-label": "Filters"},
        children=[
            html.Div(
                className="banner",
                children=[
                    html.Div(icon("cyclone"), className="banner-avatar"),
                    html.Div(
                        [
                            html.Strong("Tropical cyclone tracks"),
                            html.Small(
                                " · ".join(datasets + ["SSP3-7.0"])
                                if datasets
                                else "No datasets loaded"
                            ),
                        ],
                        className="banner-meta",
                    ),
                ],
            ),
            html.Div(
                className="filters",
                children=[
                    html.Div(
                        [
                            html.Div("Filters", className="side-label"),
                            html.P("Refine the analysis."),
                        ],
                        className="side-head",
                    ),
                    _field(
                        "Dataset",
                        dcc.Dropdown(
                            id="dataset-filter",
                            options=dropdown_options(datasets),
                            value=datasets[0] if datasets else None,
                            clearable=False,
                            searchable=False,
                            className="filter-dropdown",
                        ),
                    ),
                    _field("Region", _chips("region-filter", regions)),
                    _field("Scenario", _chips("scenario-filter", scenarios)),
                    _field(
                        "Cyclone tracker",
                        dcc.Dropdown(
                            id="tracker-filter",
                            options=dropdown_options(trackers),
                            value=trackers[0] if trackers else None,
                            clearable=False,
                            searchable=False,
                            className="filter-dropdown",
                        ),
                    ),
                    _field(
                        "Number of models",
                        dcc.Dropdown(
                            id="model-count-filter",
                            options=[{"label": "1 model", "value": 1}],
                            value=1,
                            clearable=False,
                            searchable=False,
                            className="filter-dropdown",
                        ),
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
                    _field(
                        "Year range",
                        dcc.RangeSlider(
                            id="year-filter",
                            min=year_min,
                            max=year_max,
                            value=[year_min, year_max],
                            step=1,
                            marks={year_min: str(year_min), year_max: str(year_max)},
                            allowCross=False,
                        ),
                        label_row=html.Div(
                            [
                                html.Label("Year range"),
                                html.Span(id="year-label", className="label-value"),
                            ],
                            className="label-row",
                        ),
                    ),
                    _field(
                        "Minimum category",
                        dcc.Slider(
                            id="category-filter",
                            min=0,
                            max=5,
                            value=0,
                            step=1,
                            marks={value: str(value) for value in range(6)},
                        ),
                    ),
                    html.Div(
                        className="side-buttons",
                        children=[
                            html.Button("Apply filters", id="apply-filters", className="btn btn-primary"),
                            html.Button("Reset", id="reset-filters", className="btn btn-text"),
                        ],
                    ),
                    html.Div(
                        className="footnote",
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
        ],
    )


def _about_card() -> html.Section:
    return html.Section(
        className="card about-card",
        **{"aria-labelledby": "about-title"},
        children=[
            card_heading(
                "Description & instructions",
                "What this website is for and how to use it",
                title_id="about-title",
                actions=[
                    html.Span(id="about-status", className="about-status", role="status"),
                    html.Button(
                        [icon("edit", "icon-sm"), "Edit"],
                        id="about-edit",
                        className="btn btn-outline" + ("" if SETTINGS.allow_about_edit else " is-hidden"),
                    ),
                ],
            ),
            html.Div(
                id="about-view",
                className="about-grid",
                children=[
                    html.Div(
                        [
                            html.H3([icon("info", "icon-sm"), "Description"]),
                            html.P(id="about-description", className="about-text"),
                        ],
                        className="about-block",
                    ),
                    html.Div(
                        [
                            html.H3([icon("list", "icon-sm"), "Instructions"]),
                            html.P(id="about-instructions", className="about-text"),
                        ],
                        className="about-block",
                    ),
                ],
            ),
            html.Div(
                id="about-form",
                className="about-form is-hidden",
                children=[
                    html.Div(
                        className="about-grid",
                        children=[
                            html.Div(
                                [
                                    html.Label("Description", htmlFor="about-description-input"),
                                    dcc.Textarea(
                                        id="about-description-input",
                                        maxLength=SETTINGS.about_max_chars,
                                        placeholder="Describe what TC Explorer does, the datasets it covers and who it is for.",
                                        className="textarea",
                                    ),
                                ],
                                className="field",
                            ),
                            html.Div(
                                [
                                    html.Label("Instructions", htmlFor="about-instructions-input"),
                                    dcc.Textarea(
                                        id="about-instructions-input",
                                        maxLength=SETTINGS.about_max_chars,
                                        placeholder="One step per line, e.g. 1. Choose a dataset and tracker in the sidebar.",
                                        className="textarea",
                                    ),
                                ],
                                className="field",
                            ),
                        ],
                    ),
                    html.Div(
                        className="about-actions",
                        children=[
                            html.Button("Save", id="about-save", className="btn btn-primary"),
                            html.Button("Cancel", id="about-cancel", className="btn btn-text"),
                        ],
                    ),
                ],
            ),
        ],
    )


def create_layout(dashboard_data: DashboardData) -> html.Div:
    return html.Div(
        className="app-shell",
        children=[
            dcc.Store(id="filtered-track-ids", data=[]),
            dcc.Store(id="selected-models-store", data=[]),
            dcc.Download(id="download-csv"),
            dcc.Download(id="download-summary"),
            dcc.Download(id="download-report"),

            _top_bar(dashboard_data),

            html.Div(
                className="shell",
                children=[
                    _sidebar(dashboard_data),

                    html.Main(
                        className="page",
                        children=[
                            html.Section(
                                className="page-head",
                                children=[
                                    html.Div([
                                        html.H1("Cyclone activity dashboard"),
                                        html.Div(
                                            [
                                                html.Span("Dashboard"),
                                                html.Span("›", **{"aria-hidden": "true"}),
                                                html.B("Overview"),
                                            ],
                                            className="crumbs",
                                        ),
                                    ]),
                                    html.P(id="result-summary", className="result-summary"),
                                ],
                            ),

                            _about_card(),

                            html.Section(
                                className="grid stats",
                                **{"aria-label": "Summary"},
                                children=[
                                    stat_card("Total cyclones", "total-cyclones", "total-note", "cyclone", "blue"),
                                    stat_card("Landfalls", "total-landfalls", "landfall-note", "pin", "teal"),
                                    stat_card("Average wind", "average-wind", "wind-note", "wind", "amber"),
                                    stat_card("Average lifetime", "average-lifetime", "lifetime-note", "clock", "green"),
                                ],
                            ),

                            chart_panel(
                                "Frequency comparison",
                                "Unique tracks per season",
                                "frequency-chart",
                                note=(
                                    "A season is labelled by the year it ends. Historical runs end in "
                                    f"{SETTINGS.historical_end_year} and SSP3-7.0 projections begin in "
                                    f"{SETTINGS.historical_end_year + 1}."
                                ),
                            ),

                            html.Section(
                                className="grid two-up",
                                children=[
                                    chart_panel(
                                        "Intensity comparison",
                                        "Peak wind by model",
                                        "intensity-chart",
                                        note=(
                                            "Boxes show the interquartile range and median; whiskers reach "
                                            "1.5 times the interquartile range, with outliers as dots. Coloured "
                                            "rules mark the Australian category thresholds (C1–C5)."
                                        ),
                                    ),
                                    chart_panel(
                                        "Longevity comparison",
                                        "Duration by model",
                                        "longevity-chart",
                                        note="Same box convention as the intensity chart, in days from first to last track point.",
                                    ),
                                ],
                            ),

                            html.Section(
                                className="card",
                                children=[
                                    card_heading(
                                        "Model statistics summary",
                                        "Intensity (wind speed km/h) and longevity (duration in days) quantiles",
                                    ),
                                    html.Div(id="model-stats-table", className="table-wrap"),
                                ],
                            ),

                            html.Section(
                                className="card",
                                children=[
                                    card_heading("Filtered track density", "One filtered Australia map per model"),
                                    dcc.Loading(
                                        html.Div(id="density-heatmaps", className="tiles"),
                                        type="circle",
                                        color=LOADING_COLOUR,
                                    ),
                                    html.P(
                                        "Distinct tracks entering each 2° cell per season, averaged over the "
                                        "seasons in the filter. Cells over land count cyclones that made "
                                        "landfall or crossed the coast. All maps share one colour scale.",
                                        className="note",
                                    ),
                                ],
                            ),

                            html.Section(
                                className="card",
                                children=[
                                    card_heading(
                                        "Statistical significance & Welch's t-test map",
                                        "Mean seasonal density change (future − historical) per grid cell; "
                                        "crosses mark cells significant at p < 0.05",
                                    ),
                                    dcc.Loading(
                                        dcc.Graph(
                                            id="welch-ttest-map",
                                            config=GRAPH_CONFIG,
                                            style={"height": "480px"},
                                        ),
                                        type="circle",
                                        color=LOADING_COLOUR,
                                    ),
                                ],
                            ),

                            html.Section(
                                className="card",
                                children=[
                                    card_heading(
                                        "Strongest cyclones",
                                        "Select a track to map it.",
                                        actions=dcc.Dropdown(
                                            id="selected-cyclone",
                                            placeholder="Select a cyclone…",
                                            clearable=True,
                                            className="cyclone-selector",
                                        ),
                                    ),
                                    html.Div(id="records-table", className="table-wrap"),
                                ],
                            ),

                            html.Section(
                                className="card",
                                children=[
                                    card_heading("Selected cyclone track", "Points coloured by category at each time step"),
                                    html.Div(
                                        className="track-layout",
                                        children=[
                                            dcc.Loading(
                                                dcc.Graph(
                                                    id="cyclone-map",
                                                    config=GRAPH_CONFIG,
                                                    style={"height": "430px"},
                                                ),
                                                type="circle",
                                                color=LOADING_COLOUR,
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(id="selected-cyclone-summary", className="summary-chips"),
                                                    category_legend(),
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            ),

                            html.Footer(
                                "TC Explorer 2.0 · IT Project II – Group 2 · Team Susanoo",
                                className="footer",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
