from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.config import MODEL_COLOURS
from app.figures.common import empty_figure
from app.services.analysis_service import (
    frequency_by_model,
    intensity_by_track,
    longevity_by_track,
)


def frequency_figure(
    tracks: pd.DataFrame,
) -> go.Figure:
    values = frequency_by_model(tracks)

    if values.empty:
        return empty_figure(
            "No frequency data match the filters."
        )

    figure = px.line(
        values,
        x="season",
        y="cyclones",
        color="driving_model",
        markers=True,
        color_discrete_sequence=MODEL_COLOURS,
        labels={
            "season": "Season",
            "cyclones": "Cyclone tracks",
            "driving_model": "Model",
        },
    )

    figure.update_layout(
        template="plotly_white",
        height=390,
        hovermode="x unified",
        legend_title_text="Driving model",
        margin={
            "l": 55,
            "r": 25,
            "t": 20,
            "b": 50,
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    figure.update_yaxes(rangemode="tozero")

    return figure


def intensity_figure(
    tracks: pd.DataFrame,
) -> go.Figure:
    values = intensity_by_track(tracks)

    if values.empty:
        return empty_figure(
            "No intensity data match the filters."
        )

    figure = px.box(
        values,
        x="driving_model",
        y="max_wind_speed",
        color="driving_model",
        points="outliers",
        color_discrete_sequence=MODEL_COLOURS,
        labels={
            "driving_model": "Driving model",
            "max_wind_speed": "Peak wind (km/h)",
        },
    )

    figure.update_layout(
        template="plotly_white",
        height=390,
        showlegend=False,
        margin={
            "l": 60,
            "r": 25,
            "t": 20,
            "b": 90,
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return figure


def longevity_figure(
    tracks: pd.DataFrame,
) -> go.Figure:
    values = longevity_by_track(tracks)

    if values.empty:
        return empty_figure(
            "No longevity data match the filters."
        )

    figure = px.box(
        values,
        x="driving_model",
        y="lifetime_days",
        color="driving_model",
        points="outliers",
        color_discrete_sequence=MODEL_COLOURS,
        labels={
            "driving_model": "Driving model",
            "lifetime_days": "Duration (days)",
        },
    )

    figure.update_layout(
        template="plotly_white",
        height=390,
        showlegend=False,
        margin={
            "l": 60,
            "r": 25,
            "t": 20,
            "b": 90,
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return figure