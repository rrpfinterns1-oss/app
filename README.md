# RRPF Carbon Scenario Explorer

A Streamlit app for exploring the RRPF engine portfolio forecast, the emissions it
implies, and carbon-offset scenarios. Every figure comes from
`data/Carbon_Emissions_Workbook_rev.xlsx`. The app reports facts about each
scenario. It does not recommend a strategy; interpretation and conclusions belong
to the presentation.

## Run it

```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Tabs

| Tab | What it does | User stories |
| --- | --- | --- |
| Portfolio | Engine quantities 2026–2035: year selector, totals by year, mix by family, full progression table with trends; bar or line charts | US-01, US-09 |
| Emissions | Estimated tCO₂e by engine family for a chosen year: quantity, annual tCO₂e per engine and portfolio total; bar or line charts | US-02, US-09 |
| Scenario Builder | Pick a saved scenario to change it (or start a new one); edit any quantity, choose families to offset, set the offset % and carbon project; live results, coverage bar and a factual interpretation; save changes, save as new or delete | US-03, US-04, US-05 |
| Compare Scenarios | Saved scenarios side by side (assumptions and outputs), charts, CSV/JSON export and JSON import | US-06 |
| Charts | Pick any data (engine quantities or emissions by year, emissions per engine, profit per engine, project prices, saved scenarios) and show it as a bar chart or line graph; choose families and years | US-09 |
| Source Data | Every workbook table, notes on the workbook, calculation method and boundaries; source values and user assumptions are labelled | US-07 |
| Testing | Hand-calculated test cases (manual calculation, year change, quantity change, targeted selection, zero offset, full offset, commercial indicator) and workbook integrity checks, with a downloadable record | US-08 |
| Findings | Notes written by the team, optionally linked to a scenario, exported as Markdown or CSV | US-10 |

On the Portfolio and Emissions tabs a Bar / Line switch (kept in step across both
tabs) turns the charts into line graphs: totals by year as a line, and each engine
family over time with one chosen family highlighted.

Four illustrative scenarios are preloaded so the comparison has content on first
open: full offset, partial offset (50%), targeted offset (the three families with
the largest 2026 emissions) and a portfolio change (2030 calculated with 2026
quantities). They are editable starting points, not recommendations.

## Calculations

| Output | Calculation |
| --- | --- |
| Baseline portfolio emissions | Workbook quantity for the year × annual tCO₂e per engine, summed over all families |
| Scenario portfolio emissions | Scenario quantity × annual tCO₂e per engine, summed over all families |
| Emissions change | Scenario − baseline (negative means lower modelled emissions) |
| Selected emissions | Scenario emissions of the families selected for offsetting |
| Tonnes offset | Selected emissions × offset percentage |
| Estimated offset cost | Tonnes offset × project price per tCO₂e |
| Commercial indicator | Scenario quantity × average profit per engine per year (simplified teaching indicator) |

Annual tCO₂e per engine is the workbook's tCO₂e per engine per flight × flights per
year. For example, the 2026 baseline is 2,060,410 tCO₂e and the 2030 baseline is
2,169,160 tCO₂e.

## Notes on the workbook

- The `CO2.Credits` row "Select from drop-down" is a placeholder and is not offered as a project.
- The "Project URL" column points to pages that do not match the project names (for
  example Aranya Reforestation → colorado-grasslands). The app uses the "Project Link"
  hyperlinks, which do match.
- SAFc and Accelerate CDR have no country in the workbook.
- Engine economics are the workbook's 2026 values and are applied to every year.

## Tests

```
pip install -r requirements-dev.txt
pytest
```

The suite checks the loader against fixed cell addresses, the calculations against
hand-calculated values, the neutrality of the interpretation text, and runs the app
headlessly to exercise the main flows.

## Updating the data

Replace `data/Carbon_Emissions_Workbook_rev.xlsx` with a revised workbook that keeps
the same sheet names and headings. Tables are found by their header labels, so
added years or projects are picked up automatically. Run `pytest` afterwards; the
hand-calculated test values in `carbon_explorer/checks.py` will need updating if the
2026 or 2030 figures change.

## Layout

```
streamlit_app.py            entry point: page setup, header, tabs
carbon_explorer/data.py     workbook loader
carbon_explorer/model.py    calculations and factual interpretation
carbon_explorer/examples.py illustrative scenarios
carbon_explorer/checks.py   recorded test cases and workbook checks
carbon_explorer/ui/         theme, charts, session state and one module per tab
tests/                      pytest suite
```
