"""Clean SLD diagram layouts — no overlapping text.

Designed for the main column next to the customer title rail (~900–1000 CSS px).
"""

from __future__ import annotations


def sld_half_home_svg(
    *,
    voltage: str,
    phase: str,
    service_a: int,
    main_a: int,
    bus_a: int | None,
    disco: int,
    pass_a: float,
    cont_a: float,
    ac_kw: float,
    inv_name: str,
    inv_ne_ma: str,
    inv_qty: int,
    load_title: str,
    mod_line: str,
    n_str: int,
    voc_note: str,
    bat_kwh: float,
    ac_disco_a: int | None,
    feed: str,
    egc: str,
    conduit: str,
    seg_lines: list[str],
) -> str:
    """Half-home / dual-disco hybrid one-line with clear columns."""
    inv_short = inv_name if len(inv_name) <= 42 else inv_name[:40] + "…"
    load_short = load_title if len(load_title) <= 28 else load_title[:26] + "…"
    mod_short = mod_line if len(mod_line) <= 44 else mod_line[:42] + "…"
    voc_short = (voc_note or "See PV-4 string calcs")[:44]
    bus_txt = f" · Bus {bus_a}A" if bus_a else ""

    ac_extra = ""
    if ac_disco_a:
        ac_extra = f"""
  <line x1="200" y1="248" x2="200" y2="262" stroke="#0b5c2e" stroke-width="2"/>
  <rect x="145" y="262" width="110" height="24" fill="#fff" stroke="#b00000" stroke-width="1.5"/>
  <text x="200" y="278" text-anchor="middle" font-size="8" font-weight="700" fill="#b00000" font-family="Segoe UI,Arial">(N) {ac_disco_a}A AC DISCO</text>
  <line x1="200" y1="286" x2="200" y2="300" stroke="#0b5c2e" stroke-width="2"/>
"""
    else:
        ac_extra = '<line x1="200" y1="248" x2="200" y2="300" stroke="#0b5c2e" stroke-width="2"/>'

    segs_joined = "\n".join(seg_lines)

    return f'''<svg class="sld" viewBox="0 0 920 680" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial, sans-serif">
  <!-- Header strip -->
  <rect x="0" y="0" width="920" height="36" fill="#f0f0f0" stroke="#111" stroke-width="1"/>
  <text x="10" y="15" font-size="10" font-weight="700">ELECTRICAL SINGLE-LINE DIAGRAM · 120/240 V 1Ø · SCALE: NTS</text>
  <text x="10" y="28" font-size="8" fill="#333">Power flow TOP → BOTTOM · single line = L1/L2/N/G · (E)=existing · (N)=new · verify ampacity &amp; torque in field</text>

  <!-- ========== LEFT COLUMN: ONE-LINE ========== -->
  <!-- Utility -->
  <circle cx="200" cy="58" r="12" fill="none" stroke="#111" stroke-width="1.8"/>
  <text x="200" y="62" text-anchor="middle" font-size="12" font-weight="700">~</text>
  <text x="220" y="56" font-size="9" font-weight="700">(E) UTILITY</text>
  <text x="220" y="68" font-size="8" fill="#444">{voltage} · {phase}</text>

  <line x1="200" y1="70" x2="200" y2="88" stroke="#111" stroke-width="2"/>
  <rect x="140" y="88" width="120" height="28" fill="#fff" stroke="#111" stroke-width="1.5"/>
  <text x="200" y="106" text-anchor="middle" font-size="9" font-weight="700">(E) METER</text>

  <line x1="200" y1="116" x2="200" y2="132" stroke="#111" stroke-width="2"/>
  <rect x="125" y="132" width="150" height="32" fill="#fff" stroke="#111" stroke-width="1.5"/>
  <text x="200" y="146" text-anchor="middle" font-size="9" font-weight="700">(E) {service_a}A SERVICE</text>
  <text x="200" y="158" text-anchor="middle" font-size="7.5" fill="#444">Main {main_a}A{bus_txt}</text>

  <!-- Split -->
  <line x1="200" y1="164" x2="200" y2="178" stroke="#111" stroke-width="2"/>
  <line x1="90" y1="178" x2="360" y2="178" stroke="#111" stroke-width="2"/>
  <line x1="90" y1="178" x2="90" y2="192" stroke="#111" stroke-width="2"/>
  <line x1="360" y1="178" x2="360" y2="192" stroke="#111" stroke-width="2"/>

  <!-- Disco 1 -->
  <rect x="35" y="192" width="110" height="40" fill="#e8f5ee" stroke="#0b5c2e" stroke-width="1.8"/>
  <text x="90" y="208" text-anchor="middle" font-size="9" font-weight="700" fill="#0b5c2e">(E) {disco}A DISCO #1</text>
  <text x="90" y="222" text-anchor="middle" font-size="7.5" fill="#333">TO HYBRID GRID</text>

  <!-- Disco 2 -->
  <rect x="305" y="192" width="110" height="40" fill="#fff" stroke="#111" stroke-width="1.5"/>
  <text x="360" y="208" text-anchor="middle" font-size="9" font-weight="700">(E) {disco}A DISCO #2</text>
  <text x="360" y="222" text-anchor="middle" font-size="7.5" fill="#555">UTILITY ONLY</text>

  <!-- Path to hybrid (left) -->
  <line x1="90" y1="232" x2="90" y2="248" stroke="#0b5c2e" stroke-width="2"/>
  <line x1="90" y1="248" x2="200" y2="248" stroke="#0b5c2e" stroke-width="2"/>
  {ac_extra}

  <!-- Hybrid inverter -->
  <rect x="95" y="300" width="210" height="88" fill="#fff" stroke="#0b5c2e" stroke-width="2"/>
  <text x="200" y="316" text-anchor="middle" font-size="9" font-weight="700" fill="#0b5c2e">(N) HYBRID INVERTER</text>
  <text x="200" y="330" text-anchor="middle" font-size="8" fill="#222">{inv_short}</text>
  <text x="200" y="343" text-anchor="middle" font-size="7.5" fill="#444">UL 1741 · {inv_ne_ma} · qty {inv_qty}</text>
  <text x="200" y="356" text-anchor="middle" font-size="7.5" fill="#333">GRID ← Disco#1 · LOAD → BU panel</text>
  <text x="200" y="369" text-anchor="middle" font-size="7.5" fill="#333">Pass-thru {pass_a:.0f}A · Island ~{cont_a:.0f}A ({ac_kw:.1f} kW)</text>
  <text x="200" y="381" text-anchor="middle" font-size="7.5" fill="#8b0000" font-weight="700">Island ≠ {disco}A panel handle</text>

  <!-- PV left of hybrid -->
  <line x1="95" y1="340" x2="50" y2="340" stroke="#b8860b" stroke-width="2"/>
  <line x1="50" y1="340" x2="50" y2="400" stroke="#b8860b" stroke-width="2"/>
  <rect x="8" y="400" width="84" height="52" fill="#fff8e6" stroke="#b8860b" stroke-width="1.5"/>
  <text x="50" y="416" text-anchor="middle" font-size="8" font-weight="700" fill="#6b5200">(N) PV ARRAY</text>
  <text x="50" y="428" text-anchor="middle" font-size="6.5" fill="#333">{mod_short[:22]}</text>
  <text x="50" y="439" text-anchor="middle" font-size="6.5" fill="#555">{n_str} str · PV-4</text>
  <text x="50" y="448" text-anchor="middle" font-size="6" fill="#666">{voc_short[:20]}</text>

  <!-- Battery right of hybrid -->
  <line x1="305" y1="340" x2="350" y2="340" stroke="#c45c00" stroke-width="2"/>
  <rect x="350" y="318" width="88" height="44" fill="#fff5eb" stroke="#c45c00" stroke-width="1.5"/>
  <text x="394" y="336" text-anchor="middle" font-size="8" font-weight="700" fill="#c45c00">(N) BATTERY</text>
  <text x="394" y="350" text-anchor="middle" font-size="7.5" fill="#333">{bat_kwh:.0f} kWh</text>
  <text x="394" y="361" text-anchor="middle" font-size="6.5" fill="#555">int. DC disco</text>

  <!-- Load out -->
  <line x1="200" y1="388" x2="200" y2="412" stroke="#0b5c2e" stroke-width="2"/>
  <rect x="115" y="412" width="170" height="36" fill="#0b5c2e"/>
  <text x="200" y="428" text-anchor="middle" font-size="9" font-weight="700" fill="#fff">(N) {load_short}</text>
  <text x="200" y="441" text-anchor="middle" font-size="7.5" fill="#d4f0e2">Main ≤{disco}A · island ~{cont_a:.0f}A cont.</text>

  <!-- Panel 2 path -->
  <line x1="360" y1="232" x2="360" y2="280" stroke="#111" stroke-width="2"/>
  <rect x="305" y="280" width="110" height="32" fill="#fff" stroke="#111" stroke-width="1.5"/>
  <text x="360" y="294" text-anchor="middle" font-size="8" font-weight="700">(E) PANEL #2</text>
  <text x="360" y="306" text-anchor="middle" font-size="7" fill="#666">DARK IN OUTAGE</text>

  <!-- RSD -->
  <rect x="310" y="400" width="130" height="36" fill="#8b0000"/>
  <text x="375" y="415" text-anchor="middle" font-size="8" font-weight="700" fill="#fff">RSD INITIATOR</text>
  <text x="375" y="428" text-anchor="middle" font-size="7" fill="#fcc">NEC 690.12 · outdoor</text>

  <!-- GEC -->
  <line x1="275" y1="148" x2="300" y2="148" stroke="#111" stroke-width="1"/>
  <line x1="300" y1="148" x2="300" y2="162" stroke="#111" stroke-width="1"/>
  <line x1="292" y1="162" x2="308" y2="162" stroke="#111" stroke-width="1.4"/>
  <line x1="294" y1="167" x2="306" y2="167" stroke="#111" stroke-width="1.4"/>
  <text x="312" y="160" font-size="7" fill="#333">GEC</text>

  <!-- ========== RIGHT COLUMN: NOTES (no collision with diagram) ========== -->
  <rect x="460" y="48" width="450" height="200" fill="#f7f7f7" stroke="#111" stroke-width="1.2"/>
  <text x="472" y="66" font-size="10" font-weight="700">ELECTRICIAN — INSTALL SEQUENCE</text>
  <line x1="472" y1="72" x2="896" y2="72" stroke="#ccc"/>
  <text x="472" y="90" font-size="8">1. LOTO Disco #1 and #2. Verify zero energy.</text>
  <text x="472" y="105" font-size="8">2. Land hybrid GRID on load side of Disco #1 only.</text>
  <text x="472" y="118" font-size="8">   Never combine both 200 A feeders into one inverter.</text>
  <text x="472" y="135" font-size="8">3. LOAD port → backed-up panel only. Torque all lugs.</text>
  <text x="472" y="150" font-size="8">4. PV: polarity, string map (PV-4), RSD initiator at service.</text>
  <text x="472" y="165" font-size="8">5. Battery last: polarity, integrated disco after AC/DC landed.</text>
  <text x="472" y="180" font-size="8">6. Bonding: single N–G bond at service only (unless mfr requires).</text>
  <text x="472" y="195" font-size="8">7. Apply PV-6 labels before energization. Commission per mfr.</text>
  <text x="472" y="218" font-size="8" fill="#8b0000" font-weight="700">Island continuous ≈ {cont_a:.0f} A @ 240 V — not full {disco} A panel.</text>
  <text x="472" y="235" font-size="7.5" fill="#444">Conductors (design basis): GRID/LOAD (2) {feed} + {egc} EGC + N in {conduit} · 75 °C</text>

  <rect x="460" y="260" width="450" height="72" fill="#fff" stroke="#111" stroke-width="1"/>
  <text x="472" y="276" font-size="9" font-weight="700">LEGEND</text>
  <text x="472" y="292" font-size="7.5">Green = backed-up AC path · Black = utility-only · Gold = PV DC · Orange = battery DC</text>
  <text x="472" y="306" font-size="7.5">Red = rapid shutdown (690.12) · Schedule below = pull wire / set OCPD</text>
  <text x="472" y="320" font-size="7.5" fill="#555">Field EC confirms ampacity, conduit fill, voltage drop, and AHJ rules.</text>

  <!-- ========== BOTTOM: CONDUCTOR SCHEDULE ========== -->
  <rect x="8" y="470" width="904" height="200" fill="#fafafa" stroke="#111" stroke-width="1.2"/>
  <text x="16" y="488" font-size="9" font-weight="700">CONDUCTOR / OCPD SCHEDULE (also on PV-5)</text>
  <line x1="16" y1="494" x2="900" y2="494" stroke="#ccc"/>
  {segs_joined}
  <text x="16" y="660" font-size="7.5" fill="#444">Cu THWN-2 unless noted · EGC with every circuit · VD check if run &gt; 100 ft · AHJ may require upsizing</text>
</svg>'''


