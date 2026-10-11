"""Dash callback registration."""
"""
This file is used to register all callback functions for TC Explorer 2.0.

The main function register_callbacks() connects different callback modules
to the Dash application. It includes filters for selecting data, analysis
for updating results, maps for displaying cyclone information, export for
downloading results, and callbacks for the About and Help pages.

The file uses two main classes:
- Dash: Represents the main application and manages the callbacks.
- DashboardData: Provides the data needed by different callback modules.

Each callback is registered separately to keep the code organised and
make it easier to manage or update each part of the dashboard.
This file only connects the callbacks, while the actual functions and
processing are handled in their own modules.
"""

from dash import Dash

from app.callbacks.about import (
    register_about_callbacks,
)
from app.callbacks.analysis import (
    register_analysis_callbacks,
)
from app.callbacks.export import (
    register_export_callbacks,
)
from app.callbacks.filters import (
    register_filter_callbacks,
)
from app.callbacks.maps import (
    register_map_callbacks,
)
from app.services.dashboard_data_service import (
    DashboardData,
)


def register_callbacks(
    app: Dash,
    dashboard_data: DashboardData,
) -> None:
    register_filter_callbacks(
        app,
        dashboard_data,
    )

    register_analysis_callbacks(
        app,
        dashboard_data,
    )

    register_map_callbacks(
        app,
        dashboard_data,
    )

    register_export_callbacks(
        app,
        dashboard_data,
    )

    register_about_callbacks(app)
    from app.callbacks.help_page import register_help_callbacks
    register_help_callbacks(app)
