"""User-entered numbers for the Charts tab.

The workbook stays the source of truth. These are copies of its inputs that a
user may overwrite to see how the charts respond; they are labelled as
assumptions wherever they are shown and never feed the Scenario Builder.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import pandas as pd

from .data import HORIZON, Workbook

KINDS = ("quantities", "annual", "profit", "prices")


@dataclass(frozen=True)
class Inputs:
    quantities: pd.DataFrame  # index: engine family; columns: HORIZON years
    annual: pd.Series         # annual tCO2e per engine, by engine family
    profit: pd.Series         # average profit per engine per year (USD), by engine family
    prices: pd.Series         # USD per tCO2e, by carbon project


def workbook_inputs(wb: Workbook) -> Inputs:
    return Inputs(
        quantities=wb.quantities[list(HORIZON)].astype(int),
        annual=wb.emissions["annual"].astype(float),
        profit=wb.economics["profit"].astype(float),
        prices=pd.Series({p.name: p.price for p in wb.projects}, dtype=float),
    )


def with_overrides(base: Inputs, overrides: dict) -> Inputs:
    """Replace whole input tables; anything not overridden stays as in the workbook."""
    return replace(base, **{k: v for k, v in overrides.items() if k in KINDS and v is not None})


def changes(base: Inputs, edited: Inputs, kind: str) -> list[tuple[str, float, float]]:
    """(where, workbook value, new value) for every value of `kind` that differs."""
    old, new = getattr(base, kind), getattr(edited, kind)
    found = []
    if isinstance(old, pd.DataFrame):
        for row in old.index:
            for col in old.columns:
                if abs(float(new.at[row, col]) - float(old.at[row, col])) > 1e-9:
                    found.append((f"{row} {col}", float(old.at[row, col]), float(new.at[row, col])))
    else:
        for row in old.index:
            if abs(float(new[row]) - float(old[row])) > 1e-9:
                found.append((str(row), float(old[row]), float(new[row])))
    return found
