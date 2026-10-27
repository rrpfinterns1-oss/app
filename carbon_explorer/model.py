"""Scenario calculations and the factual scenario interpretation.

Every output follows the calculation table in the project brief:

- Baseline portfolio emissions = workbook quantity for the year × annual tCO2e
  per engine, summed across all engine families.
- Scenario portfolio emissions = scenario quantity × annual tCO2e per engine,
  summed across all engine families.
- Emissions change = scenario − baseline (negative = lower modelled emissions).
- Selected emissions = scenario emissions of the families selected for offsetting.
- Tonnes offset = selected emissions × offset percentage.
- Estimated offset cost = tonnes offset × selected project price per tCO2e.
- Commercial indicator = scenario quantity × average profit per engine per year
  (a simplified teaching indicator).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .data import HORIZON, Project, Workbook
from .fmt import input_pct, num, pct, signed, signed_pct, signed_usd, usd


class ScenarioError(ValueError):
    """Raised when scenario assumptions are not valid."""


@dataclass(frozen=True)
class Scenario:
    name: str
    year: int
    quantities: dict[str, int]
    selected: frozenset[str]
    offset_pct: float
    project: str | None = None
    description: str = ""
    illustrative: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "year": self.year,
            "quantities": dict(self.quantities),
            "selected": sorted(self.selected),
            "offset_pct": self.offset_pct,
            "project": self.project,
            "description": self.description,
            "illustrative": self.illustrative,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Scenario":
        try:
            return cls(
                name=str(data["name"]).strip(),
                year=int(data["year"]),
                quantities={str(k): int(v) for k, v in data["quantities"].items()},
                selected=frozenset(str(f) for f in data.get("selected", [])),
                offset_pct=float(data.get("offset_pct", 0)),
                project=data.get("project") or None,
                description=str(data.get("description", "")),
                illustrative=bool(data.get("illustrative", False)),
            )
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise ScenarioError(f"Scenario record is incomplete or malformed: {exc}") from exc


@dataclass(frozen=True)
class FamilyLine:
    family: str
    baseline_qty: int
    scenario_qty: int
    annual_per_engine: float
    profit_per_engine: float
    selected: bool
    baseline_tco2e: float
    scenario_tco2e: float
    offset_tco2e: float

    @property
    def qty_change(self) -> int:
        return self.scenario_qty - self.baseline_qty

    @property
    def tco2e_change(self) -> float:
        return self.scenario_tco2e - self.baseline_tco2e


@dataclass(frozen=True)
class Result:
    scenario: Scenario
    project: Project | None
    lines: tuple[FamilyLine, ...]
    baseline_engines: int
    scenario_engines: int
    baseline_emissions: float
    scenario_emissions: float
    emissions_change: float
    emissions_change_pct: float | None
    selected_emissions: float
    selected_share: float | None
    tonnes_offset: float
    offset_share: float | None
    not_offset: float
    offset_cost: float | None
    commercial_baseline: float
    commercial_scenario: float
    economics_year: str | None = None
    quantity_changes: tuple[tuple[str, int, int], ...] = field(default_factory=tuple)

    @property
    def n_families(self) -> int:
        return len(self.lines)

    @property
    def commercial_change(self) -> float:
        return self.commercial_scenario - self.commercial_baseline

    def table(self) -> pd.DataFrame:
        """Per-family breakdown with the values behind every total."""
        rows = [
            {
                "Engine family": ln.family,
                "Workbook qty": ln.baseline_qty,
                "Scenario qty": ln.scenario_qty,
                "Qty change": ln.qty_change,
                "Annual tCO₂e per engine": ln.annual_per_engine,
                "Baseline tCO₂e": ln.baseline_tco2e,
                "Scenario tCO₂e": ln.scenario_tco2e,
                "Change tCO₂e": ln.tco2e_change,
                "Selected for offset": ln.selected,
                "Offset tCO₂e": ln.offset_tco2e,
                "Offset cost (USD)": (
                    ln.offset_tco2e * self.project.price
                    if self.project is not None
                    else (0.0 if ln.offset_tco2e == 0 else None)
                ),
            }
            for ln in self.lines
        ]
        return pd.DataFrame(rows)


def validate(wb: Workbook, s: Scenario) -> None:
    if not s.name:
        raise ScenarioError("A scenario needs a name.")
    if s.year not in HORIZON:
        raise ScenarioError(f"Year must be between {HORIZON[0]} and {HORIZON[-1]}.")
    unknown = (set(s.quantities) | set(s.selected)) - set(wb.families)
    if unknown:
        raise ScenarioError("Unknown engine families: " + ", ".join(sorted(unknown)))
    missing = set(wb.families) - set(s.quantities)
    if missing:
        raise ScenarioError("Missing scenario quantities for: " + ", ".join(sorted(missing)))
    for family, qty in s.quantities.items():
        if isinstance(qty, bool) or int(qty) != qty or qty < 0:
            raise ScenarioError(f"Quantity for {family} must be a whole number of 0 or more.")
    if not 0 <= s.offset_pct <= 100:
        raise ScenarioError("Offset percentage must be between 0 and 100.")
    if s.project is not None:
        try:
            wb.project(s.project)
        except KeyError as exc:
            raise ScenarioError(str(exc.args[0])) from exc


def _share(part: float, whole: float) -> float | None:
    return part / whole if whole else None


def evaluate(wb: Workbook, s: Scenario) -> Result:
    validate(wb, s)
    baseline_q = wb.quantities_for(s.year)
    project = wb.project(s.project) if s.project else None

    lines = []
    for f in wb.families:
        annual = wb.annual_tco2e(f)
        scen_tco2e = s.quantities[f] * annual
        selected = f in s.selected
        lines.append(
            FamilyLine(
                family=f,
                baseline_qty=baseline_q[f],
                scenario_qty=int(s.quantities[f]),
                annual_per_engine=annual,
                profit_per_engine=wb.profit(f),
                selected=selected,
                baseline_tco2e=baseline_q[f] * annual,
                scenario_tco2e=scen_tco2e,
                # Multiply before dividing to keep whole-tonne results exact.
                offset_tco2e=(scen_tco2e * s.offset_pct / 100) if selected else 0.0,
            )
        )

    baseline = sum(ln.baseline_tco2e for ln in lines)
    scenario = sum(ln.scenario_tco2e for ln in lines)
    selected_em = sum(ln.scenario_tco2e for ln in lines if ln.selected)
    tonnes_offset = selected_em * s.offset_pct / 100
    if project is not None:
        cost: float | None = tonnes_offset * project.price
    else:
        cost = 0.0 if tonnes_offset == 0 else None

    return Result(
        scenario=s,
        project=project,
        lines=tuple(lines),
        baseline_engines=sum(ln.baseline_qty for ln in lines),
        scenario_engines=sum(ln.scenario_qty for ln in lines),
        baseline_emissions=baseline,
        scenario_emissions=scenario,
        emissions_change=scenario - baseline,
        emissions_change_pct=_share(scenario - baseline, baseline),
        selected_emissions=selected_em,
        selected_share=_share(selected_em, scenario),
        tonnes_offset=tonnes_offset,
        offset_share=_share(tonnes_offset, scenario),
        not_offset=scenario - tonnes_offset,
        offset_cost=cost,
        commercial_baseline=sum(ln.baseline_qty * ln.profit_per_engine for ln in lines),
        commercial_scenario=sum(ln.scenario_qty * ln.profit_per_engine for ln in lines),
        economics_year=wb.economics_year,
        quantity_changes=tuple(
            (ln.family, ln.baseline_qty, ln.scenario_qty) for ln in lines if ln.qty_change
        ),
    )


def baseline_emissions_by_year(wb: Workbook) -> pd.DataFrame:
    """Workbook-forecast engines and estimated emissions for each horizon year."""
    annual = wb.emissions["annual"]
    rows = []
    for y in HORIZON:
        q = wb.quantities[y]
        rows.append(
            {"Year": y, "Engines": int(q.sum()), "Estimated tCO₂e": float((q * annual).sum())}
        )
    return pd.DataFrame(rows)


def emissions_table(wb: Workbook, year: int) -> pd.DataFrame:
    """Estimated emissions by engine family for one year of the workbook forecast."""
    q = wb.quantities[year]
    df = pd.DataFrame(
        {
            "Engine family": list(wb.families),
            "Quantity": q.astype(int).to_numpy(),
            "tCO₂e per engine per flight": wb.emissions["per_flight"].to_numpy(),
            "Flights per year": wb.emissions["flights"].to_numpy(),
            "Annual tCO₂e per engine": wb.emissions["annual"].to_numpy(),
        }
    )
    df["Estimated tCO₂e"] = df["Quantity"] * df["Annual tCO₂e per engine"]
    total = df["Estimated tCO₂e"].sum()
    df["Share of total"] = df["Estimated tCO₂e"] / total if total else 0.0
    return df


# ---------------------------------------------------------------------------
# Factual interpretation


def _families_phrase(names: list[str]) -> str:
    if len(names) <= 2:
        return " and ".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def interpret(r: Result) -> list[str]:
    """A neutral, factual summary of a scenario result, one paragraph per topic.

    The text reports what the numbers are; it does not rank, judge or
    recommend. Interpretation and conclusions belong to the presentation.
    """
    s = r.scenario
    paras: list[str] = []

    # Quantities
    if not r.quantity_changes:
        active = sum(1 for ln in r.lines if ln.scenario_qty)
        paras.append(
            f"Scenario quantities match the workbook forecast for {s.year}: "
            f"{r.scenario_engines:,} engines across {active} engine families "
            "with a non-zero quantity."
        )
    else:
        n = len(r.quantity_changes)
        items = "; ".join(
            f"{f} {b:,} → {q:,} ({signed(q - b)})" for f, b, q in r.quantity_changes
        )
        paras.append(
            f"Scenario quantities differ from the workbook forecast for {s.year} in "
            f"{n} engine {'family' if n == 1 else 'families'}: {items}. The total number "
            f"of engines changes from {r.baseline_engines:,} to {r.scenario_engines:,} "
            f"({signed(r.scenario_engines - r.baseline_engines)})."
        )

    # Emissions
    if r.emissions_change == 0:
        paras.append(
            f"Modelled scenario emissions are {num(r.scenario_emissions)} tCO₂e, the same "
            f"as the workbook-forecast baseline of {num(r.baseline_emissions)} tCO₂e "
            "(change: 0 tCO₂e)."
        )
    else:
        direction = "lower" if r.emissions_change < 0 else "higher"
        change_pct = (
            f" ({signed_pct(r.emissions_change_pct)})"
            if r.emissions_change_pct is not None
            else ""
        )
        paras.append(
            f"Modelled scenario emissions are {num(r.scenario_emissions)} tCO₂e, compared "
            f"with a workbook-forecast baseline of {num(r.baseline_emissions)} tCO₂e. The "
            f"change is {signed(r.emissions_change)} tCO₂e{change_pct}, so modelled "
            f"emissions are {direction} than the baseline."
        )

    # Selection and offset
    selected = [ln.family for ln in r.lines if ln.selected]
    if not selected:
        paras.append(
            "No engine families are selected for offsetting, so selected emissions and "
            "tonnes offset are both 0 tCO₂e and the estimated offset cost is $0."
        )
    else:
        if len(selected) == r.n_families:
            who = f"All {r.n_families} engine families are selected for offsetting."
        else:
            who = (
                f"{len(selected)} of {r.n_families} engine families are selected for "
                f"offsetting: {_families_phrase(selected)}."
            )
        share = (
            f", {pct(r.selected_share)} of scenario emissions"
            if r.selected_share is not None
            else ""
        )
        text = f"{who} Their scenario emissions are {num(r.selected_emissions)} tCO₂e{share}."
        zero = [ln.family for ln in r.lines if ln.selected and ln.scenario_qty == 0]
        if zero and len(selected) < r.n_families:
            text += (
                f" {len(zero)} of the selected families "
                f"({_families_phrase(zero)}) {'has' if len(zero) == 1 else 'have'} a "
                "scenario quantity of zero and contribute"
                f"{'s' if len(zero) == 1 else ''} no emissions."
            )
        paras.append(text)

        if s.offset_pct == 0:
            paras.append(
                "The offset percentage is 0%, so no emissions are offset and the "
                "estimated offset cost is $0."
            )
        else:
            text = (
                f"Offsetting {input_pct(s.offset_pct)} of selected emissions covers "
                f"{num(r.tonnes_offset)} tCO₂e"
            )
            if r.offset_share is not None:
                text += f", equal to {pct(r.offset_share)} of scenario emissions"
            text += (
                f"; {num(r.not_offset)} tCO₂e of scenario emissions are not covered "
                "by the offset."
            )
            if r.project is not None:
                text += (
                    f" Using {r.project.name} at the workbook price of "
                    f"{usd(r.project.price, 2)} per tCO₂e, the estimated offset cost is "
                    f"{usd(r.offset_cost)}."
                )
            else:
                text += (
                    " No carbon project is selected, so the estimated offset cost is "
                    "not calculated."
                )
            paras.append(text)

    # Commercial indicator
    basis = (
        f"the workbook's {r.economics_year} economics"
        if r.economics_year
        else "the workbook's economics"
    )
    if r.commercial_change == 0:
        comparison = "the same as for the workbook forecast quantities"
    else:
        comparison = (
            f"compared with {usd(r.commercial_baseline)} for the workbook forecast "
            f"quantities ({signed_usd(r.commercial_change)})"
        )
    paras.append(
        "Simplified commercial indicator (teaching only): scenario quantity × average "
        f"profit per engine per year, using {basis}, gives "
        f"{usd(r.commercial_scenario)}, {comparison}. It is not a profit forecast."
    )

    paras.append(
        "These figures follow directly from the assumptions entered and the workbook's "
        "teaching estimates. They do not indicate a preferred option."
    )
    return paras


# ---------------------------------------------------------------------------
# Side-by-side summaries


ASSUMPTION = "Assumption"
OUTPUT = "Output"


def summary(r: Result) -> list[tuple[str, str, object, str]]:
    """(group, label, raw value, display text) rows describing one scenario."""
    s = r.scenario
    selected = [ln.family for ln in r.lines if ln.selected]
    if not selected:
        selected_text = "None"
    elif len(selected) == r.n_families:
        selected_text = f"All {r.n_families}"
    else:
        selected_text = f"{len(selected)}: " + ", ".join(selected)
    changes = (
        "; ".join(f"{f} {b} → {q}" for f, b, q in r.quantity_changes)
        if r.quantity_changes
        else "None (workbook forecast)"
    )
    project = (
        f"{r.project.name} ({usd(r.project.price, 2)}/tCO₂e)" if r.project else "None selected"
    )
    return [
        (ASSUMPTION, "Year", s.year, str(s.year)),
        (ASSUMPTION, "Quantity changes", changes, changes),
        (ASSUMPTION, "Engines (workbook → scenario)",
         f"{r.baseline_engines} → {r.scenario_engines}",
         f"{r.baseline_engines:,} → {r.scenario_engines:,}"),
        (ASSUMPTION, "Families selected for offset", selected_text, selected_text),
        (ASSUMPTION, "Offset percentage", s.offset_pct, input_pct(s.offset_pct)),
        (ASSUMPTION, "Carbon project", r.project.name if r.project else "", project),
        (OUTPUT, "Baseline emissions (tCO₂e)", r.baseline_emissions, num(r.baseline_emissions)),
        (OUTPUT, "Scenario emissions (tCO₂e)", r.scenario_emissions, num(r.scenario_emissions)),
        (OUTPUT, "Emissions change (tCO₂e)", r.emissions_change, signed(r.emissions_change)),
        (OUTPUT, "Emissions change (%)", r.emissions_change_pct,
         signed_pct(r.emissions_change_pct, 2)),
        (OUTPUT, "Selected emissions (tCO₂e)", r.selected_emissions, num(r.selected_emissions)),
        (OUTPUT, "Selected share of scenario", r.selected_share, pct(r.selected_share)),
        (OUTPUT, "Tonnes offset (tCO₂e)", r.tonnes_offset, num(r.tonnes_offset)),
        (OUTPUT, "Offset share of scenario", r.offset_share, pct(r.offset_share)),
        (OUTPUT, "Emissions not offset (tCO₂e)", r.not_offset, num(r.not_offset)),
        (OUTPUT, "Estimated offset cost (USD)", r.offset_cost,
         usd(r.offset_cost) if r.offset_cost is not None else "Needs a project"),
        (OUTPUT, "Commercial indicator (USD, teaching)", r.commercial_scenario,
         usd(r.commercial_scenario)),
    ]
