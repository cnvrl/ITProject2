"""Dash callback registration."""

from dash import Dash

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