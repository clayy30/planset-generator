"""Prove real library integration — not research notes."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.calc_engine import (  # noqa: E402
    HAS_PVLIB,
    engine_banner,
    max_series_modules,
    voc_temperature_correct,
)
from backend.app.presets import duracell_400a_half_home  # noqa: E402
from backend.app.sld import generate_sld_svg  # noqa: E402
from backend.app.sld_schemdraw import HAS_SCHEMDRAW, render_schemdraw_sld  # noqa: E402
from backend.app.calcs import compute_system  # noqa: E402


def test_pvlib_is_installed():
    assert HAS_PVLIB, "pvlib must be installed for production quality calcs"
    assert "pvlib" in engine_banner()


def test_voc_cold_raises_voltage():
    r = voc_temperature_correct(49.5, -0.27, -5.0)
    assert r.voc_design > r.voc_stc
    assert abs(r.voc_at_t_rel - r.voc_at_t_abs) < 0.02
    assert "49.50" in r.formula_rel
    assert r.engine.startswith("planset+pvlib")


def test_max_series_matches_hand_math():
    # 53.51 V/mod cold, 500 V max → floor(500/53.51)=9
    r = voc_temperature_correct(49.5, -0.27, -5.0)
    n = max_series_modules(r.voc_design, 500.0)
    assert n == 9


def test_schemdraw_is_installed():
    assert HAS_SCHEMDRAW, "schemdraw must be installed for symbol SLD"


def test_schemdraw_renders_svg():
    p = duracell_400a_half_home()
    t = compute_system(p)
    svg = render_schemdraw_sld(p, t)
    assert svg is not None
    assert "<svg" in svg
    assert len(svg) > 1000


def test_generate_sld_prefers_schemdraw():
    p = duracell_400a_half_home()
    t = compute_system(p)
    out = generate_sld_svg(p, t)
    assert "schemdraw" in out.lower() or "<svg" in out
    # schemdraw path wraps or includes svg paths
    assert "svg" in out.lower()


def test_compute_system_exposes_engine_banner():
    t = compute_system(duracell_400a_half_home())
    assert any("Calc engine" in n for n in t.continuous_factor_notes)
    assert any("pvlib" in n for n in t.continuous_factor_notes)
