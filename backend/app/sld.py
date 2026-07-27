"""Install-grade single-line diagram generator.

Designed so a field electrician can pull wire, land lugs, and set OCPD
without guessing. Follows common US solar permit / NEC one-line practice:
  • Top → bottom power flow (utility first, array at bottom/side)
  • (E) existing / (N) new equipment tags
  • Amp rating on every OCPD / disco
  • Conductor + raceway callouts on each segment
  • Grounding electrode note
  • RSD initiator location

References (practice, not a PE stamp):
  NEC 110, 250, 690, 705, 706 · common AHJ solar checklist SLD content ·
  IEEE/ANSI one-line symbol conventions simplified for residential hybrid.
"""

from __future__ import annotations

from dataclasses import dataclass

from .calcs import SystemTotals
from .models import ProjectInput


def _awg_for_amps(a: float, al: bool = False) -> str:
    """Conservative 75°C Cu ampacity pick for SLD callouts (field verify)."""
    # NEC 310.16 75°C Cu approx
    table = [
        (20, "12 AWG"),
        (25, "10 AWG"),
        (35, "8 AWG"),
        (50, "6 AWG"),
        (65, "4 AWG"),
        (85, "3 AWG"),
        (100, "2 AWG"),
        (115, "1 AWG"),
        (130, "1/0 AWG"),
        (150, "2/0 AWG"),
        (175, "3/0 AWG"),
        (200, "4/0 AWG"),
        (230, "250 kcmil"),
        (255, "300 kcmil"),
        (285, "350 kcmil"),
        (310, "400 kcmil"),
        (335, "500 kcmil"),
    ]
    for amp, size in table:
        if a <= amp:
            return f"{size} Cu THWN-2"
    return "500 kcmil Cu THWN-2 (verify)"


def _egc_for_ocpd(a: float) -> str:
    # NEC 250.122 simplified
    if a <= 15:
        return "14 AWG Cu"
    if a <= 20:
        return "12 AWG Cu"
    if a <= 60:
        return "10 AWG Cu"
    if a <= 100:
        return "8 AWG Cu"
    if a <= 200:
        return "6 AWG Cu"
    if a <= 300:
        return "4 AWG Cu"
    return "3 AWG Cu"


def _conduit_for_fill(n_cond: int, awg_hint: str) -> str:
    if "4/0" in awg_hint or "kcmil" in awg_hint:
        return '2" EMT'
    if any(x in awg_hint for x in ("1/0", "2/0", "3/0", "1 AWG", "2 AWG")):
        return '1-1/2" EMT'
    if "4 AWG" in awg_hint or "3 AWG" in awg_hint:
        return '1-1/4" EMT'
    if "6 AWG" in awg_hint:
        return '1" EMT'
    return '3/4" EMT'


@dataclass
class Seg:
    tag: str
    from_eq: str
    to_eq: str
    conductors: str
    ocpd: str
    notes: str = ""


