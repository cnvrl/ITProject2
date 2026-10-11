"""
This file manages the callbacks for the About section in TC Explorer 2.0.

The main function register_about_callbacks() connects the About section
to the Dash application. It allows users to view, edit, save or cancel
changes to the project description and instructions.

The _display() function checks if the text is available and shows a
default message when there is no content.

The update_about() function handles the Edit, Save and Cancel buttons.
It uses load_about() to read the saved information and save_about() to
save new changes. It also checks for errors when saving and displays
a message if something goes wrong.

The code uses the Dash class, Input, Output, State and ctx to manage
user interactions. It also uses SETTINGS to control editing permissions,
file location and the maximum number of characters.

The CSS class variables are used to show or hide the editor and
buttons depending on what the user is doing.
"""
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
