from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.config import (
    CATEGORY_COLOURS,
    SETTINGS,
)
from app.figures.common import empty_figure
from app.figures.theme import (
    MUTED_TEXT_COLOUR,
    model_colour_map,
    style_chart,
)
from app.services.analysis_service import (
    frequency_by_model,
    intensity_by_track,
    longevity_by_track,
)


# Australian cyclone category thresholds (km/h), as used in standardize.py.
CATEGORY_THRESHOLDS_KMH = [63, 89, 118, 160, 200]


def _colours(
    tracks: pd.DataFrame,
    colours: dict[str, str] | None,
) -> dict[str, str]:
    if colours:
        return colours

    return model_colour_map(
        sorted(tracks["driving_model"].dropna().astype(str).unique())
    )


def _model_order(
    tracks: pd.DataFrame,
    colours: dict[str, str],
) -> list[str]:
    """Models in the colour map's order (the sidebar order), then any others."""
    present = list(dict.fromkeys(tracks["driving_model"].dropna().astype(str)))
    ordered = [model for model in colours if model in present]
    return ordered + sorted(model for model in present if model not in ordered)


def frequency_figure(
    tracks: pd.DataFrame,
    colours: dict[str, str] | None = None,
) -> go.Figure:
    values = frequency_by_model(tracks)

    if values.empty:
        return empty_figure(
            "No frequency data match the filters."
        )

    colours = _colours(tracks, colours)

    figure = px.line(
        values,
        x="season",
        y="cyclones",
        color="driving_model",
        color_discrete_map=colours,
        category_orders={"driving_model": _model_order(tracks, colours)},
        labels={
            "season": "Season",
            "cyclones": "Cyclone tracks",
            "driving_model": "Model",
        },
    )

    figure.update_traces(line={"width": 2})
    style_chart(figure, height=390)
    figure.update_layout(hovermode="x unified")
    figure.update_yaxes(rangemode="tozero")
    figure.update_xaxes(showgrid=False, hoverformat="d")

    # Mark where historical runs end and SSP3-7.0 projections begin.
    boundary = SETTINGS.historical_end_year + 0.5
    seasons = pd.to_numeric(values["season"], errors="coerce")

    if seasons.min() < boundary < seasons.max():
        figure.add_vline(
            x=boundary,
            line={"color": MUTED_TEXT_COLOUR, "width": 1},
        )
        figure.add_annotation(
            x=boundary, xref="x", y=1, yref="paper",
            text="Historical ", xanchor="right", yanchor="top",
            showarrow=False, font={"size": 11, "color": MUTED_TEXT_COLOUR},
        )
        figure.add_annotation(
            x=boundary, xref="x", y=1, yref="paper",
            text=" SSP3-7.0", xanchor="left", yanchor="top",
            showarrow=False, font={"size": 11, "color": MUTED_TEXT_COLOUR},
        )

    return figure


def _model_box_figure(
    values: pd.DataFrame,
    value_column: str,
    axis_title: str,
    colours: dict[str, str],
) -> go.Figure:
    order = _model_order(values, colours)

    figure = px.box(
        values,
        x="driving_model",
        y=value_column,
        color="driving_model",
        points="outliers",
        color_discrete_map=colours,
        category_orders={"driving_model": order},
        labels={
            "driving_model": "Driving model",
            value_column: axis_title,
        },
    )

    figure.update_traces(
        line={"width": 1.5},
        marker={"size": 4, "opacity": 0.6},
        width=0.45,
    )
    style_chart(figure, height=390)
    figure.update_layout(showlegend=False, margin={"t": 12})
    figure.update_xaxes(showgrid=False, title=None)

    return figure


def intensity_figure(
    tracks: pd.DataFrame,
    colours: dict[str, str] | None = None,
) -> go.Figure:
    values = intensity_by_track(tracks)

    if values.empty:
        return empty_figure(
            "No intensity data match the filters."
        )

    figure = _model_box_figure(
        values,
        "max_wind_speed",
        "Peak wind (km/h)",
        _colours(tracks, colours),
    )

    # Category threshold rules, only where they fall inside the data range.
    peak = pd.to_numeric(values["max_wind_speed"], errors="coerce").max()

    for category, threshold in enumerate(CATEGORY_THRESHOLDS_KMH, start=1):
        if pd.isna(peak) or threshold > peak * 1.05:
            break

        # Room on the right for the C1-C5 labels.
        figure.update_layout(margin={"r": 36})

        figure.add_hline(
            y=threshold,
            line={"color": CATEGORY_COLOURS[category], "width": 1},
            layer="below",
            annotation_text=f"C{category}",
            annotation_position="right",
            annotation_font={"size": 11, "color": MUTED_TEXT_COLOUR},
        )

    return figure


def longevity_figure(
    tracks: pd.DataFrame,
    colours: dict[str, str] | None = None,
) -> go.Figure:
    values = longevity_by_track(tracks)

    if values.empty:
        return empty_figure(
            "No longevity data match the filters."
        )

    return _model_box_figure(
        values,
        "lifetime_days",
        "Duration (days)",
        _colours(tracks, colours),
    )
