"""Regression harness for the October 2026 TC-Explorer application.

Run with: python -m pytest tests/test_tc_harness_updated.py -v
Tests use small deterministic fixtures and do not load the large supplied CSV files.
"""
from pathlib import Path
import ast
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_navigation_is_present():
    """Ensure both navigation links exist. This catches accidental removal of the
    Help entry point during future changes to the top navigation bar."""
    source = (ROOT / 'app/ui/layout.py').read_text()
    assert 'href="/help"' in source
    assert 'href="/"' in source


def test_help_page_covers_key_workflows():
    """Check the user guide includes the four essential user actions: selecting
    filters, inspecting results, selecting cyclone tracks and exporting data."""
    source = (ROOT / 'app/callbacks/help_page.py').read_text()
    for phrase in ('Apply the filters', 'Select a cyclone', 'Download CSV', 'year range'):
        assert phrase in source


def test_help_page_distinguishes_models_and_trackers():
    """Prevent confusing atmospheric models with cyclone-tracking algorithms.
    BARPA/CCAM represent climate modelling sources; TE/CDD identify tracks."""
    source = (ROOT / 'app/callbacks/help_page.py').read_text()
    for label in ('BARPA', 'CCAM', 'TempestExtremes', 'CDD'):
        assert label in source
    assert 'not tropical cyclone tracking algorithms' in source


@pytest.mark.parametrize('filename', [
    'app/dashboard.py', 'app/ui/layout.py', 'app/callbacks/help_page.py',
    'app/callbacks/filters.py', 'app/callbacks/analysis.py',
    'app/services/filter_service.py', 'app/services/analysis_service.py',
    'app/services/dashboard_data_service.py', 'app/pipeline/validators.py',
    'app/pipeline/standardize.py', 'app/pipeline/segmentation.py',
])
def test_python_modules_compile(filename):
    """Syntax smoke test for each critical backend/frontend module. Useful when
    modules are edited independently or merged from teammates' branches."""
    ast.parse((ROOT / filename).read_text(), filename=filename)


def test_help_navigation_callback_registered():
    """Confirm that the Help callback is wired into the main Dash callback
    registration; merely creating help_page.py would not make navigation work."""
    source = (ROOT / 'app/callbacks/__init__.py').read_text()
    assert 'register_help_callbacks(app)' in source


def test_existing_dashboard_callbacks_preserved():
    """Ensure the new page has not replaced existing dashboard callback groups.
    Filters, analysis, map selection, exports and About must remain registered."""
    source = (ROOT / 'app/callbacks/__init__.py').read_text()
    for callback in ('register_filter_callbacks', 'register_analysis_callbacks',
                     'register_map_callbacks', 'register_export_callbacks',
                     'register_about_callbacks'):
        assert callback in source


def test_help_page_styles_present():
    """Confirm the new page has scoped CSS so its appearance matches the app
    without unintentionally overriding existing dashboard chart/card styling."""
    css = (ROOT / 'app/assets/style.css').read_text()
    assert '.help-page' in css
    assert '.help-section' in css


def test_project_required_data_sources_exist():
    """Verify the supplied project bundle includes all four model/tracker
    combinations expected by the dashboard. This checks file presence, not CSV
    correctness; a separate data-validation test should check data contents."""
    for name in ('barpa_cdd_all_ssp370.csv', 'barpa_te_all_ssp370.csv',
                 'ccam_cdd_all_ssp370.csv', 'ccam_te_all_ssp370.csv'):
        assert (ROOT / 'data' / name).is_file()


def test_help_page_render_and_routes():
    """Integration check: build the Help page and verify its headings. Skips
    cleanly if Dash is not installed in a backend-only development environment."""
    pytest.importorskip('dash')
    from app.callbacks.help_page import _help_content
    elements = _help_content()
    assert len(elements) >= 5
    assert elements[0].className == 'page-head'
