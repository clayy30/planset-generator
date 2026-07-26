"""Professional SLD rendering via schemdraw (MIT).

schemdraw provides proper electrical symbols (breaker, ground, source, solar).
We draw an installation-oriented one-line and annotate conductors from the
segment schedule — not a cartoon block diagram.
"""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

from .calcs import SystemTotals, compute_system
from .sld import build_segments

if TYPE_CHECKING:
    from .models import ProjectInput

try:
    import schemdraw
    import schemdraw.elements as elm

    HAS_SCHEMDRAW = True
except Exception:  # pragma: no cover
    schemdraw = None  # type: ignore
    elm = None  # type: ignore
    HAS_SCHEMDRAW = False


def _short(s: str, n: int = 28) -> str:
    s = s.replace("Duracell Power Center", "DPC").replace("Max Hybrid", "MH")
    return s if len(s) <= n else s[: n - 1] + "…"


def render_schemdraw_sld(project: "ProjectInput", totals: SystemTotals | None = None) -> str | None:
    """Return SVG string, or None if schemdraw unavailable / topology unsupported."""
    if not HAS_SCHEMDRAW:
        return None

    totals = totals or compute_system(project)
    segs = build_segments(project, totals)
    inv = project.inverters[0] if project.inverters else None
    cont_a = (inv.continuous_ac_a * inv.quantity) if inv else totals.ac_a_continuous
    disco = project.service.disconnect_rating_a
    pass_a = inv.passthrough_a if inv and inv.passthrough_a else disco
    inv_label = _short(f"{inv.manufacturer} {inv.model}" if inv else "HYBRID", 32)
    backup = project.service.backup_mode.value
    ic = project.service.interconnection.value

    # Prefer hybrid dual-disco / half-home path (most of our residential work)
    use_half = (
        backup in ("half_home", "full_dual_disco", "critical_loads")
        or project.service.num_disconnects >= 2
        or ic == "dual_disco_hybrid"
    )
    if not use_half and ic != "backfeed_breaker":
        use_half = True  # default residential hybrid presentation

    try:
        if ic == "backfeed_breaker" and backup not in (
            "half_home",
            "full_dual_disco",
            "critical_loads",
        ):
            svg = _draw_backfeed(project, totals, segs, inv_label, cont_a)
        else:
            svg = _draw_half_home(
                project, totals, segs, inv_label, cont_a, disco, pass_a, backup
            )
        return svg
    except Exception:
        return None


def _drawing():
    # inches-ish unit; black/white professional
    d = schemdraw.Drawing(show=False)
    d.config(unit=2.2, fontsize=9, lw=1.5, font="sans-serif")
    return d


def _to_svg(d) -> str:
    data = d.get_imagedata("svg")
    if isinstance(data, bytes):
        return data.decode("utf-8")
    return str(data)


