from __future__ import annotations

import pandas as pd
from dash import dcc, html

from app.config import CATEGORY_COLOURS
from app.figures.common import empty_figure


GRAPH_CONFIG = {"displaylogo": False, "responsive": True}
LOADING_COLOUR = "#1b84ff"


def dropdown_options(
    values: list[str],
) -> list[dict[str, str]]:
    return [
        {
            "label": value,
            "value": value,
        }
        for value in values
    ]


def icon(name: str, extra_class: str = "") -> html.Span:
    """Inline icon drawn by CSS (see the .icon-* rules in assets/style.css)."""
    return html.Span(
        className=f"icon icon-{name} {extra_class}".strip(),
        **{"aria-hidden": "true"},
    )


def colour_dot(colour: str | None) -> html.Span:
    return html.Span(
        className="dot",
        style={"backgroundColor": colour or "#a9b5c1"},
        **{"aria-hidden": "true"},
    )


def model_label(model: str, colour: str | None) -> html.Span:
    return html.Span(
        [colour_dot(colour), model],
        className="model-cell",
    )


def stat_card(
    title: str,
    value_id: str,
    note_id: str,
    icon_name: str,
    tone: str = "blue",
) -> html.Div:
    return html.Div(
        className="card stat",
        children=[
            html.Div(
                icon(icon_name),
                className=f"stat-icon {tone}",
            ),
            html.Div(
                [
                    html.P(title, className="stat-label"),
                    html.Div(id=value_id, className="stat-value"),
                    html.P(id=note_id, className="stat-note"),
                ]
            ),
        ],
    )


def card_heading(
    title: str,
    description: str | None = None,
    *,
    title_id: str | None = None,
    description_id: str | None = None,
    actions=None,
) -> html.Div:
    text = [html.H2(title, id=title_id) if title_id else html.H2(title)]

    if description is not None or description_id:
        text.append(
            html.P(description, id=description_id)
            if description_id
            else html.P(description)
        )

    children = [html.Div(text)]

    if actions is not None:
        children.append(html.Div(actions, className="card-actions"))

    return html.Div(children, className="card-head")


def chart_panel(
    title: str,
    description: str,
    graph_id: str,
    *,
    note: str | None = None,
    height: int = 390,
    extra_class: str = "",
) -> html.Article:
    children = [
        card_heading(title, description),
        dcc.Loading(
            dcc.Graph(
                id=graph_id,
                figure=empty_figure(
                    "Apply filters to display results.",
                    height=height,
                ),
                config=GRAPH_CONFIG,
                style={"height": f"{height}px"},
            ),
            type="circle",
            color=LOADING_COLOUR,
        ),
    ]

    if note:
        children.append(html.P(note, className="note"))

    return html.Article(
        children,
        className=f"card chart-card {extra_class}".strip(),
    )


def category_pill(category: int) -> html.Span:
    category = int(max(0, min(5, category)))

    return html.Span(
        [
            html.Span(
                className="sw",
                style={"backgroundColor": CATEGORY_COLOURS[category]},
            ),
            f"Category {category}",
        ],
        className=f"pill category-pill category-{category}",
    )


def category_legend() -> html.Div:
    return html.Div(
        [
            html.Span(
                [colour_dot(CATEGORY_COLOURS[category]), f"Cat {category}"],
            )
            for category in range(6)
        ],
        className="legend category-legend",
    )


def summary_chip(label: str, value: str) -> html.Div:
    return html.Div(
        [html.Small(label), html.B(value)],
        className="vs",
    )


def model_distribution_table(
    tracks: pd.DataFrame,
    colours: dict[str, str] | None = None,
) -> html.Table:
    """Render statistical metrics (Min, Q1, Median, Q3, Max, Mean) per model."""
    if tracks.empty:
        return html.Div("No data available for statistics.", className="empty-state")

    colours = colours or {}
    rows = []
    for model, group in tracks.groupby("driving_model"):
        wind = pd.to_numeric(group["max_wind_speed"], errors="coerce").dropna()
        days = (pd.to_numeric(group["lifetime_hours"], errors="coerce") / 24.0).dropna()

        if wind.empty or days.empty:
            continue

        rows.append(
            html.Tr([
                html.Td(model_label(model, colours.get(model))),
                html.Td(f"{len(group):,}", className="num"),
                html.Td(f"{wind.quantile(0.25):.1f} / {days.quantile(0.25):.1f}", className="num"),
                html.Td(f"{wind.median():.1f} / {days.median():.1f}", className="num"),
                html.Td(f"{wind.quantile(0.75):.1f} / {days.quantile(0.75):.1f}", className="num"),
                html.Td(f"{wind.min():.0f}–{wind.max():.0f} / {days.min():.1f}–{days.max():.1f}", className="num"),
                html.Td(f"{wind.mean():.1f} / {days.mean():.1f}", className="num"),
            ])
        )

    return html.Table([
        html.Thead(
            html.Tr([
                html.Th("Model"),
                html.Th("Tracks", className="num"),
                html.Th("Q1 (km/h / days)", className="num"),
                html.Th("Median", className="num"),
                html.Th("Q3", className="num"),
                html.Th("Min–max", className="num"),
                html.Th("Mean", className="num"),
            ])
        ),
        html.Tbody(rows),
    ])


def records_table(
    tracks: pd.DataFrame,
    colours: dict[str, str] | None = None,
) -> html.Div | html.Table:
    if tracks.empty:
        return html.Div(
            "No cyclone records match the filters.",
            className="empty-state",
        )

    colours = colours or {}
    rows = []
    for _, row in tracks.iterrows():
        landfall = (
            html.Span([icon("pin", "icon-sm"), "Yes"], className="yes")
            if row["landfall"]
            else "No"
        )

        rows.append(
            html.Tr([
                html.Td(
                    html.Strong(f"Cyclone {row['raw_track_id']} ({row['season']})"),
                    className="track-id",
                ),
                html.Td(row["dataset"]),
                html.Td(model_label(row["driving_model"], colours.get(row["driving_model"]))),
                html.Td(row["tracker"]),
                html.Td(row["region"]),
                html.Td(str(row["season"]), className="num"),
                html.Td(category_pill(int(row["max_category"]))),
                html.Td(f"{row['max_wind_speed']:.0f} km/h", className="num"),
                html.Td(f"{row['lifetime_hours']:.0f} h", className="num"),
                html.Td(landfall),
            ])
        )

    return html.Table([
        html.Thead(
            html.Tr([
                html.Th("Track"),
                html.Th("Dataset"),
                html.Th("Model"),
                html.Th("Tracker"),
                html.Th("Region"),
                html.Th("Season", className="num"),
                html.Th("Intensity"),
                html.Th("Peak wind", className="num"),
                html.Th("Lifetime", className="num"),
                html.Th("Landfall"),
            ])
        ),
        html.Tbody(rows),
    ])


def density_card(
    model: str,
    track_count: int,
    point_count: int,
    figure,
    colour: str | None = None,
    height: int = 500,
) -> html.Div:
    return html.Div(
        className="tile",
        children=[
            html.Div(
                [
                    html.B(model_label(model, colour)),
                    html.Small(f"{track_count:,} tracks · {point_count:,} observations"),
                ],
                className="tile-head",
            ),
            dcc.Graph(
                figure=figure,
                config=GRAPH_CONFIG,
                style={"height": f"{height}px"},
            ),
        ],
    )
