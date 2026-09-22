from __future__ import annotations

import pandas as pd
from dash import dcc, html

from app.figures.common import empty_figure


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


def stat_card(
    title: str,
    value_id: str,
    note_id: str,
    icon: str,
) -> html.Div:
    return html.Div(
        className="stat-card",
        children=[
            html.Div(
                icon,
                className="stat-icon",
                **{"aria-hidden": "true"},
            ),
            html.Div(
                [
                    html.P(
                        title,
                        className="stat-title",
                    ),
                    html.H2(
                        id=value_id,
                        className="stat-value",
                    ),
                    html.P(
                        id=note_id,
                        className="stat-note",
                    ),
                ]
            ),
        ],
    )


def chart_panel(
    title: str,
    description: str,
    graph_id: str,
    *,
    wide: bool = False,
) -> html.Div:
    style = (
        {"gridColumn": "1 / -1"}
        if wide
        else None
    )

    return html.Div(
        className="panel chart-panel",
        style=style,
        children=[
            html.Div(
                [
                    html.H3(title),
                    html.P(description),
                ],
                className="panel-heading compact",
            ),
            dcc.Loading(
                dcc.Graph(
                    id=graph_id,
                    figure=empty_figure(
                        "Apply filters to display results.",
                        height=390,
                    ),
                    config={
                        "displaylogo": False,
                        "responsive": True,
                    },
                    style={
                        "height": "390px",
                    },
                ),
                type="circle",
            ),
        ],
    )


def records_table(
    tracks: pd.DataFrame,
) -> html.Div | html.Table:
    if tracks.empty:
        return html.Div(
            "No cyclone records match the filters.",
            className="empty-state",
        )

    rows = []

    for _, row in tracks.iterrows():
        category = int(row["max_category"])

        rows.append(
            html.Tr(
                [
                    html.Td(
                        [
                            html.Strong(
                                (
                                    f"Cyclone "
                                    f"{row['raw_track_id']} "
                                    f"({row['season']})"
                                )
                            ),
                            html.Small(
                                (
                                    f"{row['dataset']} · "
                                    f"{row['tracker']} · "
                                    f"{row['driving_model']}"
                                ),
                                className="track-meta",
                            ),
                        ]
                    ),
                    html.Td(row["dataset"]),
                    html.Td(row["driving_model"]),
                    html.Td(row["tracker"]),
                    html.Td(row["region"]),
                    html.Td(str(row["season"])),
                    html.Td(
                        html.Span(
                            f"Category {category}",
                            className=(
                                f"category-pill "
                                f"category-{category}"
                            ),
                        )
                    ),
                    html.Td(
                        f"{row['max_wind_speed']:.0f} km/h"
                    ),
                    html.Td(
                        f"{row['lifetime_hours']:.0f} h"
                    ),
                    html.Td(
                        "Yes"
                        if row["landfall"]
                        else "No"
                    ),
                ]
            )
        )

    return html.Table(
        [
            html.Thead(
                html.Tr(
                    [
                        html.Th("Track"),
                        html.Th("Dataset"),
                        html.Th("Model"),
                        html.Th("Tracker"),
                        html.Th("Region"),
                        html.Th("Season"),
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


def density_card(
    model: str,
    track_count: int,
    point_count: int,
    figure,
) -> html.Div:
    return html.Div(
        className="panel chart-panel",
        children=[
            html.Div(
                [
                    html.H3(
                        f"{model} track density"
                    ),
                    html.P(
                        (
                            f"{track_count:,} tracks · "
                            f"{point_count:,} observations"
                        )
                    ),
                ],
                className="panel-heading compact",
            ),
            dcc.Graph(
                figure=figure,
                config={
                    "displaylogo": False,
                    "responsive": True,
                },
                style={
                    "height": "500px",
                },
            ),
        ],
    )