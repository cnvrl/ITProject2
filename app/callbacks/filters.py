"""
This file manages the filter callbacks for TC Explorer 2.0.

The main function register_filter_callbacks() connects the filter section
to the Dash application. It allows users to select different datasets,
trackers, regions, scenarios, years, cyclone categories and models.

The file includes several callback functions:
- show_year_range() displays the selected year range.
- update_model_count() checks the available models and updates how many
  models users can select for comparison.
- render_model_selectors() creates the model dropdown menus based on the
  selected dataset and tracker. It also shows a message if some models
  are missing from the loaded data.
- prevent_duplicate_models() prevents users from selecting the same model
  in different dropdown menus.
- colour_model_dot() updates the colour indicator for each selected model.
- store_selected_models() saves the selected models for other callbacks.
- reset_filters() returns the filter options to their default values.

The code uses two main classes, Dash and DashboardData. Dash manages the
application and its callbacks, while DashboardData provides the cyclone
data and available filter values.

It also uses Input, Output, State and ctx to manage user interactions.
ALL and MATCH are used to handle multiple model dropdown menus.
The dcc and html components are used to create the filter interface.

Supporting functions from model_service and filter_service are used to
check available models, prepare dropdown options and clean selected values.
The model_colour_map() function gives each model its own colour, while
SETTINGS controls the default number of models.

Overall, this file makes sure the filter options work correctly and
allows users to select different cyclone models for comparison.
"""
from __future__ import annotations

from dash import (
    ALL,
    MATCH,
    Dash,
    Input,
    Output,
    State,
    ctx,
    dcc,
    html,
)

from app.config import SETTINGS
from app.figures.theme import model_colour_map
from app.services.dashboard_data_service import (
    DashboardData,
)
from app.services.filter_service import (
    clean_selection,
)
from app.services.model_service import (
    available_models,
    configured_models,
    loaded_models,
    model_options,
)


