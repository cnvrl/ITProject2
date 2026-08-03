from __future__ import annotations

from datetime import datetime
import math
import random

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, callback, dcc, html, no_update


# -----------------------------------------------------------------------------
# Demo data
# Replace build_demo_data() with the real DataManager/API when available.
# -----------------------------------------------------------------------------
def build_demo_data(seed: int = 22) -> tuple[pd.DataFrame, pd.DataFrame]:
    random.seed(seed)

    datasets = ["Best Track", "BARPA", "CCAM"]
    scenarios = ["Historical", "Current", "Future +2K", "Future +4K"]
    regions = ["Australia", "Western", "Northern", "Eastern"]

    tracks: list[dict] = []
    points: list[dict] = []

    for index in range(1, 181):
        year = random.randint(1980, 2025)
        dataset = random.choices(datasets, weights=[0.38, 0.32, 0.30])[0]
        scenario = "Historical" if year < 2010 else random.choice(scenarios)
        tracker = "Observed" if dataset == "Best Track" else random.choice(["CDD", "TE"])
        region = random.choice(regions)
        category = random.choices([0, 1, 2, 3, 4, 5], weights=[15, 25, 24, 18, 12, 6])[0]
        max_wind = round(55 + category * 32 + random.uniform(-12, 18), 1)
        lifetime = round(random.uniform(30, 240), 1)
        landfall = random.random() < 0.39

        start_lat = random.uniform(-8, -22)
        start_lon = random.uniform(103, 166)
        n_points = random.randint(7, 16)
        track_id = f"TC-{year}-{index:03d}"
        genesis_date = datetime(year, random.randint(1, 4), random.randint(1, 25))

        end_lat = start_lat
        end_lon = start_lon

        for step in range(n_points):
            curve = math.sin(step / max(n_points - 1, 1) * math.pi)
            lat = start_lat - step * random.uniform(0.65, 1.15)
            lon = start_lon + step * random.uniform(-0.8, 0.75) + curve * random.uniform(-1.2, 1.2)
            wind = max(30, max_wind - abs(step - n_points * 0.55) * random.uniform(4, 9))
            point_category = min(5, max(0, int((wind - 55) // 32)))

            points.append(
                {
                    "track_id": track_id,
                    "step": step,
                    "lat": round(lat, 3),
                    "lon": round(lon, 3),
                    "wind_speed": round(wind, 1),
                    "category": point_category,
                }
            )
            end_lat, end_lon = lat, lon

        tracks.append(
            {
                "track_id": track_id,
                "name": f"Cyclone {index:03d}",
                "dataset": dataset,
                "scenario": scenario,
                "region": region,
                "tracker": tracker,
                "year": year,
                "max_category": category,
                "max_wind_speed": max_wind,
                "lifetime_hours": lifetime,
                "landfall": landfall,
                "genesis_lat": round(start_lat, 3),
                "genesis_lon": round(start_lon, 3),
                "last_lat": round(end_lat, 3),
                "last_lon": round(end_lon, 3),
                "genesis_date": genesis_date.date().isoformat(),
            }
        )

    return pd.DataFrame(tracks), pd.DataFrame(points)


TRACKS, POINTS = build_demo_data()
YEAR_MIN = int(TRACKS["year"].min())
YEAR_MAX = int(TRACKS["year"].max())

CATEGORY_COLOURS = {
    0: "#94a3b8",
    1: "#38bdf8",
    2: "#22c55e",
    3: "#facc15",
    4: "#fb923c",
    5: "#ef4444",
}


def options(values: list[str]) -> list[dict[str, str]]:
    return [{"label": value, "value": value} for value in values]


def stat_card(title: str, value_id: str, note_id: str, icon: str) -> html.Div:
    return html.Div(
        className="stat-card",
        children=[
            html.Div(icon, className="stat-icon", **{"aria-hidden": "true"}),
            html.Div(
                [
                    html.P(title, className="stat-title"),
                    html.H2(id=value_id, className="stat-value"),
                    html.P(id=note_id, className="stat-note"),
                ]
            ),
        ],
    )


def empty_figure(message: str, height: int = 340) -> go.Figure:
    figure = go.Figure()
    figure.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        showarrow=False,
        font={"size": 15, "color": "#64748b"},
    )
    figure.update_layout(
        template="plotly_white",
        height=height,
        autosize=False,
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return figure


def filter_tracks(
    datasets: list[str],
    regions: list[str],
    scenarios: list[str],
    trackers: list[str],
    years: list[int],
    minimum_category: int,
) -> pd.DataFrame:
    start_year, end_year = years

    return TRACKS[
        TRACKS["dataset"].isin(datasets or [])
        & TRACKS["region"].isin(regions or [])
        & TRACKS["scenario"].isin(scenarios or [])
        & TRACKS["tracker"].isin(trackers or [])
        & TRACKS["year"].between(start_year, end_year)
        & (TRACKS["max_category"] >= minimum_category)
    ].copy()


app = Dash(__name__, title="TC Explorer 2.0", suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div(
    className="app-shell",
    children=[
        dcc.Store(id="filtered-track-ids"),
        dcc.Download(id="download-csv"),

        html.Header(
            className="topbar",
            children=[
                html.Div(
                    className="brand",
                    children=[
                        html.Div("TC", className="brand-mark"),
                        html.Div(
                            [
                                html.H1("TC Explorer 2.0"),
                                html.P("Tropical cyclone analysis dashboard"),
                            ]
                        ),
                    ],
                ),
                html.Div(
                    className="topbar-actions",
                    children=[
                        html.Div(
                            [html.Span(className="status-dot"), html.Span("Demo data loaded")],
                            className="data-status",
                        ),
                        html.Button(
                            "Download CSV",
                            id="export-button",
                            className="button button-secondary",
                        ),
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
                                html.P("Refine the dashboard using the controls below."),
                            ],
                            className="sidebar-heading",
                        ),

                        html.Label("Dataset"),
                        dcc.Dropdown(
                            id="dataset-filter",
                            options=options(sorted(TRACKS["dataset"].unique().tolist())),
                            value=sorted(TRACKS["dataset"].unique().tolist()),
                            multi=True,
                            clearable=False,
                        ),

                        html.Label("Region"),
                        dcc.Dropdown(
                            id="region-filter",
                            options=options(sorted(TRACKS["region"].unique().tolist())),
                            value=sorted(TRACKS["region"].unique().tolist()),
                            multi=True,
                            clearable=False,
                        ),

                        html.Label("Scenario"),
                        dcc.Dropdown(
                            id="scenario-filter",
                            options=options(sorted(TRACKS["scenario"].unique().tolist())),
                            value=sorted(TRACKS["scenario"].unique().tolist()),
                            multi=True,
                            clearable=False,
                        ),

                        html.Label("Tracking method"),
                        dcc.Dropdown(
                            id="tracker-filter",
                            options=options(sorted(TRACKS["tracker"].unique().tolist())),
                            value=sorted(TRACKS["tracker"].unique().tolist()),
                            multi=True,
                            clearable=False,
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
                            min=YEAR_MIN,
                            max=YEAR_MAX,
                            value=[YEAR_MIN, YEAR_MAX],
                            step=1,
                            marks={
                                YEAR_MIN: str(YEAR_MIN),
                                2000: "2000",
                                YEAR_MAX: str(YEAR_MAX),
                            },
                        ),

                        html.Label("Minimum category"),
                        dcc.Slider(
                            id="category-filter",
                            min=0,
                            max=5,
                            value=0,
                            step=1,
                            marks={i: str(i) for i in range(6)},
                        ),

                        html.Div(
                            className="sidebar-buttons",
                            children=[
                                html.Button(
                                    "Apply filters",
                                    id="apply-filters",
                                    className="button button-primary",
                                ),
                                html.Button(
                                    "Reset",
                                    id="reset-filters",
                                    className="button button-ghost",
                                ),
                            ],
                        ),

                        html.Div(
                            className="sidebar-footnote",
                            children=[
                                html.Strong("Developer note"),
                                html.P(
                                    "The dashboard currently uses generated demonstration records. "
                                    "Replace build_demo_data() with the project DataManager or API later."
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
                                html.Div(
                                    [
                                        html.P("OVERVIEW", className="eyebrow"),
                                        html.H2("Cyclone activity dashboard"),
                                    ]
                                ),
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
                                html.Div(
                                    className="panel chart-panel",
                                    children=[
                                        html.Div(
                                            [
                                                html.H3("Cyclones per year"),
                                                html.P("Annual number of selected cyclone records"),
                                            ],
                                            className="panel-heading compact",
                                        ),
                                        dcc.Graph(
                                            id="frequency-chart",
                                            config={"displaylogo": False, "responsive": True},
                                            style={"height": "340px"},
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="panel chart-panel",
                                    children=[
                                        html.Div(
                                            [
                                                html.H3("Intensity distribution"),
                                                html.P("Maximum category reached"),
                                            ],
                                            className="panel-heading compact",
                                        ),
                                        dcc.Graph(
                                            id="intensity-chart",
                                            config={"displaylogo": False, "responsive": True},
                                            style={"height": "340px"},
                                        ),
                                    ],
                                ),
                            ],
                        ),

                        html.Section(
                            className="panel table-panel",
                            children=[
                                html.Div(
                                    className="panel-heading",
                                    children=[
                                        html.Div(
                                            [
                                                html.H3("Strongest cyclone records"),
                                                html.P(
                                                    "Select one cyclone to display its track on the map below"
                                                ),
                                            ]
                                        ),
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
                                        html.Div(
                                            [
                                                html.H3("Selected cyclone map"),
                                                html.P(
                                                    "Only the selected cyclone is displayed"
                                                ),
                                            ]
                                        ),
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


@callback(Output("year-label", "children"), Input("year-filter", "value"))
def show_year_range(years):
    return f"{years[0]}–{years[1]}"


@callback(
    Output("dataset-filter", "value"),
    Output("region-filter", "value"),
    Output("scenario-filter", "value"),
    Output("tracker-filter", "value"),
    Output("year-filter", "value"),
    Output("category-filter", "value"),
    Input("reset-filters", "n_clicks"),
    prevent_initial_call=True,
)
def reset_filters(_):
    return (
        sorted(TRACKS["dataset"].unique().tolist()),
        sorted(TRACKS["region"].unique().tolist()),
        sorted(TRACKS["scenario"].unique().tolist()),
        sorted(TRACKS["tracker"].unique().tolist()),
        [YEAR_MIN, YEAR_MAX],
        0,
    )


@callback(
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
    Output("records-table", "children"),
    Output("selected-cyclone", "options"),
    Input("apply-filters", "n_clicks"),
    Input("reset-filters", "n_clicks"),
    State("dataset-filter", "value"),
    State("region-filter", "value"),
    State("scenario-filter", "value"),
    State("tracker-filter", "value"),
    State("year-filter", "value"),
    State("category-filter", "value"),
)
def update_dashboard(
    _,
    __,
    datasets,
    regions,
    scenarios,
    trackers,
    years,
    minimum_category,
):
    selected = filter_tracks(
        datasets,
        regions,
        scenarios,
        trackers,
        years,
        minimum_category,
    )

    ids = selected["track_id"].tolist()

    if selected.empty:
        table = html.Div(
            "No cyclone records match the selected filters.",
            className="empty-state",
        )
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
            empty_figure("No frequency data"),
            empty_figure("No intensity data"),
            table,
            [],
        )

    count = len(selected)
    landfalls = int(selected["landfall"].sum())
    landfall_rate = landfalls / count * 100
    average_wind = selected["max_wind_speed"].mean()
    average_lifetime = selected["lifetime_hours"].mean()

    frequency = (
        selected.groupby("year", as_index=False)
        .size()
        .rename(columns={"size": "cyclones"})
    )
    frequency_figure = px.area(
        frequency,
        x="year",
        y="cyclones",
        markers=True,
    )
    frequency_figure.update_traces(
        line={"width": 2.5, "color": "#1769aa"},
        fillcolor="rgba(23,105,170,0.16)",
    )
    frequency_figure.update_layout(
        template="plotly_white",
        height=340,
        autosize=False,
        margin=dict(l=45, r=20, t=20, b=45),
        xaxis_title=None,
        yaxis_title="Cyclones",
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    distribution = (
        selected["max_category"]
        .value_counts()
        .reindex(range(6), fill_value=0)
        .reset_index()
    )
    distribution.columns = ["category", "cyclones"]

    intensity_figure = px.bar(
        distribution,
        x="category",
        y="cyclones",
    )
    intensity_figure.update_traces(
        marker_color=[
            CATEGORY_COLOURS[int(category)]
            for category in distribution["category"]
        ],
        hovertemplate="Category %{x}<br>%{y} cyclones<extra></extra>",
    )
    intensity_figure.update_layout(
        template="plotly_white",
        height=340,
        autosize=False,
        margin=dict(l=45, r=20, t=20, b=45),
        xaxis_title="Category",
        yaxis_title="Cyclones",
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    top = selected.sort_values(
        ["max_category", "max_wind_speed"],
        ascending=False,
    ).head(12)

    rows = []
    for _, row in top.iterrows():
        rows.append(
            html.Tr(
                [
                    html.Td(html.Strong(row["track_id"])),
                    html.Td(row["dataset"]),
                    html.Td(row["region"]),
                    html.Td(str(row["year"])),
                    html.Td(
                        html.Span(
                            f"Category {row['max_category']}",
                            className=f"category-pill category-{row['max_category']}",
                        )
                    ),
                    html.Td(f"{row['max_wind_speed']:.0f} km/h"),
                    html.Td(f"{row['lifetime_hours']:.0f} h"),
                    html.Td("Yes" if row["landfall"] else "No"),
                ]
            )
        )

    table = html.Table(
        [
            html.Thead(
                html.Tr(
                    [
                        html.Th("Track"),
                        html.Th("Dataset"),
                        html.Th("Region"),
                        html.Th("Year"),
                        html.Th("Intensity"),
                        html.Th("Peak wind"),
                        html.Th("Lifetime"),
                        html.Th("Landfall"),
                    ]
                )
            ),
            html.Tbody(rows),
        ]
    )

    selector_options = [
        {
            "label": (
                f"{row['track_id']} — Category {row['max_category']} — "
                f"{row['max_wind_speed']:.0f} km/h"
            ),
            "value": row["track_id"],
        }
        for _, row in top.iterrows()
    ]

    return (
        ids,
        f"{count:,}",
        f"Across {selected['dataset'].nunique()} datasets",
        f"{landfalls:,}",
        f"{landfall_rate:.1f}% of selection",
        f"{average_wind:.0f} km/h",
        f"Peak {selected['max_wind_speed'].max():.0f} km/h",
        f"{average_lifetime:.0f} h",
        f"Median {selected['lifetime_hours'].median():.0f} hours",
        f"Showing {count:,} records from {years[0]} to {years[1]}",
        frequency_figure,
        intensity_figure,
        table,
        selector_options,
    )


@callback(
    Output("cyclone-map", "figure"),
    Output("selected-cyclone-summary", "children"),
    Input("selected-cyclone", "value"),
)
def update_selected_map(selected_cyclone):
    if not selected_cyclone:
        return (
            empty_figure(
                "Select one cyclone above to display its track",
                height=430,
            ),
            "No cyclone selected",
        )

    record_frame = TRACKS[TRACKS["track_id"] == selected_cyclone]
    cyclone_points = POINTS[
        POINTS["track_id"] == selected_cyclone
    ].sort_values("step")

    if record_frame.empty or cyclone_points.empty:
        return (
            empty_figure("Selected cyclone data is unavailable", height=430),
            "Data unavailable",
        )

    record = record_frame.iloc[0]
    category = int(record["max_category"])

    figure = go.Figure()

    figure.add_trace(
        go.Scattergeo(
            lon=cyclone_points["lon"],
            lat=cyclone_points["lat"],
            mode="lines+markers",
            line={
                "width": 3,
                "color": CATEGORY_COLOURS[category],
            },
            marker={
                "size": 5,
                "color": CATEGORY_COLOURS[category],
            },
            name=selected_cyclone,
            customdata=cyclone_points[["wind_speed", "category"]],
            hovertemplate=(
                f"<b>{selected_cyclone}</b>"
                "<br>Wind: %{customdata[0]} km/h"
                "<br>Category: %{customdata[1]}"
                "<extra></extra>"
            ),
        )
    )

    figure.add_trace(
        go.Scattergeo(
            lon=[record["genesis_lon"]],
            lat=[record["genesis_lat"]],
            mode="markers",
            marker={
                "size": 11,
                "color": "#0f172a",
                "line": {"width": 2, "color": "white"},
            },
            name="Genesis",
            hovertemplate="<b>Genesis point</b><extra></extra>",
        )
    )

    if bool(record["landfall"]):
        figure.add_trace(
            go.Scattergeo(
                lon=[record["last_lon"]],
                lat=[record["last_lat"]],
                mode="markers",
                marker={
                    "size": 12,
                    "symbol": "x",
                    "color": "#7c3aed",
                    "line": {"width": 2},
                },
                name="Landfall endpoint",
                hovertemplate="<b>Landfall endpoint</b><extra></extra>",
            )
        )

    lon_padding = 5
    lat_padding = 5

    figure.update_geos(
        projection_type="mercator",
        lonaxis_range=[
            cyclone_points["lon"].min() - lon_padding,
            cyclone_points["lon"].max() + lon_padding,
        ],
        lataxis_range=[
            cyclone_points["lat"].min() - lat_padding,
            cyclone_points["lat"].max() + lat_padding,
        ],
        showland=True,
        landcolor="#e9eef3",
        showocean=True,
        oceancolor="#eaf7fb",
        showcoastlines=True,
        coastlinecolor="#94a3b8",
        showcountries=True,
        countrycolor="#cbd5e1",
        resolution=50,
    )
    figure.update_layout(
        height=430,
        autosize=False,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend={
            "orientation": "h",
            "y": 0.01,
            "x": 0.01,
            "bgcolor": "rgba(255,255,255,0.88)",
        },
        uirevision="selected-cyclone-map",
    )

    summary = (
        f"{selected_cyclone} · Category {category} · "
        f"{record['max_wind_speed']:.0f} km/h"
    )
    return figure, summary


@callback(
    Output("download-csv", "data"),
    Input("export-button", "n_clicks"),
    State("filtered-track-ids", "data"),
    prevent_initial_call=True,
)
def export_filtered_data(_, ids):
    if not ids:
        return no_update

    export_columns = [
        "track_id",
        "name",
        "dataset",
        "scenario",
        "region",
        "tracker",
        "year",
        "max_category",
        "max_wind_speed",
        "lifetime_hours",
        "landfall",
        "genesis_lat",
        "genesis_lon",
        "genesis_date",
    ]

    output = TRACKS[
        TRACKS["track_id"].isin(ids)
    ][export_columns]

    return dcc.send_data_frame(
        output.to_csv,
        "tc_explorer_filtered_records.csv",
        index=False,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
