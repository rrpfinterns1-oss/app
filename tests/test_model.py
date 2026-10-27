"""Scenario calculations, interpretation wording and the recorded test cases."""

import re

import pytest

from carbon_explorer.checks import MODEL_CASES, integrity_checks, run_model_cases
from carbon_explorer.data import HORIZON, load_workbook
from carbon_explorer.examples import illustrative_scenarios
from carbon_explorer.fmt import num, signed, signed_pct, usd
from carbon_explorer.model import Scenario, ScenarioError, evaluate, interpret, summary


@pytest.fixture(scope="module")
def wb():
    return load_workbook()


def scenario(wb, year=2026, changes=None, selected=(), offset=0, project=None, name="t"):
    q = wb.quantities_for(year)
    q.update(changes or {})
    return Scenario(name=name, year=year, quantities=q, selected=frozenset(selected),
                    offset_pct=offset, project=project)


# --- Recorded cases (US-08) ----------------------------------------------------

@pytest.mark.parametrize("case", MODEL_CASES, ids=lambda c: c.id)
def test_recorded_case(wb, case):
    result = evaluate(wb, case.build(wb))
    for e in case.expectations:
        assert getattr(result, e.metric) == pytest.approx(e.expected, abs=e.tolerance), e.label


def test_all_recorded_outcomes_pass(wb):
    outcomes = run_model_cases(wb)
    assert outcomes and all(o.passed for o in outcomes)


def test_workbook_integrity(wb):
    checks = integrity_checks(wb)
    assert len(checks) == 6
    assert all(c.passed for c in checks), [c for c in checks if not c.passed]


# --- Calculation rules ----------------------------------------------------------

def test_baseline_for_every_year_matches_hand_sum(wb):
    expected = {2026: 2_060_410, 2027: 2_087_340, 2028: 2_122_760, 2029: 2_142_460,
                2030: 2_169_160, 2031: 2_258_860, 2032: 2_348_560, 2033: 2_438_260,
                2034: 2_527_960, 2035: 2_617_660}
    for year in HORIZON:
        assert evaluate(wb, scenario(wb, year)).baseline_emissions == expected[year]


def test_selected_emissions_use_scenario_quantities(wb):
    r = evaluate(wb, scenario(wb, changes={"Trent 1000": 10}, selected=["Trent 1000"],
                              offset=100, project="Bondhu Chula Stoves"))
    assert r.selected_emissions == 10 * 16_500
    assert r.offset_cost == pytest.approx(165_000 * 14.80)


def test_partial_percentage_keeps_fractions(wb):
    r = evaluate(wb, scenario(wb, selected=wb.families, offset=37, project="Accelerate CDR"))
    assert r.tonnes_offset == pytest.approx(2_060_410 * 0.37)
    assert r.offset_cost == pytest.approx(2_060_410 * 0.37 * 34.90)
    assert r.not_offset == pytest.approx(2_060_410 * 0.63)


def test_cost_needs_a_project_only_when_something_is_offset(wb):
    assert evaluate(wb, scenario(wb, selected=wb.families, offset=50)).offset_cost is None
    assert evaluate(wb, scenario(wb, selected=wb.families, offset=0)).offset_cost == 0


def test_shares_are_none_when_scenario_emissions_are_zero(wb):
    zero = {f: 0 for f in wb.families}
    r = evaluate(wb, Scenario("z", 2026, zero, frozenset(wb.families), 100, "Accelerate CDR"))
    assert r.scenario_emissions == 0
    assert r.selected_share is None and r.offset_share is None
    assert r.emissions_change == -2_060_410
    assert r.emissions_change_pct == pytest.approx(-1.0)


def test_commercial_indicator_uses_scenario_quantities(wb):
    r = evaluate(wb, scenario(wb, changes={"Trent 900": 0}))
    # Trent 900 has a negative average profit, so removing its 5 engines raises the total.
    assert r.commercial_change == pytest.approx(5 * 101_544.235324, abs=0.01)


def test_per_family_table_totals_match(wb):
    r = evaluate(wb, scenario(wb, changes={"Trent XWB": 50}, selected=["Trent XWB", "LEAP 1-A"],
                              offset=40, project="Aranya Reforestation"))
    t = r.table()
    assert t["Scenario tCO₂e"].sum() == r.scenario_emissions
    assert t["Baseline tCO₂e"].sum() == r.baseline_emissions
    assert t["Offset tCO₂e"].sum() == pytest.approx(r.tonnes_offset)
    assert t["Offset cost (USD)"].sum() == pytest.approx(r.offset_cost)


