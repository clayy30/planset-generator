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
from backend.app.models import BackupMode, InterconnectionMethod  # noqa: E402
from backend.app.presets import duracell_400a_half_home, eg4_gridboss_sample  # noqa: E402
from backend.app.sld import SldRenderError, generate_sld_svg  # noqa: E402
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


def _assert_real_symbols_only(out: str) -> None:
    """The only acceptable SLD output: the schemdraw wrapper div, containing
    real schemdraw-rendered SVG. No hand-drawn box/label fallback exists in
    the codebase any more, but this pins the contract so it can't silently
    come back.
    """
    assert out.startswith('<div class="schemdraw-sld"'), "SLD output must be the schemdraw wrapper, not a fallback diagram"
    assert "<svg" in out


def test_generate_sld_uses_real_symbols_half_home():
    p = duracell_400a_half_home()
    t = compute_system(p)
    _assert_real_symbols_only(generate_sld_svg(p, t))


def test_generate_sld_uses_real_symbols_gridboss():
    p = eg4_gridboss_sample()
    t = compute_system(p)
    _assert_real_symbols_only(generate_sld_svg(p, t))


def test_generate_sld_uses_real_symbols_backfeed():
    p = duracell_400a_half_home()
    p.batteries = []
    p.service.interconnection = InterconnectionMethod.BACKFEED
    p.service.backup_mode = BackupMode.NONE
    p.service.num_disconnects = 1
    t = compute_system(p)
    _assert_real_symbols_only(generate_sld_svg(p, t))


def test_generate_sld_raises_instead_of_falling_back_when_schemdraw_missing(monkeypatch):
    """If schemdraw isn't available, the SLD must fail loudly - never
    silently substitute a hand-drawn box diagram.
    """
    import backend.app.sld_schemdraw as schemdraw_module

    monkeypatch.setattr(schemdraw_module, "HAS_SCHEMDRAW", False)
    p = duracell_400a_half_home()
    t = compute_system(p)
    with pytest.raises(SldRenderError):
        generate_sld_svg(p, t)


def test_generate_sld_raises_instead_of_falling_back_on_empty_render(monkeypatch):
    """If schemdraw runs but produces unusable output, that must also raise,
    not silently fall through to a box diagram.
    """
    import backend.app.sld_schemdraw as schemdraw_module

    monkeypatch.setattr(schemdraw_module, "render_schemdraw_sld", lambda project, totals=None: None)
    p = duracell_400a_half_home()
    t = compute_system(p)
    with pytest.raises(SldRenderError):
        generate_sld_svg(p, t)


def test_compute_system_exposes_engine_banner():
    t = compute_system(duracell_400a_half_home())
    assert any("Calc engine" in n for n in t.continuous_factor_notes)
    assert any("pvlib" in n for n in t.continuous_factor_notes)
