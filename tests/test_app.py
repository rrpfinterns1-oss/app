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
    # After saving, the builder carries on changing that scenario.
    assert app.session_state["sb_editing"] == "Forty percent"
    assert app.session_state["sb_pick"] == "Forty percent"

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


def test_charts_tab_draws_every_dataset_as_bar_and_line(app):
    from carbon_explorer.ui.views.explore import DATASETS

    for ds in DATASETS:
        app.selectbox(key="ex_data").set_value(ds.label).run()
        for kind in ("Line", "Bar"):
            app.button_group(key="ex_kind").set_value(kind).run()
            assert not app.exception, (ds.label, kind)
    # Time-series data: change the families shown and the year range.
    app.selectbox(key="ex_data").set_value("Engine quantities by year").run()
    app.multiselect(key="ex_show_Engine quantities by year").set_value(
        ["Portfolio total", "Trent 7000"]).run()
    app.select_slider(key="ex_years").set_value((2028, 2033)).run()
    assert not app.exception


EXAMPLE_B = "B · Partial offset (2026)"
EXAMPLE_C = "C · Targeted offset (2026)"


def names(app):
    return [s.name for s in app.session_state["scenarios"]]


def test_change_a_saved_scenario_from_the_picker(app):
    assert app.session_state["sb_pick"] == "__new__"
    app.selectbox(key="sb_pick").set_value(EXAMPLE_B).run()
    assert app.session_state["sb_offset"] == 50
    assert app.session_state["sb_editing"] == EXAMPLE_B

    by_label(app.slider, "Share of selected emissions to offset").set_value(75).run()
    app.button(key="sb_save_changes").click().run()
    b = app.session_state["scenarios"][names(app).index(EXAMPLE_B)]
    assert b.offset_pct == 75 and not b.illustrative
    assert len(names(app)) == 4

    # "Save as new" needs a name that is not taken.
    app.button(key="sb_save_new").click().run()
    assert len(names(app)) == 4 and app.error
    app.text_input(key="sb_name").input("B at 75%").run()
    app.button(key="sb_save_new").click().run()
    assert names(app)[-1] == "B at 75%" and app.session_state["sb_editing"] == "B at 75%"

    # Deleting the scenario being changed keeps its values as a new, unsaved one.
    app.button(key="sb_delete").click().run()
    assert "B at 75%" not in names(app)
    assert app.session_state["sb_editing"] is None
    assert app.session_state["sb_offset"] == 75
    assert not app.exception


def test_new_scenario_starts_from_the_workbook_forecast(app):
    app.selectbox(key="sb_pick").set_value(EXAMPLE_C).run()
    app.selectbox(key="sb_pick").set_value("__new__").run()
    anchor = app.session_state["sb_anchor"]
    assert (anchor["Scenario qty"] == anchor["Workbook qty"]).all() and anchor["Offset"].all()
    assert app.session_state["sb_offset"] == 0 and app.session_state["sb_project"] is None
    assert app.session_state["sb_editing"] is None


def test_renaming_keeps_label_and_linked_notes(app):
    by_label(app.selectbox, "Related scenario (optional)").set_value(EXAMPLE_C)
    by_label(app.text_area, "Observation").input("Covers 70.5% of emissions.")
    app.button(key="FormSubmitter:note_form-Add note").click().run()

    app.selectbox(key="sb_pick").set_value(EXAMPLE_C).run()
    app.text_input(key="sb_name").input("Targeted: top three").run()
    app.button(key="sb_save_changes").click().run()
    renamed = app.session_state["scenarios"][names(app).index("Targeted: top three")]
    assert renamed.illustrative  # only the name changed
    assert EXAMPLE_C not in names(app)
    assert app.session_state["notes"][0]["scenario"] == "Targeted: top three"


def test_compare_tab_opens_a_scenario_for_changing(app):
    app.selectbox(key="cmp_edit").set_value(EXAMPLE_C).run()
    app.button(key="cmp_open").click().run()
    assert app.session_state["sb_editing"] == EXAMPLE_C
    assert app.session_state["nav"] == "Scenario Builder"
    assert not app.exception
