from carbon_explorer.data import load_workbook
from carbon_explorer.whatif import changes, with_overrides, workbook_inputs


def test_overrides_and_changes():
    base = workbook_inputs(load_workbook())
    q = base.quantities.copy()
    q.loc["Trent XWB", 2030] = 60
    annual = base.annual.copy()
    annual["GE90"] = 20000
    edited = with_overrides(base, {"quantities": q, "annual": annual})
    assert changes(base, edited, "quantities") == [("Trent XWB 2030", 68.0, 60.0)]
    assert changes(base, edited, "annual") == [("GE90", 23760.0, 20000.0)]
    assert changes(base, edited, "prices") == []
    # The workbook copy is untouched.
    assert base.quantities.loc["Trent XWB", 2030] == 68
    # Emissions follow the edited inputs: 2030 total drops by 8 × 12,240.
    before = (base.quantities[2030] * base.annual).sum()
    after = (edited.quantities[2030] * edited.annual).sum()
    assert before == 2_169_160 and before - after == 8 * 12_240
