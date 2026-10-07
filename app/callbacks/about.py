from __future__ import annotations

from dash import (
    Dash,
    Input,
    Output,
    State,
    ctx,
    no_update,
)

from app.config import SETTINGS
from app.services.about_service import (
    load_about,
    save_about,
)


VIEW_CLASS = "about-grid"
FORM_CLASS = "about-form"
EDIT_CLASS = "btn btn-outline"
HIDDEN = " is-hidden"


def _display(text: str, placeholder: str) -> str:
    return text if text else placeholder


def register_about_callbacks(app: Dash) -> None:
    @app.callback(
        Output("about-description", "children"),
        Output("about-instructions", "children"),
        Output("about-view", "className"),
        Output("about-form", "className"),
        Output("about-edit", "className"),
        Output("about-description-input", "value"),
        Output("about-instructions-input", "value"),
        Output("about-status", "children"),
        Input("about-edit", "n_clicks"),
        Input("about-cancel", "n_clicks"),
        Input("about-save", "n_clicks"),
        State("about-description-input", "value"),
        State("about-instructions-input", "value"),
    )
    def update_about(
        _edit,
        _cancel,
        _save,
        description_input,
        instructions_input,
    ):
        """Show the saved text on load, open the editor on Edit, and save on Save."""
        trigger = ctx.triggered_id
        editable = SETTINGS.allow_about_edit
        edit_class = EDIT_CLASS if editable else EDIT_CLASS + HIDDEN
        content = load_about(SETTINGS.about_file)

        if trigger == "about-edit" and editable:
            return (
                no_update,
                no_update,
                VIEW_CLASS + HIDDEN,
                FORM_CLASS,
                EDIT_CLASS + HIDDEN,
                content["description"],
                content["instructions"],
                "",
            )

        status = ""

        if trigger == "about-save" and editable:
            try:
                content = save_about(
                    SETTINGS.about_file,
                    description_input,
                    instructions_input,
                    SETTINGS.about_max_chars,
                )
            except ValueError as error:
                return (
                    no_update,
                    no_update,
                    VIEW_CLASS + HIDDEN,
                    FORM_CLASS,
                    EDIT_CLASS + HIDDEN,
                    no_update,
                    no_update,
                    str(error),
                )
            except OSError:
                return (
                    no_update,
                    no_update,
                    VIEW_CLASS + HIDDEN,
                    FORM_CLASS,
                    EDIT_CLASS + HIDDEN,
                    no_update,
                    no_update,
                    "Couldn't write the description file. Check that the app can write to "
                    f"{SETTINGS.about_file.parent} and try again.",
                )

            status = "Saved"

        return (
            _display(content["description"], "No description yet."),
            _display(content["instructions"], "No instructions yet."),
            VIEW_CLASS,
            FORM_CLASS + HIDDEN,
            edit_class,
            no_update,
            no_update,
            status,
        )