@pytest.mark.parametrize("bad", [
    dict(year=2025),
    dict(offset=101),
    dict(offset=-1),
    dict(project="Unknown project"),
    dict(changes={"Trent XWB": -1}),
    dict(selected=["Not an engine"]),
])
def test_invalid_assumptions_are_rejected(wb, bad):
    year = bad.pop("year", 2026)
    if year not in HORIZON:
        s = Scenario("t", year, wb.quantities_for(year), frozenset(), 0)
    else:
        s = scenario(wb, **bad)
    with pytest.raises(ScenarioError):
        evaluate(wb, s)


def test_missing_family_quantity_is_rejected(wb):
    q = wb.quantities_for(2026)
    q.pop("CFM56")
    with pytest.raises(ScenarioError):
        evaluate(wb, Scenario("t", 2026, q, frozenset(), 0))


# --- Interpretation: factual and neutral (US-05) ---------------------------------

BANNED = re.compile(
    r"\b(should|recommend\w*|best|better|worse|optimal|ideal|advis\w*|inefficient|old|"
    r"disposal|dispose|retire\w*|good|bad|attractive|cheapest|favourable|favorable)\b",
    re.IGNORECASE,
)


def all_interpretations(wb):
    examples = [evaluate(wb, s) for s in illustrative_scenarios(wb)]
    extra = [
        evaluate(wb, scenario(wb, changes={"Trent XWB": 50, "LEAP 1-A": 30},
                              selected=["Trent XWB"], offset=25, project="SAFc: Sustainable "
                              "Aviation Fuel Certificates")),
        evaluate(wb, scenario(wb, 2035, selected=["GE90"], offset=60)),
    ]
    return [(r, interpret(r)) for r in examples + extra]


def test_interpretation_uses_neutral_language(wb):
    for _, paras in all_interpretations(wb):
        text = " ".join(paras)
        # The closing disclaimer names "preferred option" in the negative; allow only that.
        text = text.replace("They do not indicate a preferred option.", "")
        assert not BANNED.search(text), BANNED.search(text).group(0)
        assert "prefer" not in text.lower()


def test_interpretation_covers_required_facts(wb):
    s = scenario(wb, changes={"Trent XWB": 50}, selected=["Trent 1000", "Trent 700"],
                 offset=50, project="Aranya Reforestation")
    r = evaluate(wb, s)
    text = " ".join(interpret(r))
    assert "Trent XWB 56 → 50 (−6)" in text                      # quantity change
    assert f"{signed(r.emissions_change)} tCO₂e" in text            # emissions change
    assert signed_pct(r.emissions_change_pct) in text               # and percentage
    assert f"{num(r.selected_emissions)} tCO₂e" in text            # selected emissions
    assert "of scenario emissions" in text                          # selected / offset share
    assert usd(r.offset_cost) in text                               # estimated cost
    assert "do not indicate a preferred option" in text


def test_interpretation_reports_lower_for_negative_change(wb):
    r = evaluate(wb, scenario(wb, changes={"Trent XWB": 50}))
    assert "lower than the baseline" in " ".join(interpret(r))
    r = evaluate(wb, scenario(wb, changes={"Trent XWB": 60}))
    assert "higher than the baseline" in " ".join(interpret(r))


# --- Examples and persistence ---------------------------------------------------------

def test_examples_cover_four_scenario_types(wb):
    examples = illustrative_scenarios(wb)
    assert [s.name[0] for s in examples] == ["A", "B", "C", "D"]
    results = [evaluate(wb, s) for s in examples]
    full, partial, targeted, change = results
    assert full.tonnes_offset == full.scenario_emissions == 2_060_410
    assert partial.tonnes_offset == 1_030_205
    assert targeted.selected_emissions == 685_440 + 495_000 + 273_000
    assert change.scenario_emissions == 2_060_410 and change.baseline_emissions == 2_169_160
    assert all(s.illustrative for s in examples)


def test_scenario_round_trips_through_dict(wb):
    s = scenario(wb, changes={"V2500": 3}, selected=["V2500", "CFM56"], offset=12.5,
                 project="Accelerate CDR", name="Round trip")
    assert Scenario.from_dict(s.to_dict()) == s


def test_from_dict_rejects_malformed_records():
    with pytest.raises(ScenarioError):
        Scenario.from_dict({"name": "x"})


def test_summary_rows_are_consistent(wb):
    rows = summary(evaluate(wb, illustrative_scenarios(wb)[0]))
    labels = [label for _, label, _, _ in rows]
    assert labels[0] == "Year" and "Estimated offset cost (USD)" in labels
    assert dict((label, text) for _, label, _, text in rows)["Estimated offset cost (USD)"] == "$44,916,938"