def register_filter_callbacks(
    app: Dash,
    data: DashboardData,
) -> None:
    @app.callback(
        Output("year-label", "children"),
        Input("year-filter", "value"),
    )
    def show_year_range(years):
        if not years or len(years) != 2:
            return ""

        return f"{years[0]}–{years[1]}"

    @app.callback(
        Output("model-count-filter", "options"),
        Output("model-count-filter", "value"),
        Input("dataset-filter", "value"),
        Input("tracker-filter", "value"),
        Input("reset-filters", "n_clicks"),
        State("model-count-filter", "value"),
    )
    def update_model_count(
        dataset,
        tracker,
        _reset,
        current,
    ):
        available = available_models(
            data.tracks,
            dataset,
            tracker,
        )

        maximum = max(1, len(available))

        count_options = [
            {
                "label": (
                    f"{number} model"
                    if number == 1
                    else f"{number} models"
                ),
                "value": number,
            }
            for number in range(
                1,
                maximum + 1,
            )
        ]

        if ctx.triggered_id == "reset-filters":
            value = min(
                SETTINGS.default_model_count,
                maximum,
            )
        else:
            value = min(
                max(int(current or 1), 1),
                maximum,
            )

        return count_options, value

    @app.callback(
        Output(
            "model-selectors-container",
            "children",
        ),
        Output(
            "model-availability-message",
            "children",
        ),
        Input("model-count-filter", "value"),
        Input("dataset-filter", "value"),
        Input("tracker-filter", "value"),
        State(
            {
                "type": "comparison-model",
                "index": ALL,
            },
            "value",
        ),
    )
    def render_model_selectors(
        model_count,
        dataset,
        tracker,
        previous_values,
    ):
        available = available_models(
            data.tracks,
            dataset,
            tracker,
        )

        configured = configured_models(
            dataset,
            tracker,
        )

        present = set(
            loaded_models(
                data.tracks,
                dataset,
                tracker,
            )
        )

        if not available:
            return (
                [],
                (
                    f"No models are available for "
                    f"{dataset} + {tracker}."
                ),
            )

        requested = min(
            int(model_count or 1),
            len(available),
        )

        selected = [
            value
            for value in clean_selection(
                previous_values
            )
            if value in available
        ][:requested]

        for model in available:
            if len(selected) >= requested:
                break

            if model not in selected:
                selected.append(model)

        colours = model_colour_map(available)
        controls = []

        for index in range(requested):
            current_value = selected[index]
            selected_elsewhere = set(selected)
            selected_elsewhere.discard(
                current_value
            )

            controls.append(
                html.Div(
                    [
                        html.Label(
                            f"Model {index + 1}"
                        ),
                        html.Div(
                            [
                                html.Span(
                                    id={
                                        "type": "model-dot",
                                        "index": index,
                                    },
                                    className="dot",
                                    style={
                                        "backgroundColor": colours.get(
                                            current_value
                                        ),
                                    },
                                ),
                        dcc.Dropdown(
                            id={
                                "type": (
                                    "comparison-model"
                                ),
                                "index": index,
                            },
                            options=model_options(
                                data.tracks,
                                dataset,
                                tracker,
                                selected_elsewhere=(
                                    selected_elsewhere
                                ),
                                current_value=(
                                    current_value
                                ),
                            ),
                            value=current_value,
                            clearable=False,
                            searchable=True,
                            className=(
                                "filter-dropdown "
                                "model-dropdown"
                            ),
                        ),
                            ],
                            className="model-field",
                        ),
                    ],
                    className=(
                        "dynamic-model-selector"
                    ),
                )
            )

        unavailable = [
            model
            for model in configured
            if model not in present
        ]

        message = (
            f"{len(available)} models available for "
            f"{dataset} + {tracker}."
        )

        if unavailable:
            message += (
                " Missing from loaded data: "
                + ", ".join(unavailable)
                + "."
            )

        return controls, message

    @app.callback(
        Output(
            {
                "type": "comparison-model",
                "index": ALL,
            },
            "options",
        ),
        Input(
            {
                "type": "comparison-model",
                "index": ALL,
            },
            "value",
        ),
        State("dataset-filter", "value"),
        State("tracker-filter", "value"),
        prevent_initial_call=True,
    )
    def prevent_duplicate_models(
        values,
        dataset,
        tracker,
    ):
        selected = clean_selection(values)
        outputs = []

        for current in values or []:
            other_values = set(selected)
            other_values.discard(current)

            outputs.append(
                model_options(
                    data.tracks,
                    dataset,
                    tracker,
                    selected_elsewhere=(
                        other_values
                    ),
                    current_value=current,
                )
            )

        return outputs

    @app.callback(
        Output(
            {
                "type": "model-dot",
                "index": MATCH,
            },
            "style",
        ),
        Input(
            {
                "type": "comparison-model",
                "index": MATCH,
            },
            "value",
        ),
        State("dataset-filter", "value"),
        State("tracker-filter", "value"),
        prevent_initial_call=True,
    )
    def colour_model_dot(
        value,
        dataset,
        tracker,
    ):
        colours = model_colour_map(
            available_models(
                data.tracks,
                dataset,
                tracker,
            )
        )

        return {
            "backgroundColor": colours.get(
                value,
                "#a9b5c1",
            ),
        }

    @app.callback(
        Output(
            "selected-models-store",
            "data",
        ),
        Input(
            {
                "type": "comparison-model",
                "index": ALL,
            },
            "value",
        ),
    )
    def store_selected_models(values):
        return clean_selection(values)

    @app.callback(
        Output("dataset-filter", "value"),
        Output("region-filter", "value"),
        Output("scenario-filter", "value"),
        Output("tracker-filter", "value"),
        Output("year-filter", "value"),
        Output("category-filter", "value"),
        Input("reset-filters", "n_clicks"),
        prevent_initial_call=True,
    )
    def reset_filters(_clicks):
        datasets = data.unique_values(
            "dataset"
        )

        trackers = data.unique_values(
            "tracker"
        )

        return (
            datasets[0] if datasets else None,
            data.unique_values("region"),
            data.unique_values("scenario"),
            trackers[0] if trackers else None,
            [
                data.year_min,
                data.year_max,
            ],
            0,
        )