def build_segments(project: ProjectInput, totals: SystemTotals) -> list[Seg]:
    """Build the wire/OCPD schedule the SLD and PV-5 share."""
    inv = project.inverters[0] if project.inverters else None
    cont_a = inv.continuous_ac_a * inv.quantity if inv else totals.ac_a_continuous
    inv_ocpd = int(totals.max_backfeed_a or (cont_a * 1.25 + 4) // 5 * 5)
    if inv_ocpd < 15:
        inv_ocpd = 15
    pass_a = inv.passthrough_a if inv and inv.passthrough_a else project.service.disconnect_rating_a
    disco = project.service.disconnect_rating_a
    ac_wire = _awg_for_amps(max(inv_ocpd, cont_a * 1.25))
    feed_wire = _awg_for_amps(disco)
    # Battery DC OCPD class — use integrated hybrid rating; cap reasonable residential
    bat_a = 200
    if inv and inv.battery_cont_w:
        bat_a = min(200, max(100, int(inv.battery_cont_w / 48 * 1.25 / 5) * 5))

    segs: list[Seg] = []

    # PV DC
    isc = max((s.parallel_isc for s in totals.string_calcs), default=15.0)
    dc_ocpd = max(15, int(1.25 * isc + 0.99))
    segs.append(
        Seg(
            "PV1",
            "PV ARRAY / JB",
            f"{inv.model if inv else 'INVERTER'} PV INPUTS",
            f"PV wire #10 Cu TYP · {len(totals.string_calcs) or 1} string(s) · outdoor UV · "
            f"EGC {_egc_for_ocpd(dc_ocpd)}",
            f"String fuse if req · MPPT self-limit · Voc_cold per PV-4",
            "DC only · polarity marked · RSD controlled",
        )
    )

    # Battery
    if project.batteries and any(b.quantity for b in project.batteries):
        segs.append(
            Seg(
                "BAT1",
                "BATTERY BANK",
                f"{inv.model if inv else 'INVERTER'} BAT+/−",
                f"Mfr DC cable kit or sized to {bat_a}A continuous · "
                f"Cu · short as practical · polarity marked",
                f"Integrated battery OCPD / disco (typ. {bat_a}A class)",
                "Torque per mfr · do not reverse polarity",
            )
        )

    ic = project.service.interconnection.value
    backup = project.service.backup_mode.value

    if ic == "backfeed_breaker":
        segs.append(
            Seg(
                "AC1",
                f"{inv.model if inv else 'INVERTER'} AC OUTPUT",
                f"(E) MSP BACKFEED BREAKER {inv_ocpd}A",
                f"(2) {ac_wire} + {_egc_for_ocpd(inv_ocpd)} EGC + N · "
                f"{_conduit_for_fill(4, ac_wire)}",
                f"{inv_ocpd}A 2P backfed breaker · opposite end of bus if 120% rule",
                "Land L1/L2/N/G · label dual power source",
            )
        )
        segs.append(
            Seg(
                "AC0",
                "(E) UTILITY METER",
                f"(E) MSP {project.service.main_breaker_a}A MAIN",
                "Existing service conductors",
                f"{project.service.main_breaker_a}A main",
                "Existing",
            )
        )
    elif backup in ("half_home", "full_dual_disco") or project.service.num_disconnects >= 2:
        segs.append(
            Seg(
                "AC-GRID",
                f"(E) {disco}A DISCO #1 LOAD SIDE",
                f"{inv.model if inv else 'HYBRID'} GRID PORT",
                f"(2) {feed_wire} + {_egc_for_ocpd(disco)} EGC + N · "
                f"{_conduit_for_fill(4, feed_wire)} · 75°C",
                f"{disco}A disco (existing) · hybrid pass-through rating {pass_a}A",
                "Must not exceed inverter grid port rating",
            )
        )
        segs.append(
            Seg(
                "AC-LOAD",
                f"{inv.model if inv else 'HYBRID'} LOAD PORT",
                "BACKED-UP PANEL #1 MAIN",
                f"(2) {feed_wire} + {_egc_for_ocpd(disco)} EGC + N · "
                f"{_conduit_for_fill(4, feed_wire)}",
                f"Panel main ≤ {disco}A · islanded continuous only "
                f"~{cont_a:.0f}A @ 240V",
                "Critical: island capacity ≠ breaker handle rating",
            )
        )
        if project.service.ac_disco_a:
            segs.append(
                Seg(
                    "AC-DISCO",
                    f"{inv.model if inv else 'HYBRID'} AC",
                    f"(N) {project.service.ac_disco_a}A AC DISCONNECT",
                    f"Same as AC-GRID or AC-LOAD per POCO required location",
                    f"{project.service.ac_disco_a}A lockable visible disco",
                    "Utility access · NEMA 3R if outdoor",
                )
            )
    else:
        segs.append(
            Seg(
                "AC1",
                f"{inv.model if inv else 'INVERTER'} AC",
                "POINT OF INTERCONNECTION",
                f"(2) {ac_wire} + {_egc_for_ocpd(inv_ocpd)} EGC + N · "
                f"{_conduit_for_fill(4, ac_wire)}",
                f"{inv_ocpd}A OCPD",
                "Per interconnection method",
            )
        )

    segs.append(
        Seg(
            "GND",
            "INVERTER / RACK / DISCOS",
            "SERVICE GES / GEC",
            f"EGC per 250.122 · GEC per 250.66 · bond rails to EGC",
            "—",
            "Single N-G bond at service only",
        )
    )
    return segs


class SldRenderError(RuntimeError):
    """Raised when a compliant, real-symbol SLD cannot be produced.

    There is no fallback to hand-drawn box diagrams: a plan set with
    non-standard symbols is not an acceptable degraded output, so a
    rendering failure must surface as an error the caller has to handle,
    not a silently substituted lower-quality sheet.
    """


def generate_sld_svg(project: ProjectInput, totals: SystemTotals) -> str:
    """Return full SVG string for PV-3, using real electrical symbols
    (schemdraw: breaker, ground, source, solar, battery) exclusively.

    Raises SldRenderError if a compliant diagram cannot be produced. There
    is intentionally no fallback to hand-drawn box/label diagrams.
    """
    from .sld_schemdraw import HAS_SCHEMDRAW, render_schemdraw_sld

    if not HAS_SCHEMDRAW:
        raise SldRenderError(
            "schemdraw is not installed. It is a required dependency (see requirements.txt) - "
            "plan sets may only use real electrical symbols, never hand-drawn box/label diagrams."
        )

    schem = render_schemdraw_sld(project, totals)
    if not schem or len(schem) < 500:
        raise SldRenderError(
            f"schemdraw SLD rendering produced no usable output for project "
            f"'{getattr(project.meta, 'project_name', '<unknown>')}'."
        )

    # Wrap with a light title so template CSS still applies
    return (
        '<div class="schemdraw-sld" style="width:100%;overflow:auto;background:#fff">'
        + schem
        + "</div>"
    )



def segments_as_wires(project: ProjectInput, totals: SystemTotals) -> list[dict[str, str]]:
    """For PV-5 auto-fill when project.wires empty."""
    return [
        {
            "name": s.tag,
            "from_equip": s.from_eq,
            "to_equip": s.to_eq,
            "conductors": s.conductors,
            "ocpd": s.ocpd,
            "notes": s.notes,
        }
        for s in build_segments(project, totals)
    ]
