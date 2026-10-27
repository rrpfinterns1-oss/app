"""Illustrative starting scenarios.

One example for each scenario type named in the brief (full, partial, targeted
and portfolio change). They exist so the comparison view has content on first
open; they are editable assumptions, not recommendations. All examples that
use a carbon project use the first project listed in the workbook, so the
offset examples differ only in the offset approach being illustrated.
"""

from __future__ import annotations

from .data import HORIZON, Workbook
from .model import Scenario

EXAMPLE_YEAR = HORIZON[0]
PORTFOLIO_CHANGE_YEAR = 2030


def largest_emitters(wb: Workbook, year: int, n: int) -> list[str]:
    """The n families with the largest workbook-forecast emissions in a year."""
    q = wb.quantities_for(year)
    ranked = sorted(wb.families, key=lambda f: q[f] * wb.annual_tco2e(f), reverse=True)
    return [f for f in ranked[:n] if q[f]]


def illustrative_scenarios(wb: Workbook) -> list[Scenario]:
    y = EXAMPLE_YEAR
    forecast = wb.quantities_for(y)
    everyone = frozenset(wb.families)
    project = wb.projects[0].name
    top3 = largest_emitters(wb, y, 3)
    return [
        Scenario(
            name=f"A · Full offset ({y})",
            year=y,
            quantities=forecast,
            selected=everyone,
            offset_pct=100,
            project=project,
            description=(
                f"Workbook forecast quantities for {y}. All engine families selected; "
                f"100% of selected emissions offset with {project}."
            ),
            illustrative=True,
        ),
        Scenario(
            name=f"B · Partial offset ({y})",
            year=y,
            quantities=forecast,
            selected=everyone,
            offset_pct=50,
            project=project,
            description=(
                f"Workbook forecast quantities for {y}. All engine families selected; "
                f"50% of selected emissions offset with {project}."
            ),
            illustrative=True,
        ),
        Scenario(
            name=f"C · Targeted offset ({y})",
            year=y,
            quantities=forecast,
            selected=frozenset(top3),
            offset_pct=100,
            project=project,
            description=(
                f"Workbook forecast quantities for {y}. Only the three engine families "
                f"with the largest {y} workbook emissions ({', '.join(top3)}) selected; "
                f"100% of selected emissions offset with {project}."
            ),
            illustrative=True,
        ),
        Scenario(
            name=f"D · Portfolio change ({PORTFOLIO_CHANGE_YEAR})",
            year=PORTFOLIO_CHANGE_YEAR,
            quantities=forecast,
            selected=frozenset(),
            offset_pct=0,
            project=None,
            description=(
                f"{PORTFOLIO_CHANGE_YEAR} calculated with the {y} workbook quantities "
                "held constant instead of the forecast quantities. No offset applied."
            ),
            illustrative=True,
        ),
    ]
