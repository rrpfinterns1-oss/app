"""Headless run of the Streamlit app: every tab renders and the main flows work."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from carbon_explorer.ui.state import TABS

APP = Path(__file__).resolve().parent.parent / "streamlit_app.py"


@pytest.fixture
def app():
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    assert not at.exception
    return at


def by_label(widgets, label):
    return next(w for w in widgets if w.label == label)


def test_all_tabs_render(app):
    assert [t.label for t in app.tabs] == list(TABS)
    assert not app.error


def test_year_selection_is_shared_between_portfolio_and_emissions(app):
    app.button_group(key="portfolio_year").set_value(2031).run()
    assert app.session_state["emissions_year"] == 2031
    app.button_group(key="emissions_year").set_value(2028).run()
    assert app.session_state["portfolio_year"] == 2028
    assert not app.exception


def test_build_save_and_reload_a_scenario(app):
    by_label(app.slider, "Share of selected emissions to offset").set_value(40).run()
    by_label(app.selectbox, "Carbon project").set_value("Bondhu Chula Stoves").run()
    app.text_input(key="sb_name").input("Forty percent").run()
    by_label(app.button, "Save scenario").click().run()
    assert not app.exception

    saved = {s.name: s for s in app.session_state["scenarios"]}
    assert "Forty percent" in saved
    s = saved["Forty percent"]
    assert s.offset_pct == 40 and s.project == "Bondhu Chula Stoves" and s.year == 2026
    assert len(s.selected) == 13  # every family is selected by default
    # The name field moves on to a fresh default after saving.
    assert app.session_state["sb_name"] != "Forty percent"

    # Change the builder, then load the saved scenario back into it.
    by_label(app.slider, "Share of selected emissions to offset").set_value(0).run()
    index = [x.name for x in app.session_state["scenarios"]].index("Forty percent")
    app.button(key=f"open_{index}_Forty percent").click().run()
    assert app.session_state["sb_offset"] == 40
    assert app.session_state["sb_project"] == "Bondhu Chula Stoves"
    assert app.session_state["nav"] == "Scenario Builder"
    assert not app.exception


def test_changing_builder_year_reloads_workbook_quantities(app):
    app.select_slider(key="sb_year").set_value(2030).run()
    anchor = app.session_state["sb_anchor"]
    assert anchor["Workbook qty"].sum() == 217
    assert (anchor["Scenario qty"] == anchor["Workbook qty"]).all()
    assert not app.exception


def test_selection_helpers(app):
    by_label(app.button, "Clear").click().run()
    assert not app.session_state["sb_anchor"]["Offset"].any()
    by_label(app.button, "With engines").click().run()
    anchor = app.session_state["sb_anchor"]
    assert (anchor["Offset"] == (anchor["Scenario qty"] > 0)).all()


def test_examples_preloaded_and_removable(app):
    assert len(app.session_state["scenarios"]) == 4
    by_label(app.button, "Remove all scenarios").click().run()
    assert app.session_state["scenarios"] == []
    by_label(app.button, "Restore illustrative examples").click().run()
    assert len(app.session_state["scenarios"]) == 4
    assert not app.exception


def test_add_note(app):
    by_label(app.text_area, "Observation").input("Targeted offset covers 70.5%.")
    by_label(app.text_input, "Title (optional)").input("Coverage")
    app.button(key="FormSubmitter:note_form-Add note").click().run()
    notes = app.session_state["notes"]
    assert len(notes) == 1 and notes[0]["title"] == "Coverage"
    assert not app.exception


def test_line_chart_option_on_portfolio_and_emissions(app):
    app.button_group(key="portfolio_chart").set_value("Line").run()
    assert app.session_state["emissions_chart"] == "Line"
    assert not app.exception
    # The per-family line chart lets any family be highlighted.
    app.selectbox(key="portfolio_focus").set_value("Trent 7000").run()
    app.selectbox(key="emissions_focus").set_value("LEAP 1-A").run()
    app.button_group(key="emissions_year").set_value(2033).run()
    assert not app.exception
    app.button_group(key="emissions_chart").set_value("Bar").run()
    assert app.session_state["portfolio_chart"] == "Bar"
    assert not app.exception