def _draw_half_home(project, totals, segs, inv_label, cont_a, disco, pass_a, backup) -> str:
    d = _drawing()
    load_name = "CRITICAL PANEL" if backup == "critical_loads" else "BU PANEL #1"

    # Title annotation
    d += elm.Label().at((0, 5.2)).label(
        f"SINGLE-LINE DIAGRAM  ·  {project.service.voltage}  ·  schemdraw symbols  ·  NTS",
        loc="right",
        fontsize=11,
        font="sans-serif",
        halign="left",
    )
    d += elm.Label().at((0, 4.85)).label(
        "Power flow left→right on AC backbone  ·  (E)=existing  ·  (N)=new  ·  verify torque/ampacity in field",
        loc="right",
        fontsize=8,
        color="gray",
        halign="left",
    )

    # --- AC backbone ---
    d += elm.Dot().at((0, 3.2)).label("(E) UTILITY\n" + project.service.voltage, loc="left", fontsize=8)
    d += elm.SourceSin().right().label("GRID", loc="top", fontsize=8)
    d += elm.Line().right().length(0.8)
    d += elm.Breaker().label(f"(E) METER\nSERVICE", loc="top", fontsize=8)
    d += elm.Line().right().length(0.6)
    # Split: use a vertical tee via Dot
    d += elm.Dot()
    split = d.here

    # Upper: Disco #1 → Hybrid path
    d += elm.Line().up().at(split).length(1.0)
    d += elm.Breaker().right().label(f"(E) {disco}A\nDISCO #1", loc="top", fontsize=8)
    d += elm.Line().right().length(0.5)
    d += elm.Breaker().label(f"(N) HYBRID\n{inv_label}\npass {pass_a:.0f}A", loc="top", fontsize=7)
    inv_here = d.here
    d += elm.Line().right().length(0.5)
    d += elm.Breaker().label(f"(N) {load_name}\nisland ~{cont_a:.0f}A", loc="top", fontsize=7)
    d += elm.Line().right().length(0.4)
    d += elm.Dot().label("LOADS", loc="right", fontsize=8)

    # Lower: Disco #2 utility only
    d += elm.Line().down().at(split).length(1.0)
    d += elm.Breaker().right().label(f"(E) {disco}A\nDISCO #2", loc="bot", fontsize=8)
    d += elm.Line().right().length(1.2)
    d += elm.Dot().label("(E) PANEL #2\n(no backup)", loc="right", fontsize=8)

    # PV into hybrid (from above inverter)
    d += elm.Line().up().at(inv_here).length(0.9)
    d += elm.Solar().left().label("(N) PV ARRAY\n" + f"{totals.dc_kw:.2f} kWDC", loc="top", fontsize=7)
    d += elm.Line().left().length(0.3)
    d += elm.Dot().label(f"{totals.module_count} mod", loc="left", fontsize=7)

    # Battery into hybrid (from below inverter area)
    d += elm.Line().down().at(inv_here).length(0.9)
    if totals.battery_kwh > 0:
        d += elm.Battery().left().label(f"(N) BATTERY\n{totals.battery_kwh:.0f} kWh", loc="bot", fontsize=7)
    else:
        d += elm.Line().left().length(1.0).label("(no battery)", loc="bot", fontsize=7)

    # Ground at service
    d += elm.Ground().at(split).down().label("GEC/EGC\nNEC 250", loc="bot", fontsize=7)

    # Wire schedule block (text annotations bottom)
    y = -1.2
    d += elm.Label().at((0, y)).label("CONDUCTOR / OCPD (design basis — EC confirms):", loc="right", fontsize=8, halign="left", font="sans-serif")
    y -= 0.35
    for seg in segs[:5]:
        line = f"{seg.tag}: {seg.conductors[:70]}  |  OCPD: {seg.ocpd[:40]}"
        d += elm.Label().at((0, y)).label(line, loc="right", fontsize=6.5, color="#222", halign="left", font="sans-serif")
        y -= 0.28

    y -= 0.15
    d += elm.Label().at((0, y)).label(
        f"⚠ Island continuous ≈ {cont_a:.0f} A @ 240 V ({totals.ac_kw_continuous:.1f} kW) — NOT full {disco} A disco handle in blackout.",
        loc="right",
        fontsize=7.5,
        color="#8b0000",
        halign="left",
        font="sans-serif",
    )
    y -= 0.3
    d += elm.Label().at((0, y)).label(
        "Symbols: schemdraw (MIT) · Math: planset + pvlib · Install: LOTO → GRID on Disco#1 only → LOAD → PV → BAT → labels → commission",
        loc="right",
        fontsize=6.5,
        color="#444",
        halign="left",
        font="sans-serif",
    )

    return _to_svg(d)


def _draw_backfeed(project, totals, segs, inv_label, cont_a) -> str:
    d = _drawing()
    inv_ocpd = int(totals.max_backfeed_a or max(15, cont_a * 1.25))
    main = project.service.main_breaker_a
    bus = project.service.busbar_a or main

    d += elm.Label().at((0, 3.5)).label(
        f"SINGLE-LINE · BACKFED BREAKER · {project.service.voltage} · schemdraw · NTS",
        loc="right",
        fontsize=11,
        halign="left",
    )

    d += elm.Dot().at((0, 2)).label("(E) UTILITY", loc="left", fontsize=8)
    d += elm.SourceSin().right()
    d += elm.Line().right().length(0.6)
    d += elm.Breaker().label("(E) METER", loc="top", fontsize=8)
    d += elm.Line().right().length(0.5)
    d += elm.Breaker().label(f"(E) MSP\nMain {main}A Bus {bus}A", loc="top", fontsize=7)
    d += elm.Line().right().length(0.4)
    d += elm.Breaker().label(f"(N) BACKFEED\n{inv_ocpd}A 2P", loc="top", fontsize=8)
    d += elm.Line().right().length(0.5)
    d += elm.Breaker().label(f"(N) {inv_label}\n{cont_a:.0f}A cont", loc="top", fontsize=7)
    inv = d.here
    d += elm.Line().right().length(0.3)
    d += elm.Dot()

    d += elm.Line().up().at(inv).length(0.8)
    d += elm.Solar().left().label(f"PV {totals.dc_kw:.2f} kW", loc="top", fontsize=7)
    if totals.battery_kwh > 0:
        d += elm.Line().down().at(inv).length(0.8)
        d += elm.Battery().left().label(f"BAT {totals.battery_kwh:.0f} kWh", loc="bot", fontsize=7)

    d += elm.Ground().at(inv).down().label("GEC", fontsize=7)

    y = 0.3
    d += elm.Label().at((0, y)).label(
        f"120% bus: Main {main}A + BF {inv_ocpd}A ≤ 1.20×{bus}A — see PV-4",
        loc="right",
        fontsize=8,
        color="#8b0000",
        halign="left",
    )
    y -= 0.35
    for seg in segs[:4]:
        d += elm.Label().at((0, y)).label(
            f"{seg.tag}: {seg.conductors[:65]}",
            loc="right",
            fontsize=6.5,
            halign="left",
        )
        y -= 0.28

    return _to_svg(d)
