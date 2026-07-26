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
from typing import Any

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


def generate_sld_svg(project: ProjectInput, totals: SystemTotals) -> str:
    """Return full SVG string for PV-3 (clean layout, no overlaps)."""
    from .sld_diagrams import sld_backfeed_svg, sld_half_home_svg

    segs = build_segments(project, totals)
    inv = project.inverters[0] if project.inverters else None
    mod = project.modules[0] if project.modules else None
    backup = project.service.backup_mode.value
    ic = project.service.interconnection.value
    critical = backup == "critical_loads"
    cont_a = (inv.continuous_ac_a * inv.quantity) if inv else totals.ac_a_continuous
    inv_ocpd = int(totals.max_backfeed_a or max(15, (cont_a * 1.25 + 4) // 5 * 5))
    disco = project.service.disconnect_rating_a
    pass_a = float(inv.passthrough_a) if inv and inv.passthrough_a else float(disco)

    inv_name = f"{inv.manufacturer} {inv.model}" if inv else "HYBRID INVERTER"
    mod_line = (
        f"{mod.quantity} × {mod.model} ({mod.pmax_w:.0f}W) = {totals.dc_kw:.2f} kWDC"
        if mod
        else f"{totals.dc_kw:.2f} kWDC"
    )
    n_str = len(totals.string_calcs) or 1
    voc_note = ""
    if totals.string_calcs:
        s0 = totals.string_calcs[0]
        voc_note = f"Voc_cold {s0.string_voc_cold:.0f}V · Isc {s0.parallel_isc:.1f}A"

    # Schedule rows — start Y depends on diagram (half-home uses 500+)
    is_backfeed = ic == "backfeed_breaker" and backup not in (
        "half_home",
        "full_dual_disco",
    )
    table_y = 390 if is_backfeed else 500
    row_h = 28
    seg_lines: list[str] = []
    for i, s in enumerate(segs[:5]):
        y = table_y + 18 + i * row_h
        fr = (s.from_eq[:34] + "…") if len(s.from_eq) > 34 else s.from_eq
        to = (s.to_eq[:34] + "…") if len(s.to_eq) > 34 else s.to_eq
        cond = (s.conductors[:70] + "…") if len(s.conductors) > 70 else s.conductors
        ocpd = (s.ocpd[:50] + "…") if len(s.ocpd) > 50 else s.ocpd
        seg_lines.append(
            f'<text x="16" y="{y}" font-size="8" font-weight="700" '
            f'font-family="IBM Plex Mono,Consolas,monospace">{s.tag}</text>'
            f'<text x="52" y="{y}" font-size="7.5" font-family="Segoe UI,Arial">'
            f"{fr}  →  {to}</text>"
            f'<text x="52" y="{y + 11}" font-size="7" fill="#333" '
            f'font-family="IBM Plex Mono,Consolas,monospace">{cond}</text>'
            f'<text x="52" y="{y + 21}" font-size="7" fill="#555" '
            f'font-family="Segoe UI,Arial">OCPD: {ocpd}</text>'
        )

    feed = _awg_for_amps(disco if not is_backfeed else inv_ocpd)
    egc = _egc_for_ocpd(disco if not is_backfeed else inv_ocpd)
    conduit = _conduit_for_fill(4, feed)
    load_title = "CRITICAL LOADS PANEL" if critical else "BACKED-UP LOAD CENTER #1"

    if is_backfeed:
        return sld_backfeed_svg(
            voltage=project.service.voltage,
            main_a=project.service.main_breaker_a,
            bus_a=project.service.busbar_a or project.service.main_breaker_a,
            inv_ocpd=inv_ocpd,
            cont_a=cont_a,
            inv_name=inv_name,
            mod_line=mod_line,
            bat_kwh=totals.battery_kwh,
            feed=feed,
            egc=egc,
            conduit=conduit,
            seg_lines=seg_lines,
        )

    return sld_half_home_svg(
        voltage=project.service.voltage,
        phase=project.service.phase,
        service_a=project.service.service_a,
        main_a=project.service.main_breaker_a,
        bus_a=project.service.busbar_a,
        disco=disco,
        pass_a=pass_a,
        cont_a=cont_a,
        ac_kw=totals.ac_kw_continuous,
        inv_name=inv_name,
        inv_ne_ma=inv.ne_ma if inv else "NEMA 3R",
        inv_qty=inv.quantity if inv else 1,
        load_title=load_title,
        mod_line=mod_line,
        n_str=n_str,
        voc_note=voc_note,
        bat_kwh=totals.battery_kwh,
        ac_disco_a=project.service.ac_disco_a,
        feed=feed,
        egc=egc,
        conduit=conduit,
        seg_lines=seg_lines,
    )


def _breaker(x: float, y: float, amps: str, label: str = "") -> str:
    """Small 2-pole breaker symbol with amp callout."""
    return f'''
    <rect x="{x}" y="{y}" width="36" height="22" fill="#fff" stroke="#111" stroke-width="1.5"/>
    <line x1="{x+8}" y1="{y+6}" x2="{x+28}" y2="{y+6}" stroke="#111" stroke-width="1.5"/>
    <line x1="{x+8}" y1="{y+16}" x2="{x+28}" y2="{y+16}" stroke="#111" stroke-width="1.5"/>
    <circle cx="{x+8}" cy="{y+6}" r="2" fill="#111"/>
    <circle cx="{x+8}" cy="{y+16}" r="2" fill="#111"/>
    <text x="{x+18}" y="{y+38}" text-anchor="middle" font-size="9" font-weight="700" font-family="Segoe UI,Arial">{amps}</text>
    <text x="{x+18}" y="{y+48}" text-anchor="middle" font-size="7" fill="#444" font-family="Segoe UI,Arial">{label}</text>
    '''


def _disco_sym(x: float, y: float, amps: str, title: str) -> str:
    return f'''
    <rect x="{x}" y="{y}" width="120" height="44" fill="#fff" stroke="#111" stroke-width="2"/>
    <line x1="{x+15}" y1="{y+22}" x2="{x+45}" y2="{y+22}" stroke="#111" stroke-width="2"/>
    <line x1="{x+45}" y1="{y+22}" x2="{x+60}" y2="{y+10}" stroke="#111" stroke-width="2"/>
    <circle cx="{x+62}" cy="{y+10}" r="3" fill="#111"/>
    <text x="{x+60}" y="{y+18}" font-size="9" font-weight="700" font-family="Segoe UI,Arial">{amps}</text>
    <text x="{x+60}" y="{y+32}" font-size="8" font-family="Segoe UI,Arial">{title}</text>
    '''


def _wire_note(x: float, y: float, text: str, w: float = 160) -> str:
    lines = []
    # wrap rough
    words = text.split(" · ")
    row = ""
    rows = []
    for wpart in words:
        trial = (row + " · " + wpart).strip(" ·")
        if len(trial) > 42 and row:
            rows.append(row)
            row = wpart
        else:
            row = trial
    if row:
        rows.append(row)
    h = 12 + len(rows) * 10
    lines.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#ffffcc" stroke="#888" stroke-width="0.8"/>'
    )
    for i, r in enumerate(rows[:4]):
        lines.append(
            f'<text x="{x+4}" y="{y+11+i*10}" font-size="7.5" font-family="IBM Plex Mono,Consolas,monospace">{r}</text>'
        )
    return "\n".join(lines)


def _sld_half_home(
    project, totals, inv_name, mod_line, n_str, voc_note, cont_a, inv_ocpd, disco, pass_a, critical, seg_lines, segs,
) -> str:
    feed = _awg_for_amps(disco)
    ac_w = _awg_for_amps(max(inv_ocpd, cont_a * 1.25))
    egc = _egc_for_ocpd(disco)
    conduit = _conduit_for_fill(4, feed)
    inv = project.inverters[0] if project.inverters else None
    inv_ne_ma = inv.ne_ma if inv else "NEMA 3R"
    inv_qty = inv.quantity if inv else 1

    load_title = "CRITICAL LOADS PANEL" if critical else "BACKED-UP LOAD CENTER #1"
    bat_kwh = totals.battery_kwh

    return f'''<svg class="sld" viewBox="0 0 1180 720" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="#111"/>
    </marker>
  </defs>
  <text x="16" y="16" font-size="11" font-weight="700" font-family="Segoe UI,Arial">ELECTRICAL SINGLE-LINE DIAGRAM — INSTALLATION GRADE · SCALE: NTS · 120/240V 1Ø 3W</text>
  <text x="16" y="30" font-size="9" fill="#333" font-family="Segoe UI,Arial">Power flow TOP → BOTTOM. Single line = L1/L2/N/G (4-wire) unless noted. (E)=existing (N)=new. Field-verify all ampacity, torque, and AHJ/POCO requirements.</text>

  <!-- ===== UTILITY COLUMN CENTER ===== -->
  <circle cx="400" cy="55" r="16" fill="none" stroke="#111" stroke-width="2"/>
  <text x="400" y="59" text-anchor="middle" font-size="14" font-weight="700">~</text>
  <text x="425" y="52" font-size="11" font-weight="700" font-family="Segoe UI,Arial">(E) UTILITY</text>
  <text x="425" y="64" font-size="9" fill="#444" font-family="Segoe UI,Arial">{project.service.voltage} · {project.service.phase}</text>

  <line x1="400" y1="71" x2="400" y2="95" stroke="#111" stroke-width="2.5"/>
  <rect x="330" y="95" width="140" height="36" fill="#fff" stroke="#111" stroke-width="2"/>
  <text x="400" y="112" text-anchor="middle" font-size="10" font-weight="700" font-family="Segoe UI,Arial">(E) UTILITY METER</text>
  <text x="400" y="124" text-anchor="middle" font-size="8" fill="#444" font-family="Segoe UI,Arial">kWh · form per POCO</text>

  <line x1="400" y1="131" x2="400" y2="155" stroke="#111" stroke-width="2.5"/>
  <rect x="310" y="155" width="180" height="40" fill="#fff" stroke="#111" stroke-width="2"/>
  <text x="400" y="172" text-anchor="middle" font-size="10" font-weight="700" font-family="Segoe UI,Arial">(E) {project.service.service_a}A SERVICE EQUIP.</text>
  <text x="400" y="186" text-anchor="middle" font-size="8" fill="#444" font-family="Segoe UI,Arial">Main {project.service.main_breaker_a}A{" · Bus "+str(project.service.busbar_a)+"A" if project.service.busbar_a else ""}</text>

  <!-- split to discos -->
  <line x1="400" y1="195" x2="400" y2="215" stroke="#111" stroke-width="2.5"/>
  <line x1="180" y1="215" x2="700" y2="215" stroke="#111" stroke-width="2.5"/>
  <line x1="180" y1="215" x2="180" y2="235" stroke="#111" stroke-width="2.5"/>
  <line x1="700" y1="215" x2="700" y2="235" stroke="#111" stroke-width="2.5"/>

  <!-- DISCO 1 -->
  <rect x="110" y="235" width="140" height="50" fill="#e8f5ee" stroke="#0b5c2e" stroke-width="2.2"/>
  <text x="180" y="254" text-anchor="middle" font-size="10" font-weight="700" fill="#0b5c2e" font-family="Segoe UI,Arial">(E) {disco}A DISCO #1</text>
  <text x="180" y="268" text-anchor="middle" font-size="8" font-family="Segoe UI,Arial">LOCKABLE · VISIBLE</text>
  <text x="180" y="280" text-anchor="middle" font-size="8" fill="#444" font-family="Segoe UI,Arial">FEEDER TO HYBRID</text>

  <!-- DISCO 2 non-bu -->
  <rect x="630" y="235" width="140" height="50" fill="#fff" stroke="#111" stroke-width="2"/>
  <text x="700" y="254" text-anchor="middle" font-size="10" font-weight="700" font-family="Segoe UI,Arial">(E) {disco}A DISCO #2</text>
  <text x="700" y="268" text-anchor="middle" font-size="8" fill="#444" font-family="Segoe UI,Arial">UTILITY ONLY</text>
  <text x="700" y="280" text-anchor="middle" font-size="8" fill="#666" font-family="Segoe UI,Arial">NO HYBRID · NO BACKUP</text>

  <!-- wire note grid feed -->
  {_wire_note(200, 250, f"SEG AC-GRID: (2) {feed} + {egc} EGC + N · {conduit} · 75°C · TORQUE PER LUG", 200)}

  {f'''
  <line x1="180" y1="285" x2="180" y2="300" stroke="#0b5c2e" stroke-width="2.5"/>
  <rect x="120" y="300" width="120" height="28" fill="#fff" stroke="#c00" stroke-width="1.5"/>
  <text x="180" y="318" text-anchor="middle" font-size="8" font-weight="700" fill="#c00" font-family="Segoe UI,Arial">(N) {project.service.ac_disco_a}A AC DISCO</text>
  <line x1="180" y1="328" x2="180" y2="348" stroke="#0b5c2e" stroke-width="2.5"/>
  ''' if project.service.ac_disco_a else '<line x1="180" y1="285" x2="180" y2="348" stroke="#0b5c2e" stroke-width="2.5"/>'}

  <!-- HYBRID INVERTER big box -->
  <rect x="70" y="348" width="280" height="110" fill="#fff" stroke="#0b5c2e" stroke-width="2.8"/>
  <text x="210" y="368" text-anchor="middle" font-size="12" font-weight="700" fill="#0b5c2e" font-family="Segoe UI,Arial">(N) {inv_name}</text>
  <text x="210" y="384" text-anchor="middle" font-size="9" font-family="Segoe UI,Arial">UL 1741 hybrid · {inv_ne_ma} · qty {inv_qty}</text>
  <text x="85" y="404" font-size="9" font-family="Segoe UI,Arial">PORTS:</text>
  <text x="85" y="418" font-size="8.5" font-family="Segoe UI,Arial">• GRID IN ← Disco #1 ({pass_a}A pass-through max)</text>
  <text x="85" y="432" font-size="8.5" font-family="Segoe UI,Arial">• LOAD OUT → {load_title}</text>
  <text x="85" y="446" font-size="8.5" font-family="Segoe UI,Arial">• PV IN ({n_str} MPPT/strings) · BAT+/−</text>
  <text x="210" y="450" text-anchor="middle" font-size="8" fill="#666" font-family="Segoe UI,Arial">Island continuous ≈ {cont_a:.1f}A @ 240V ({totals.ac_kw_continuous:.1f} kW) — NOT {disco}A</text>

  <!-- PV branch left -->
  <line x1="70" y1="400" x2="20" y2="400" stroke="#b8860b" stroke-width="2.2"/>
  <line x1="20" y1="400" x2="20" y2="480" stroke="#b8860b" stroke-width="2.2"/>
  <rect x="5" y="480" width="130" height="55" fill="#fff8e6" stroke="#b8860b" stroke-width="2"/>
  <text x="70" y="498" text-anchor="middle" font-size="9" font-weight="700" fill="#6b5200" font-family="Segoe UI,Arial">(N) PV ARRAY</text>
  <text x="70" y="512" text-anchor="middle" font-size="7.5" font-family="Segoe UI,Arial">{mod_line[:40]}</text>
  <text x="70" y="524" text-anchor="middle" font-size="7" fill="#444" font-family="Segoe UI,Arial">{voc_note or "See PV-4"}</text>
  {_wire_note(5, 420, f"SEG PV1: #10 PV wire · {n_str} str · UV · EGC · RSD", 130)}

  <!-- BAT branch -->
  <line x1="350" y1="400" x2="420" y2="400" stroke="#c45c00" stroke-width="2.2"/>
  <rect x="420" y="375" width="120" height="50" fill="#fff5eb" stroke="#c45c00" stroke-width="2"/>
  <text x="480" y="395" text-anchor="middle" font-size="9" font-weight="700" fill="#c45c00" font-family="Segoe UI,Arial">(N) BATTERY</text>
  <text x="480" y="410" text-anchor="middle" font-size="8" font-family="Segoe UI,Arial">{bat_kwh:.0f} kWh usable</text>
  <text x="480" y="420" text-anchor="middle" font-size="7" fill="#444" font-family="Segoe UI,Arial">Int. 200A-class disco</text>

  <!-- LOAD out -->
  <line x1="180" y1="458" x2="180" y2="500" stroke="#0b5c2e" stroke-width="2.5"/>
  {_wire_note(200, 470, f"SEG AC-LOAD: (2) {feed} + {egc} EGC + N · {conduit}", 190)}
  <rect x="100" y="500" width="160" height="42" fill="#0b5c2e"/>
  <text x="180" y="518" text-anchor="middle" font-size="10" font-weight="700" fill="#fff" font-family="Segoe UI,Arial">(N) {load_title}</text>
  <text x="180" y="532" text-anchor="middle" font-size="8" fill="#d4f0e2" font-family="Segoe UI,Arial">Main ≤{disco}A · island ~{cont_a:.0f}A cont.</text>

  <!-- Panel 2 -->
  <line x1="700" y1="285" x2="700" y2="360" stroke="#111" stroke-width="2.5"/>
  <rect x="630" y="360" width="140" height="50" fill="#fff" stroke="#111" stroke-width="2"/>
  <text x="700" y="382" text-anchor="middle" font-size="10" font-weight="700" font-family="Segoe UI,Arial">(E) PANEL / LOADS #2</text>
  <text x="700" y="398" text-anchor="middle" font-size="8" fill="#666" font-family="Segoe UI,Arial">DARK IN OUTAGE</text>

  <!-- RSD -->
  <rect x="560" y="300" width="150" height="48" fill="#8b0000"/>
  <text x="635" y="320" text-anchor="middle" font-size="9" font-weight="700" fill="#fff" font-family="Segoe UI,Arial">RSD INITIATOR</text>
  <text x="635" y="334" text-anchor="middle" font-size="8" fill="#fcc" font-family="Segoe UI,Arial">NEC 690.12 · OUTDOOR</text>
  <text x="635" y="346" text-anchor="middle" font-size="7" fill="#fcc" font-family="Segoe UI,Arial">AT SERVICE ACCESS</text>
  <line x1="560" y1="324" x2="350" y2="360" stroke="#8b0000" stroke-width="1.2" stroke-dasharray="3 2"/>

  <!-- Ground -->
  <line x1="400" y1="195" x2="480" y2="195" stroke="#111" stroke-width="1.2"/>
  <line x1="480" y1="195" x2="480" y2="210" stroke="#111" stroke-width="1.2"/>
  <line x1="470" y1="210" x2="490" y2="210" stroke="#111" stroke-width="1.5"/>
  <line x1="473" y1="215" x2="487" y2="215" stroke="#111" stroke-width="1.5"/>
  <line x1="476" y1="220" x2="484" y2="220" stroke="#111" stroke-width="1.5"/>
  <text x="495" y="214" font-size="8" font-family="Segoe UI,Arial">GEC/EGC</text>
  <text x="495" y="224" font-size="7" fill="#444" font-family="Segoe UI,Arial">NEC 250 · N-G at service only</text>

  <!-- INSTALL NOTES box -->
  <rect x="780" y="50" width="380" height="200" fill="#f7f7f7" stroke="#111" stroke-width="1.5"/>
  <text x="790" y="68" font-size="10" font-weight="700" font-family="Segoe UI,Arial">ELECTRICIAN — SEQUENCE / RULES</text>
  <text x="790" y="86" font-size="8.5" font-family="Segoe UI,Arial">1. Kill Disco #1 &amp; #2. Verify zero energy. Lockout/tagout.</text>
  <text x="790" y="100" font-size="8.5" font-family="Segoe UI,Arial">2. Land GRID port on load side of Disco #1 only — never combine</text>
  <text x="790" y="112" font-size="8.5" font-family="Segoe UI,Arial">   both 200A feeders into one hybrid.</text>
  <text x="790" y="128" font-size="8.5" font-family="Segoe UI,Arial">3. LOAD port feeds backed-up panel only. Torque all lugs to mfr.</text>
  <text x="790" y="144" font-size="8.5" font-family="Segoe UI,Arial">4. PV: polarity, string map per PV-4, RSD initiator at service.</text>
  <text x="790" y="160" font-size="8.5" font-family="Segoe UI,Arial">5. Battery: polarity, integrated disco ON only after DC/AC landed.</text>
  <text x="790" y="176" font-size="8.5" font-family="Segoe UI,Arial">6. Bonding: ONE neutral-ground bond at service. No N-G in hybrid</text>
  <text x="790" y="188" font-size="8.5" font-family="Segoe UI,Arial">   or subpanels unless mfr isolation requires (follow manual).</text>
  <text x="790" y="204" font-size="8.5" font-family="Segoe UI,Arial">7. Labels: install PV-6 stickers before energization.</text>
  <text x="790" y="220" font-size="8.5" font-family="Segoe UI,Arial">8. Commission: grid, then PV, then battery per mfr checklist.</text>
  <text x="790" y="238" font-size="8.5" fill="#8b0000" font-weight="700" font-family="Segoe UI,Arial">⚠ Island amps ≈ {cont_a:.0f}A cont — do NOT expect full {disco}A panel in blackout.</text>

  <!-- Legend -->
  <rect x="780" y="265" width="380" height="70" fill="#fff" stroke="#111" stroke-width="1"/>
  <text x="790" y="282" font-size="9" font-weight="700" font-family="Segoe UI,Arial">LEGEND</text>
  <text x="790" y="298" font-size="8" font-family="Segoe UI,Arial">■ Green path = backed-up AC · ■ Black = utility only · ■ Gold = PV DC · ■ Orange = battery DC</text>
  <text x="790" y="312" font-size="8" font-family="Segoe UI,Arial">Yellow boxes = conductor callouts (design basis — EC confirms temp/fill/VD)</text>
  <text x="790" y="326" font-size="8" font-family="Segoe UI,Arial">Red box = rapid shutdown initiator (690.12) · GES = grounding electrode system</text>

  <!-- Conductor schedule strip -->
  <rect x="10" y="545" width="1160" height="165" fill="#fafafa" stroke="#111" stroke-width="1.2"/>
  <text x="20" y="562" font-size="10" font-weight="700" font-family="Segoe UI,Arial">CONDUCTOR / OCPD SCHEDULE (FROM THIS SLD — ALSO ON PV-5)</text>
  {''.join(seg_lines)}
  <text x="20" y="700" font-size="8" fill="#444" font-family="Segoe UI,Arial">All Cu THWN-2 unless noted · 75°C terminations · EGC with every circuit · Verify voltage drop if runs &gt; 100 ft · AHJ may require larger.</text>
</svg>'''


def _sld_full_dual(project, totals, inv_name, mod_line, n_str, voc_note, cont_a, disco, pass_a, seg_lines) -> str:
    # Simplified: two mirrored hybrids
    return _sld_half_home(
        project, totals, inv_name + " (×2 PATHS)", mod_line, n_str, voc_note,
        cont_a, int(cont_a * 1.25), disco, pass_a, False, seg_lines, [],
    ).replace(
        "BACKED-UP LOAD CENTER #1",
        "BU PANEL #1  |  mirror Disco#2→Hybrid B→Panel#2 for full dual",
    )


def _sld_backfeed(project, totals, inv_name, mod_line, n_str, voc_note, cont_a, inv_ocpd, seg_lines) -> str:
    feed = _awg_for_amps(inv_ocpd)
    egc = _egc_for_ocpd(inv_ocpd)
    conduit = _conduit_for_fill(4, feed)
    main = project.service.main_breaker_a
    bus = project.service.busbar_a or main
    return f'''<svg class="sld" viewBox="0 0 1180 720" xmlns="http://www.w3.org/2000/svg">
  <text x="16" y="16" font-size="11" font-weight="700" font-family="Segoe UI,Arial">ELECTRICAL SINGLE-LINE DIAGRAM — BACKFED BREAKER · SCALE: NTS · 120/240V 1Ø</text>
  <text x="16" y="30" font-size="9" fill="#333" font-family="Segoe UI,Arial">Install grade. (E)=existing (N)=new. Backfeed OCPD at opposite end of bus from main when using 120% rule (NEC 705.12).</text>

  <circle cx="500" cy="50" r="14" fill="none" stroke="#111" stroke-width="2"/>
  <text x="500" y="54" text-anchor="middle" font-size="12" font-weight="700">~</text>
  <text x="525" y="54" font-size="11" font-weight="700" font-family="Segoe UI,Arial">(E) UTILITY {project.service.voltage}</text>

  <line x1="500" y1="64" x2="500" y2="90" stroke="#111" stroke-width="2.5"/>
  <rect x="420" y="90" width="160" height="34" fill="#fff" stroke="#111" stroke-width="2"/>
  <text x="500" y="112" text-anchor="middle" font-size="10" font-weight="700" font-family="Segoe UI,Arial">(E) UTILITY METER</text>

  <line x1="500" y1="124" x2="500" y2="150" stroke="#111" stroke-width="2.5"/>
  <rect x="400" y="150" width="200" height="70" fill="#fff" stroke="#111" stroke-width="2.2"/>
  <text x="500" y="170" text-anchor="middle" font-size="11" font-weight="700" font-family="Segoe UI,Arial">(E) MAIN SERVICE PANEL</text>
  <text x="500" y="186" text-anchor="middle" font-size="9" font-family="Segoe UI,Arial">Main breaker {main}A · Bus {bus}A</text>
  <text x="500" y="202" text-anchor="middle" font-size="9" fill="#0b5c2e" font-family="Segoe UI,Arial">(N) BACKFEED {inv_ocpd}A 2P — opposite end of bus</text>

  <!-- ground -->
  <line x1="500" y1="220" x2="500" y2="240" stroke="#111" stroke-width="2.5"/>
  {_wire_note(520, 210, f"(2) {feed} + {egc} EGC + N · {conduit} · 75°C", 180)}

  <rect x="380" y="250" width="240" height="90" fill="#fff" stroke="#0b5c2e" stroke-width="2.5"/>
  <text x="500" y="275" text-anchor="middle" font-size="12" font-weight="700" fill="#0b5c2e" font-family="Segoe UI,Arial">(N) {inv_name}</text>
  <text x="500" y="295" text-anchor="middle" font-size="9" font-family="Segoe UI,Arial">AC output → backfeed · continuous {cont_a:.1f}A @ 240V</text>
  <text x="500" y="312" text-anchor="middle" font-size="8" fill="#444" font-family="Segoe UI,Arial">PV + BAT ports as equipped · UL 1741</text>
  <text x="500" y="328" text-anchor="middle" font-size="8" fill="#666" font-family="Segoe UI,Arial">120% bus check on PV-4</text>

  <line x1="380" y1="295" x2="280" y2="295" stroke="#b8860b" stroke-width="2"/>
  <rect x="160" y="270" width="120" height="50" fill="#fff8e6" stroke="#b8860b" stroke-width="2"/>
  <text x="220" y="292" text-anchor="middle" font-size="9" font-weight="700" fill="#6b5200" font-family="Segoe UI,Arial">(N) PV ARRAY</text>
  <text x="220" y="308" text-anchor="middle" font-size="7.5" font-family="Segoe UI,Arial">{mod_line[:36]}</text>

  <line x1="620" y1="295" x2="720" y2="295" stroke="#c45c00" stroke-width="2"/>
  <rect x="720" y="270" width="110" height="50" fill="#fff5eb" stroke="#c45c00" stroke-width="2"/>
  <text x="775" y="292" text-anchor="middle" font-size="9" font-weight="700" fill="#c45c00" font-family="Segoe UI,Arial">(N) BATTERY</text>
  <text x="775" y="308" text-anchor="middle" font-size="8" font-family="Segoe UI,Arial">{totals.battery_kwh:.0f} kWh</text>

  <rect x="400" y="360" width="200" height="40" fill="#8b0000"/>
  <text x="500" y="384" text-anchor="middle" font-size="10" font-weight="700" fill="#fff" font-family="Segoe UI,Arial">RSD INITIATOR · NEC 690.12</text>

  <rect x="780" y="50" width="380" height="160" fill="#f7f7f7" stroke="#111"/>
  <text x="790" y="70" font-size="10" font-weight="700" font-family="Segoe UI,Arial">ELECTRICIAN — BACKFEED RULES</text>
  <text x="790" y="90" font-size="8.5" font-family="Segoe UI,Arial">1. Install {inv_ocpd}A 2P at end of bus opposite main feeder.</text>
  <text x="790" y="106" font-size="8.5" font-family="Segoe UI,Arial">2. Confirm 120% rule on PV-4 before energizing.</text>
  <text x="790" y="122" font-size="8.5" font-family="Segoe UI,Arial">3. Hold-down / fastener if required by panel listing.</text>
  <text x="790" y="138" font-size="8.5" font-family="Segoe UI,Arial">4. Label dual power source at MSP and meter.</text>
  <text x="790" y="154" font-size="8.5" font-family="Segoe UI,Arial">5. Do not exceed bus ampacity with main + backfeed sum.</text>
  <text x="790" y="175" font-size="8.5" fill="#8b0000" font-family="Segoe UI,Arial">Main {main}A + BF {inv_ocpd}A vs 1.20×{bus}A bus — see PV-4.</text>

  <rect x="10" y="520" width="1160" height="180" fill="#fafafa" stroke="#111"/>
  <text x="20" y="540" font-size="10" font-weight="700" font-family="Segoe UI,Arial">CONDUCTOR / OCPD SCHEDULE</text>
  {''.join(seg_lines)}
</svg>'''


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
