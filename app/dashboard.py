from __future__ import annotations

from dash import Dash

from app.callbacks import register_callbacks
from app.config import SETTINGS, ensure_runtime_directories
from app.services.dashboard_data_service import load_dashboard_data
from app.ui.layout import create_layout


def create_app() -> Dash:
    """Create and configure the TC Explorer application."""

    ensure_runtime_directories()

    dashboard_data = load_dashboard_data(
        data_dir=SETTINGS.data_dir,
    )

    dash_app = Dash(
        __name__,
        title=SETTINGS.app_name,
        suppress_callback_exceptions=True,
        assets_folder=str(SETTINGS.assets_dir),
    )

    dash_app.layout = create_layout(
        dashboard_data=dashboard_data,
    )

    register_callbacks(
        app=dash_app,
        dashboard_data=dashboard_data,
    )

    return dash_app


app = create_app()
server = app.server


if __name__ == "__main__":
    app.run(
        debug=SETTINGS.debug,
        host=SETTINGS.host,
        port=SETTINGS.port,
    )