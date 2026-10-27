"""Number formatting shared by the interpretation text and the UI."""

from __future__ import annotations

MINUS = "−"
_EPS = 1e-6


def _is_whole(x: float) -> bool:
    return abs(x - round(x)) < _EPS


def num(x: float) -> str:
    """Thousands separators; whole numbers without decimals, others to 1 dp."""
    text = f"{abs(x):,.0f}" if _is_whole(x) else f"{abs(x):,.1f}"
    return (MINUS + text) if x < 0 and text.strip("0.,") else text


def signed(x: float) -> str:
    if _is_whole(x) and round(x) == 0:
        return "0"
    return ("+" if x > 0 else "") + num(x)


def pct(fraction: float | None, dp: int = 1) -> str:
    if fraction is None:
        return "n/a"
    text = f"{abs(fraction) * 100:.{dp}f}%"
    return (MINUS + text) if fraction < 0 and text.strip("0.%") else text


def signed_pct(fraction: float | None, dp: int = 1) -> str:
    if fraction is None:
        return "n/a"
    text = pct(fraction, dp)
    return ("+" + text) if fraction > 0 and text.strip("0.%") else text


def input_pct(value: float) -> str:
    """An offset percentage as the user entered it (already 0-100)."""
    return f"{value:g}%"


def usd(x: float | None, dp: int = 0) -> str:
    if x is None:
        return "n/a"
    text = f"${abs(x):,.{dp}f}"
    return (MINUS + text) if x < 0 and text.strip("$0.,") else text


def signed_usd(x: float, dp: int = 0) -> str:
    text = usd(x, dp)
    return ("+" + text) if x > 0 and text.strip("$0.,") else text
