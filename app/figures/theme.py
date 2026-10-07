from __future__ import annotations

from typing import Iterable

import plotly.graph_objects as go

from app.config import (
    MODEL_COLOURS,
    MODEL_REFERENCE_COLOUR,
)


# Shared chart styling, matched to app/assets/style.css.
FONT_FAMILY = "Poppins, 'Segoe UI', system-ui, -apple-system, sans-serif"
TEXT_COLOUR = "#2a3547"
MUTED_TEXT_COLOUR = "#5a6a85"
GRID_COLOUR = "#edf1f5"
CARD_COLOUR = "#ffffff"
BORDER_COLOUR = "#e5edf3"


def model_colour_map(models: Iterable[str]) -> dict[str, str]:
    """
    Fixed colour per driving model.

    Pass every model available for the chosen dataset and tracker, in a
    stable order, so a model keeps its colour when others are added or
    removed from the comparison. ERA5 reanalysis always uses the reference
    ink rather than a series colour.
    """
    colours: dict[str, str] = {}
    slot = 0

    for model in models:
        if model in colours:
            continue

        if str(model).upper() == "ERA5":
            colours[model] = MODEL_REFERENCE_COLOUR
            continue

        colours[model] = MODEL_COLOURS[slot % len(MODEL_COLOURS)]
        slot += 1

    return colours


def style_chart(
    figure: go.Figure,
    height: int,
) -> go.Figure:
    """Apply the dashboard's chart styling to a cartesian Plotly figure."""
    axis_style = {
        "gridcolor": GRID_COLOUR,
        "zeroline": False,
        "showline": False,
        "ticks": "",
        "tickfont": {"size": 11.5, "color": MUTED_TEXT_COLOUR},
        "title_font": {"size": 12, "color": MUTED_TEXT_COLOUR},
        "automargin": True,
    }

    figure.update_layout(
        template="plotly_white",
        height=height,
        autosize=True,
        font={"family": FONT_FAMILY, "size": 12, "color": MUTED_TEXT_COLOUR},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 8, "r": 12, "t": 36, "b": 8},
        hoverlabel={
            "bgcolor": CARD_COLOUR,
            "bordercolor": BORDER_COLOUR,
            "font": {"family": FONT_FAMILY, "size": 12, "color": TEXT_COLOUR},
        },
        legend={
            "orientation": "h",
            "x": 1,
            "xanchor": "right",
            "y": 1.02,
            "yanchor": "bottom",
            "title_text": "",
            "font": {"size": 12, "color": MUTED_TEXT_COLOUR},
        },
    )
    figure.update_xaxes(**axis_style)
    figure.update_yaxes(**axis_style)

    return figure