def sld_backfeed_svg(
    *,
    voltage: str,
    main_a: int,
    bus_a: int,
    inv_ocpd: int,
    cont_a: float,
    inv_name: str,
    mod_line: str,
    bat_kwh: float,
    feed: str,
    egc: str,
    conduit: str,
    seg_lines: list[str],
) -> str:
    inv_short = inv_name if len(inv_name) <= 40 else inv_name[:38] + "…"
    mod_short = mod_line if len(mod_line) <= 36 else mod_line[:34] + "…"
    segs_joined = "\n".join(seg_lines)
    return f'''<svg class="sld" viewBox="0 0 920 640" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial, sans-serif">
  <rect x="0" y="0" width="920" height="36" fill="#f0f0f0" stroke="#111"/>
  <text x="10" y="15" font-size="10" font-weight="700">ELECTRICAL SLD — BACKFED BREAKER · {voltage} · NTS</text>
  <text x="10" y="28" font-size="8" fill="#333">Backfeed OCPD at opposite end of bus from main (NEC 705.12 120% rule) · (E)/(N) tags</text>

  <circle cx="220" cy="60" r="12" fill="none" stroke="#111" stroke-width="1.8"/>
  <text x="220" y="64" text-anchor="middle" font-size="12" font-weight="700">~</text>
  <text x="240" y="64" font-size="9" font-weight="700">(E) UTILITY {voltage}</text>

  <line x1="220" y1="72" x2="220" y2="92" stroke="#111" stroke-width="2"/>
  <rect x="155" y="92" width="130" height="28" fill="#fff" stroke="#111"/>
  <text x="220" y="110" text-anchor="middle" font-size="9" font-weight="700">(E) METER</text>

  <line x1="220" y1="120" x2="220" y2="140" stroke="#111" stroke-width="2"/>
  <rect x="130" y="140" width="180" height="56" fill="#fff" stroke="#111" stroke-width="1.8"/>
  <text x="220" y="158" text-anchor="middle" font-size="9" font-weight="700">(E) MAIN SERVICE PANEL</text>
  <text x="220" y="172" text-anchor="middle" font-size="8" fill="#333">Main {main_a}A · Bus {bus_a}A</text>
  <text x="220" y="186" text-anchor="middle" font-size="8" fill="#0b5c2e" font-weight="700">(N) BACKFEED {inv_ocpd}A 2P — opp. end of bus</text>

  <line x1="220" y1="196" x2="220" y2="220" stroke="#0b5c2e" stroke-width="2"/>
  <rect x="115" y="220" width="210" height="70" fill="#fff" stroke="#0b5c2e" stroke-width="2"/>
  <text x="220" y="240" text-anchor="middle" font-size="9" font-weight="700" fill="#0b5c2e">(N) INVERTER</text>
  <text x="220" y="254" text-anchor="middle" font-size="8">{inv_short}</text>
  <text x="220" y="268" text-anchor="middle" font-size="7.5" fill="#333">AC → backfeed · cont. {cont_a:.1f}A @ 240V</text>
  <text x="220" y="280" text-anchor="middle" font-size="7.5" fill="#555">120% bus check on PV-4</text>

  <line x1="115" y1="255" x2="70" y2="255" stroke="#b8860b" stroke-width="2"/>
  <rect x="8" y="235" width="62" height="40" fill="#fff8e6" stroke="#b8860b"/>
  <text x="39" y="252" text-anchor="middle" font-size="7.5" font-weight="700" fill="#6b5200">(N) PV</text>
  <text x="39" y="265" text-anchor="middle" font-size="6.5" fill="#333">{mod_short[:14]}</text>

  <line x1="325" y1="255" x2="370" y2="255" stroke="#c45c00" stroke-width="2"/>
  <rect x="370" y="235" width="70" height="40" fill="#fff5eb" stroke="#c45c00"/>
  <text x="405" y="252" text-anchor="middle" font-size="7.5" font-weight="700" fill="#c45c00">(N) BAT</text>
  <text x="405" y="265" text-anchor="middle" font-size="7" fill="#333">{bat_kwh:.0f} kWh</text>

  <rect x="130" y="310" width="180" height="28" fill="#8b0000"/>
  <text x="220" y="328" text-anchor="middle" font-size="8" font-weight="700" fill="#fff">RSD INITIATOR · 690.12</text>

  <rect x="460" y="50" width="450" height="150" fill="#f7f7f7" stroke="#111"/>
  <text x="472" y="68" font-size="10" font-weight="700">ELECTRICIAN — BACKFEED RULES</text>
  <text x="472" y="88" font-size="8">1. Install {inv_ocpd}A 2P at bus end opposite main feeder.</text>
  <text x="472" y="104" font-size="8">2. Confirm 120% rule on PV-4 before energizing.</text>
  <text x="472" y="120" font-size="8">3. Hold-down if required by panel listing.</text>
  <text x="472" y="136" font-size="8">4. Label dual power source at MSP and meter (PV-6).</text>
  <text x="472" y="158" font-size="8" fill="#8b0000" font-weight="700">Main {main_a}A + BF {inv_ocpd}A vs 1.20 × {bus_a}A bus — see PV-4.</text>
  <text x="472" y="180" font-size="7.5" fill="#444">Conductor: (2) {feed} + {egc} EGC + N · {conduit} · 75 °C</text>

  <rect x="8" y="360" width="904" height="260" fill="#fafafa" stroke="#111"/>
  <text x="16" y="378" font-size="9" font-weight="700">CONDUCTOR / OCPD SCHEDULE</text>
  <line x1="16" y1="384" x2="900" y2="384" stroke="#ccc"/>
  {segs_joined}
</svg>'''
