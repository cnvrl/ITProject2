"""Client-side page navigation without destroying existing dashboard callbacks."""
from dash import Input, Output, html


def _help_content():
    def section(title, *children):
        return html.Section([html.H2(title), *children], className="card help-section")

    return [
        html.Div([html.H1("How to use TC-Explorer 2.0"),
                  html.P("A guide to exploring and comparing tropical cyclone records."),
                  html.A("← Back to dashboard", href="/", className="btn btn-primary")], className="page-head"),
        section("Getting started",
                html.Ol([html.Li("Open the Dashboard and select the datasets, regions, scenarios and tracking methods in the filter sidebar."),
                         html.Li("Adjust the year range and minimum cyclone category as required."),
                         html.Li("Apply the filters to update summary cards, charts and cyclone records."),
                         html.Li("Select a cyclone from the records to inspect its track on the map."),
                         html.Li("Use Download CSV, Summary CSV or Report to export the available results.")])),
        section("Understanding the datasets",
                html.P([html.Strong("BARPA"), " — Bureau of Meteorology Atmospheric Regional Projections for Australia: a regional climate modelling framework that provides simulated atmospheric conditions."]),
                html.P([html.Strong("CCAM"), " — Conformal Cubic Atmospheric Model: an atmospheric model used for regional climate simulations."]),
                html.P("BARPA and CCAM are model sources, not tropical cyclone tracking algorithms. They can be analysed alongside driving models and scenarios where available.")),
        section("Understanding the cyclone trackers",
                html.P([html.Strong("TE (TempestExtremes)"), " — a software framework for detecting and tracking weather features, including tropical cyclones, in model output."]),
                html.P([html.Strong("CDD"), " — the Cyclone Detection and Tracking method used in this project to identify and follow cyclone systems."]),
                html.P("Different tracking algorithms may detect different numbers of storms or define tracks differently. Comparing TE and CDD helps examine sensitivity to tracking method; neither is itself a climate dataset.")),
        section("Reading the results",
                html.P("The summary cards provide high-level cyclone statistics. Frequency charts show counts over time; intensity charts show cyclone strength distributions. Select a record to inspect its geographic track."),
                html.P("Comparisons depend on the selected data, period and tracker. An empty chart can mean that no records match your filters, not necessarily that no cyclones occurred.")),
        section("Important limitations",
                html.P("Results are derived from the datasets loaded into this deployment and the processing rules used by the project. Climate-model simulations are not direct observations. Check the selected time period, model and tracker before interpreting differences.")),
    ]


def register_help_callbacks(app):
    @app.callback(
        Output("help-page-container", "children"),
        Output("help-page-container", "className"),
        Output("dashboard-main", "style"),
        Output("dashboard-sidebar-container", "style"),
        Input("page-url", "pathname"),
    )
    def display_page(pathname):
        if pathname == "/help":
            return _help_content(), "page help-page", {"display": "none"}, {"display": "none"}
        return [], "page help-page is-hidden", {}, {}
