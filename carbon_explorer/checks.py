"""Recorded tests (user story US-08) shared by the Testing tab and pytest.

Model cases compare the app's results with values calculated by hand from the
workbook; the working is recorded next to each expected value. Integrity
checks confirm the workbook's own figures are internally consistent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .data import HORIZON, Workbook
from .fmt import num, usd
from .model import Result, Scenario, evaluate


@dataclass(frozen=True)
class Expectation:
    metric: str  # Result attribute
    label: str
    expected: float
    working: str
    kind: str = "tonnes"  # tonnes | usd | fraction | count

    @property
    def tolerance(self) -> float:
        return {"usd": 0.005, "fraction": 1e-6}.get(self.kind, 1e-6)

    def display(self, value: float | None) -> str:
        if value is None:
            return "n/a"
        if self.kind == "usd":
            return usd(value, 2)
        if self.kind == "fraction":
            return f"{value * 100:+.4f}%".replace("-", "−")
        if self.kind == "count":
            return f"{value:,.0f}"
        return f"{num(value)} tCO₂e"


@dataclass(frozen=True)
class ModelCase:
    id: str
    name: str
    inputs: str
    build: Callable[[Workbook], Scenario]
    expectations: tuple[Expectation, ...]


@dataclass(frozen=True)
class Outcome:
    case_id: str
    case: str
    inputs: str
    metric: str
    working: str
    expected: str
    actual: str
    passed: bool


@dataclass(frozen=True)
class IntegrityCheck:
    id: str
    name: str
    detail: str
    passed: bool


def _scenario(wb: Workbook, name: str, year: int, *, changes=None, selected=(),
              offset=0, project=None) -> Scenario:
    q = wb.quantities_for(year)
    q.update(changes or {})
    return Scenario(name=name, year=year, quantities=q, selected=frozenset(selected),
                    offset_pct=offset, project=project)


FIRST_PROJECT_PRICE = 21.80  # Aranya Reforestation, CO2.Credits row 4

MODEL_CASES: tuple[ModelCase, ...] = (
    ModelCase(
        id="T-01",
        name="Manual calculation",
        inputs="2026 · workbook quantities · no offset",
        build=lambda wb: _scenario(wb, "T-01", 2026),
        expectations=(
            Expectation(
                "baseline_emissions", "Baseline emissions", 2_060_410,
                "2×2,625 + 28×4,900 + 15×6,300 + 21×5,600 + 30×16,500 + 39×7,000 "
                "+ 17×12,060 + 5×9,480 + 56×12,240 (GE90, Trent 500, Trent 800, "
                "V2500 have 0 engines)",
            ),
            Expectation("scenario_emissions", "Scenario emissions", 2_060_410,
                        "Scenario quantities equal the workbook forecast"),
            Expectation("emissions_change", "Emissions change", 0,
                        "2,060,410 − 2,060,410"),
            Expectation("baseline_engines", "Engines", 213,
                        "2+28+15+21+30+39+17+5+56 (matches Sub-Totals G19)", "count"),
        ),
    ),
    ModelCase(
        id="T-02",
        name="Year change",
        inputs="2030 · workbook quantities · no offset",
        build=lambda wb: _scenario(wb, "T-02", 2030),
        expectations=(
            Expectation(
                "baseline_emissions", "Baseline emissions", 2_169_160,
                "38×4,900 + 21×6,300 + 31×5,600 + 30×16,500 + 29×12,060 + 68×12,240 "
                "(all other families have 0 engines in 2030)",
            ),
            Expectation("baseline_engines", "Engines", 217,
                        "38+21+31+30+29+68 (matches Sub-Totals K19)", "count"),
        ),
    ),
    ModelCase(
        id="T-03",
        name="Quantity change",
        inputs="2026 · Trent XWB 56 → 50 · no offset",
        build=lambda wb: _scenario(wb, "T-03", 2026, changes={"Trent XWB": 50}),
        expectations=(
            Expectation("emissions_change", "Emissions change", -73_440,
                        "(50 − 56) × 12,240"),
            Expectation("scenario_emissions", "Scenario emissions", 1_986_970,
                        "2,060,410 − 73,440"),
            Expectation("emissions_change_pct", "Emissions change %", -0.035643,
                        "−73,440 ÷ 2,060,410", "fraction"),
        ),
    ),
    ModelCase(
        id="T-04",
        name="Targeted selection",
        inputs="2026 · only Trent 1000 selected · 50% · Aranya Reforestation",
        build=lambda wb: _scenario(wb, "T-04", 2026, selected=["Trent 1000"], offset=50,
                                   project="Aranya Reforestation"),
        expectations=(
            Expectation("selected_emissions", "Selected emissions", 495_000,
                        "30 × 16,500"),
            Expectation("tonnes_offset", "Tonnes offset", 247_500, "495,000 × 50%"),
            Expectation("offset_cost", "Estimated offset cost", 5_395_500,
                        f"247,500 × ${FIRST_PROJECT_PRICE:.2f}", "usd"),
        ),
    ),
    ModelCase(
        id="T-05",
        name="Zero offset",
        inputs="2026 · all families selected · 0% · Aranya Reforestation",
        build=lambda wb: _scenario(wb, "T-05", 2026, selected=wb.families, offset=0,
                                   project="Aranya Reforestation"),
        expectations=(
            Expectation("selected_emissions", "Selected emissions", 2_060_410,
                        "All families selected, so equal to scenario emissions"),
            Expectation("tonnes_offset", "Tonnes offset", 0, "2,060,410 × 0%"),
            Expectation("offset_cost", "Estimated offset cost", 0, "0 × $21.80", "usd"),
        ),
    ),
    ModelCase(
        id="T-06",
        name="Full offset",
        inputs="2026 · all families selected · 100% · Aranya Reforestation",
        build=lambda wb: _scenario(wb, "T-06", 2026, selected=wb.families, offset=100,
                                   project="Aranya Reforestation"),
        expectations=(
            Expectation("tonnes_offset", "Tonnes offset", 2_060_410, "2,060,410 × 100%"),
            Expectation("not_offset", "Emissions not offset", 0, "2,060,410 − 2,060,410"),
            Expectation("offset_cost", "Estimated offset cost", 44_916_938,
                        f"2,060,410 × ${FIRST_PROJECT_PRICE:.2f}", "usd"),
        ),
    ),
    ModelCase(
        id="T-07",
        name="Commercial indicator",
        inputs="2026 · workbook quantities",
        build=lambda wb: _scenario(wb, "T-07", 2026),
        expectations=(
            Expectation(
                "commercial_baseline", "Commercial indicator", 45_667_538.44,
                "Σ 2026 quantity × Average Profit Per Engine Per Year (Portfolio "
                "column X), e.g. Trent XWB 56 × $370,552.55",
                "usd",
            ),
        ),
    ),
)


def run_model_cases(wb: Workbook) -> list[Outcome]:
    outcomes: list[Outcome] = []
    for case in MODEL_CASES:
        result: Result = evaluate(wb, case.build(wb))
        for e in case.expectations:
            actual = getattr(result, e.metric)
            passed = actual is not None and abs(actual - e.expected) <= e.tolerance
            outcomes.append(
                Outcome(
                    case_id=case.id,
                    case=case.name,
                    inputs=case.inputs,
                    metric=e.label,
                    working=e.working,
                    expected=e.display(e.expected),
                    actual=e.display(actual),
                    passed=passed,
                )
            )
    return outcomes


def integrity_checks(wb: Workbook) -> list[IntegrityCheck]:
    checks: list[IntegrityCheck] = []

    mismatched = [
        y for y, subtotal in wb.quantity_subtotals.items()
        if abs(wb.quantities[y].sum() - subtotal) > 1e-9
    ]
    checks.append(IntegrityCheck(
        "I-01", "Quantity Sub-Totals reconcile",
        f"Sum of the {len(wb.families)} engine families equals the workbook "
        f"'Sub-Totals' row for {len(wb.quantity_subtotals) - len(mismatched)} of "
        f"{len(wb.quantity_subtotals)} years"
        + (f"; differs in {mismatched}" if mismatched else ""),
        bool(wb.quantity_subtotals) and not mismatched,
    ))

    e = wb.emissions
    bad = [f for f in wb.families
           if abs(e.at[f, "per_flight"] * e.at[f, "flights"] - e.at[f, "annual"]) > 1e-9]
    checks.append(IntegrityCheck(
        "I-02", "Annual tCO₂e = tCO₂e per flight × flights per year",
        "Holds for all engine families" if not bad else f"Differs for {', '.join(bad)}",
        not bad,
    ))

    ec = wb.economics
    bad = [f for f in wb.families
           if abs((ec.at[f, "income"] - ec.at[f, "depreciation"] - ec.at[f, "interest"]) * 12
                  - ec.at[f, "profit"]) > 1e-6]
    checks.append(IntegrityCheck(
        "I-03", "Average profit = (income − depreciation − interest) × 12",
        "Holds for all engine families" if not bad else f"Differs for {', '.join(bad)}",
        not bad,
    ))

    horizon = wb.quantities[list(HORIZON)]
    whole = bool(((horizon % 1) == 0).all().all() and (horizon >= 0).all().all())
    checks.append(IntegrityCheck(
        "I-04", f"Quantities {HORIZON[0]}–{HORIZON[-1]} are whole numbers ≥ 0",
        f"{horizon.size} values checked", whole,
    ))

    same = list(wb.emissions.index) == list(wb.economics.index) == list(wb.families)
    checks.append(IntegrityCheck(
        "I-05", "Engine families match across tables",
        f"{len(wb.families)} families in Portfolio quantities, Portfolio economics "
        "and Est.Emissions",
        same,
    ))

    bad = [p.name for p in wb.projects if not p.price > 0 or not p.url]
    checks.append(IntegrityCheck(
        "I-06", "Carbon projects have a positive price and a link",
        f"{len(wb.projects)} projects checked" + (f"; issue with {', '.join(bad)}" if bad else ""),
        not bad,
    ))
    return checks
