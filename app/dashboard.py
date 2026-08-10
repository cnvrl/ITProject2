from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, callback, dcc, html, no_update

# ---------------------------------------------------------------------------
# Real data integration: DataManager -> Ingestor -> Loaders -> TCRecord
# ---------------------------------------------------------------------------
from app.services.data_manager import DataManager

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATASET_TYPE_BY_FILE = {
    "barpa_cdd_all_ssp370.csv": "barpa",
    "barpa_te_all_ssp370.csv": "barpa",
    "ccam_cdd_all_ssp370.csv": "ccam",
    "ccam_te_all_ssp370.csv": "ccam",
}

data_manager = DataManager(data_dir=DATA_DIR)


def load_real_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load every dataset file via DataManager/Ingestor and flatten TCRecord
    objects into two DataFrames: one per-track (TRACKS) and one per-point (POINTS).
    Falls back gracefully if a file fails to parse."""
    track_rows: list[dict] = []
    point_rows: list[dict] = []

    filenames = data_manager.list_datasets()
    csv_filenames = [f for f in filenames if f.lower().endswith(".csv")]

    for filename in csv_filenames:
        dataset_type = DATASET_TYPE_BY_FILE.get(filename)
        try:
            result = data_manager.load_dataset(filename, dataset_type=dataset_type)
        except Exception as exc:
            print(f"[dashboard] Skipping {filename}: {exc}")
            continue

        records = result.get("records", [])
        for record in records:
            track_rows.append(
                {
                    "track_id": record.track_id,
                    "name": record.track_id,
                    "dataset": record.model or record.dataset_id,
                    "scenario": record.scenario or "unknown",
                    "region": record.region or "unknown",
                    "tracker": record.tracker or "unknown",
                    "year": record.year,
                    "max_category": record.max_category if record.max_category is not None else 0,
                    "max_wind_speed": record.max_wind_speed if record.max_wind_speed is not None else 0.0,
                    "lifetime_hours": record.lifetime_hours if record.lifetime_hours is not None else 0.0,
                    "landfall": bool(record.landfall),
                    "genesis_lat": record.genesis_lat,
                    "genesis_lon": record.genesis_lon,
                    "last_lat": record.points[-1].lat if record.points else record.genesis_lat,
                    "last_lon": record.points[-1].lon if record.points else record.genesis_lon,
                    "genesis_date": record.genesis_time.date().isoformat() if record.genesis_time else None,
                }
            )
            for step, point in enumerate(record.points):
                point_rows.append(
                    {
                        "track_id": record.track_id,
                        "step": step,
                        "lat": point.lat,
                        "lon": point.lon,
                        "wind_speed": point.wind_speed if point.wind_speed is not None else 0.0,
                        "category": point.category if point.category is not None else 0,
                    }
                )

    tracks_df = pd.DataFrame(track_rows)
    points_df = pd.DataFrame(point_rows)

    if tracks_df.empty:
        raise RuntimeError("No cyclone records were loaded from data/. Check loader implementations and CSV headers.")

    tracks_df["year"] = tracks_df["year"].fillna(0).astype(int)
    return tracks_df, points_df


# ---------------------------------------------------------------------------
# Load real data (with a clear failure message if loaders are incomplete)
# ---------------------------------------------------------------------------
DATA_LOAD_ERROR: Optional[str] = None
try:
    TRACKS, POINTS = load_real_data()
except Exception as exc:  # noqa: BLE001
    DATA_LOAD_ERROR = str(exc)
    TRACKS = pd.DataFrame(
        columns=[
            "track_id", "name", "dataset", "scenario", "region", "tracker",
            "year", "max_category", "max_wind_speed", "lifetime_hours",
            "landfall", "genesis_lat", "genesis_lon", "last_lat", "last_lon",
            "genesis_date",
        ]
    )
    POINTS = pd.DataFrame(columns=["track_id", "step", "lat", "lon", "wind_speed", "category"])

YEAR_MIN = int(TRACKS["year"].min()) if not TRACKS.empty else 1980
YEAR_MAX = int(TRACKS["year"].max()) if not TRACKS.empty else 2025

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


def unique_sorted(column: str) -> list[str]:
    if TRACKS.empty or column not in TRACKS:
        return []
    return sorted(TRACKS[column].dropna().unique().tolist())


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
    if TRACKS.empty:
        return TRACKS.copy()

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
                            [
                                html.Span(className="status-dot"),
                                html.Span(
                                    "Real data loaded"
                                    if DATA_LOAD_ERROR is None
                                    else "Data load failed — see console"
                                ),
                            ],
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
                            options=options(unique_sorted("dataset")),
                            value=unique_sorted("dataset"),
                            multi=True,
                            clearable=False,
                        ),

                        html.Label("Region"),
                        dcc.Dropdown(
                            id="region-filter",
                            options=options(unique_sorted("region")),
                            value=unique_sorted("region"),
                            multi=True,
                            clearable=False,
                        ),

                        html.Label("Scenario"),
                        dcc.Dropdown(
                            id="scenario-filter",
                            options=options(unique_sorted("scenario")),
                            value=unique_sorted("scenario"),
                            multi=True,
                            clearable=False,
                        ),

                        html.Label("Tracking method"),
                        dcc.Dropdown(
                            id="tracker-filter",
                            options=options(unique_sorted("tracker")),
                            value=unique_sorted("tracker"),
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
                                html.Strong("Data source"),
                                html.P(
                                    "Tracks are loaded from CSV files in data/ through "
                                    "DataManager -> Ingestor -> loaders -> TCRecord."
                                    if DATA_LOAD_ERROR is None
                                    else f"Data load error: {DATA_LOAD_ERROR}"
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
                                stat_card("Total cyclones", "total-cyclones", "total-note", "\u25c9"),
                                stat_card("Landfalls", "total-landfalls", "landfall-note", "\u2316"),
                                stat_card("Average wind", "average-wind", "wind-note", "\u2197"),
                                stat_card("Average lifetime", "average-lifetime", "lifetime-note", "\u25f7"),
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
    return f"{years[0]}\u2013{years[1]}"


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
        unique_sorted("dataset"),
        unique_sorted("region"),
        unique_sorted("scenario"),
        unique_sorted("tracker"),
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
        message = (
            "No cyclone records match the selected filters."
            if DATA_LOAD_ERROR is None
            else f"No data loaded. {DATA_LOAD_ERROR}"
        )
        table = html.Div(message, className="empty-state")
        return (
            [],
            "0",
            "No matching records",
            "0",
            "0% of selection",
            "\u2014",
            "No data",
            "\u2014",
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
                f"{row['track_id']} \u2014 Category {row['max_category']} \u2014 "
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
        f"{selected_cyclone} \u00b7 Category {category} \u00b7 "
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
        "track_id", "name", "dataset", "scenario", "region", "tracker",
        "year", "max_category", "max_wind_speed", "lifetime_hours",
        "landfall", "genesis_lat", "genesis_lon", "genesis_date",
    ]

    output = TRACKS[TRACKS["track_id"].isin(ids)][export_columns]

    return dcc.send_data_frame(
        output.to_csv,
        "tc_explorer_filtered_records.csv",
        index=False,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)