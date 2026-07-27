"""Electrical calc regression tests — do not silently break Voc / busbar math."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.calcs import busbar_120_check, cold_voc, compute_system  # noqa: E402
from backend.app.presets import duracell_400a_half_home, eg4_gridboss_sample  # noqa: E402
from backend.app.sld import build_segments  # noqa: E402
from backend.app.sld_ir import build_sld_ir  # noqa: E402


def test_cold_voc_formula():
    # Voc=50, coeff=-0.3%/°C, Tlow=-10 → 50 * (1 + (-0.3/100)*(-10-25))
    # = 50 * (1 + (-0.3/100)*(-35)) = 50 * (1 + 0.105) = 55.25
    v = cold_voc(50.0, -0.3, -10.0)
    assert abs(v - 55.25) < 1e-6


def test_cold_voc_stc_unchanged_at_25c():
    assert abs(cold_voc(49.5, -0.27, 25.0) - 49.5) < 1e-9


def test_busbar_120_pass():
    r = busbar_120_check(busbar_a=200, main_breaker_a=200, backfeed_a=40)
    assert r is not None
    assert r["passes"] is True
    assert r["sum_ocpd"] == 240
    assert r["limit_120pct"] == 240.0


def test_busbar_120_fail():
    r = busbar_120_check(busbar_a=200, main_breaker_a=200, backfeed_a=50)
    assert r is not None
    assert r["passes"] is False


def test_duracell_preset_strings_pass():
    p = duracell_400a_half_home()
    t = compute_system(p)
    assert t.module_count == 24
    assert abs(t.dc_kw - 10.8) < 0.01  # 24 * 450
    assert abs(t.ac_kw_continuous - 15.0) < 0.01
    assert t.string_calcs
    for s in t.string_calcs:
        assert s.voc_ok, f"{s.name} Voc_cold={s.string_voc_cold} limit={s.max_voc_limit}"
        assert s.string_voc_cold > s.string_voc_stc  # cold raises Voc when coeff negative


def test_duracell_segments_exist():
    p = duracell_400a_half_home()
    t = compute_system(p)
    segs = build_segments(p, t)
    tags = {s.tag for s in segs}
    assert "PV1" in tags
    assert "AC-GRID" in tags
    assert "AC-LOAD" in tags
    assert "GND" in tags
    grid = next(s for s in segs if s.tag == "AC-GRID")
    assert "4/0" in grid.conductors or "THWN" in grid.conductors


def test_sld_ir_half_home_topology():
    p = duracell_400a_half_home()
    ir = build_sld_ir(p)
    assert ir.topology == "half_home_dual_disco"
    kinds = {n.kind.value for n in ir.nodes}
    assert "inverter" in kinds
    assert "disco" in kinds
    assert "pv_array" in kinds
    assert ir.island_continuous_a == pytest.approx(62.5)
    assert any(e.id == "PV1" or e.id.startswith("PV") for e in ir.edges)


def test_eg4_preset_runs():
    p = eg4_gridboss_sample()
    t = compute_system(p)
    assert t.module_count == 12
    assert t.dc_kw == pytest.approx(5.4)
    ir = build_sld_ir(p, t)
    assert ir.topology
    assert ir.nodes
