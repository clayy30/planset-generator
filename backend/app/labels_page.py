"""PV-6 warning labels page — layout copied from common US solar permit practice.

Label text and colors follow the public NEC (not proprietary vendor art).
Visual arrangement mirrors typical Solar Permit Solutions / AHJ submittal
sheets and the free MN DLI “2020 NEC Labeling Requirements” guide
(data/equipment/labels/MN_DLI_solar_labelguide.pdf).
"""

from __future__ import annotations

from .calcs import SystemTotals
from .models import ProjectInput


def generate_labels_svg(project: ProjectInput, totals: SystemTotals) -> str:
    inv = project.inverters[0] if project.inverters else None
    ac_a = f"{totals.ac_a_continuous:.1f}"
    inv_name = f"{inv.manufacturer} {inv.model}" if inv else "INVERTER"
    main_a = project.service.main_breaker_a
    disco_a = project.service.ac_disco_a or project.service.disconnect_rating_a
    has_bat = totals.battery_kwh > 0
    bat_line = f"(N) BATTERY {totals.battery_kwh:.0f} kWh" if has_bat else ""
    addr = project.meta.address
    street = addr.line1.upper() if addr.line1 else "SITE STREET"

    # ESS block only if batteries
    ess_block = ""
    if has_bat:
        ess_block = f'''
  <!-- ESS DISCONNECT -->
  <rect x="248" y="418" width="220" height="95" fill="#fff" stroke="#111" stroke-width="1.2"/>
  <text x="358" y="438" text-anchor="middle" font-size="10" font-weight="800" fill="#c41e3a" font-family="Arial,sans-serif">ENERGY STORAGE SYSTEM</text>
  <text x="358" y="452" text-anchor="middle" font-size="10" font-weight="800" fill="#c41e3a" font-family="Arial,sans-serif">DISCONNECT</text>
  <text x="258" y="470" font-size="8" font-family="Arial,sans-serif">NOMINAL VOLTAGE: <tspan font-weight="700" fill="#c41e3a">240 VAC / 48 VDC</tspan></text>
  <text x="258" y="484" font-size="8" font-family="Arial,sans-serif">MAX AVAILABLE ISC: <tspan font-weight="700" fill="#c41e3a">PER MFR</tspan></text>
  <text x="258" y="498" font-size="8" font-family="Arial,sans-serif">REQ'D BY NEC 706 · APPLY TO: BATTERY</text>
'''

    return f'''<svg class="sld" viewBox="0 0 1000 620" xmlns="http://www.w3.org/2000/svg" font-family="Arial, Helvetica, sans-serif">
  <text x="8" y="14" font-size="9" fill="#555">WARNING LABELS &amp; PLACARDS — text/colors per NEC · layout per common US permit practice &amp; public MN DLI NEC labeling guide (non-proprietary)</text>

  <!-- ========== COL 1 ========== -->
  <!-- Shock hazard -->
  <rect x="8" y="24" width="228" height="88" fill="#fff" stroke="#111" stroke-width="1.3"/>
  <rect x="8" y="24" width="228" height="22" fill="#111"/>
  <polygon points="18,28 28,42 8,42" fill="#fc0" stroke="#111" stroke-width="0.8"/>
  <text x="20" y="40" font-size="8" font-weight="900">!</text>
  <text x="36" y="40" font-size="11" font-weight="800" fill="#fc0">WARNING</text>
  <text x="16" y="60" font-size="9" font-weight="700">ELECTRICAL SHOCK HAZARD</text>
  <text x="16" y="74" font-size="7.5">TERMINALS ON LINE AND LOAD</text>
  <text x="16" y="84" font-size="7.5">SIDES MAY BE ENERGIZED IN</text>
  <text x="16" y="94" font-size="7.5">THE OPEN POSITION</text>
  <text x="16" y="106" font-size="6.5" fill="#444">LOC: inverter / AC disco · NEC 705.20 / 690.13(B)</text>

  <!-- PV AC DISCONNECT nameplate style -->
  <rect x="8" y="122" width="228" height="72" fill="#fff" stroke="#c41e3a" stroke-width="2.5"/>
  <text x="122" y="145" text-anchor="middle" font-size="14" font-weight="900" fill="#c41e3a">PHOTOVOLTAIC</text>
  <line x1="24" y1="152" x2="220" y2="152" stroke="#c41e3a" stroke-width="1.5"/>
  <text x="122" y="172" text-anchor="middle" font-size="14" font-weight="900" fill="#c41e3a">AC DISCONNECT</text>
  <text x="16" y="188" font-size="6.5" fill="#444">LOC: AC disconnect · NEC 690.13(B)</text>

  <!-- Dual power source -->
  <rect x="8" y="204" width="228" height="70" fill="#fff" stroke="#111" stroke-width="1.3"/>
  <rect x="8" y="204" width="228" height="28" fill="#e65c00"/>
  <text x="16" y="223" font-size="10" font-weight="800" fill="#fff">⚠ WARNING  DUAL POWER SOURCE</text>
  <text x="16" y="246" font-size="8" font-weight="700">SECOND SOURCE IS PHOTOVOLTAIC SYSTEM</text>
  <text x="16" y="262" font-size="6.5" fill="#444">LOC: POI / production meter · NEC 705.30(C) / 690.59</text>

  <!-- Notes -->
  <rect x="8" y="284" width="228" height="130" fill="#fff" stroke="#111" stroke-width="1"/>
  <text x="16" y="300" font-size="8" font-weight="700">NOTES AND SPECIFICATIONS:</text>
  <text x="16" y="314" font-size="6.5">• Signs/labels meet NEC 110.21(B) &amp; Art. 690/705/706</text>
  <text x="16" y="326" font-size="6.5">• Permanent; not handwritten; durable for environment</text>
  <text x="16" y="338" font-size="6.5">• Comply with ANSI Z535.4 product safety signs</text>
  <text x="16" y="350" font-size="6.5">• Do not cover manufacturer labels</text>
  <text x="16" y="362" font-size="6.5">• Match NEC edition adopted by AHJ</text>
  <text x="16" y="378" font-size="6.5" fill="#555">Source text: public NEC · layout: common US</text>
  <text x="16" y="390" font-size="6.5" fill="#555">permit practice (e.g. MN DLI free guide)</text>
  <text x="16" y="402" font-size="6.5" fill="#555">Project values: AC {ac_a} A · 240 V</text>

  <!-- Busbar multi source warning -->
  <rect x="8" y="424" width="228" height="88" fill="#fff" stroke="#111" stroke-width="1.3"/>
  <rect x="8" y="424" width="228" height="20" fill="#111"/>
  <text x="16" y="438" font-size="10" font-weight="800" fill="#fc0">⚠ WARNING</text>
  <text x="16" y="458" font-size="7.5" font-weight="700">THIS EQUIPMENT FED BY MULTIPLE SOURCES:</text>
  <text x="16" y="472" font-size="7">TOTAL RATING OF ALL OVERCURRENT</text>
  <text x="16" y="483" font-size="7">DEVICES EXCLUDING MAIN POWER SUPPLY</text>
  <text x="16" y="494" font-size="7">SHALL NOT EXCEED AMPACITY OF BUSBAR</text>
  <text x="16" y="506" font-size="6.5" fill="#444">LOC: points of connection · NEC 705.12</text>

  <!-- ========== COL 2 ========== -->
  <!-- AC disco with numbers -->
  <rect x="248" y="24" width="220" height="78" fill="#c41e3a"/>
  <text x="358" y="44" text-anchor="middle" font-size="11" font-weight="900" fill="#fff">PHOTOVOLTAIC AC DISCONNECT</text>
  <text x="258" y="62" font-size="8" fill="#fff">MAXIMUM AC OPERATING CURRENT: <tspan font-weight="700">{ac_a} AMPS</tspan></text>
  <text x="258" y="76" font-size="8" fill="#fff">NOMINAL OPERATING AC VOLTAGE: <tspan font-weight="700">240 VAC</tspan></text>
  <text x="258" y="92" font-size="6.5" fill="#fcc">LOC: AC disco / POI · NEC 690.54</text>

  <rect x="248" y="112" width="220" height="40" fill="#c41e3a"/>
  <text x="358" y="130" text-anchor="middle" font-size="11" font-weight="900" fill="#fff">PHOTOVOLTAIC POWER SOURCE</text>
  <text x="358" y="144" text-anchor="middle" font-size="6.5" fill="#fcc">LOC: EMT / raceways · NEC 690.31(D)(2)</text>

  <rect x="248" y="162" width="220" height="48" fill="#c41e3a"/>
  <text x="358" y="180" text-anchor="middle" font-size="10" font-weight="900" fill="#fff">MAIN PHOTOVOLTAIC</text>
  <text x="358" y="194" text-anchor="middle" font-size="10" font-weight="900" fill="#fff">SYSTEM DISCONNECT</text>
  <text x="358" y="206" text-anchor="middle" font-size="6.5" fill="#fcc">LOC: main service disco / meter · 690.13(B)</text>

  <rect x="248" y="220" width="220" height="56" fill="#c41e3a"/>
  <text x="358" y="240" text-anchor="middle" font-size="10" font-weight="900" fill="#fff">RAPID SHUTDOWN SWITCH</text>
  <text x="358" y="254" text-anchor="middle" font-size="10" font-weight="900" fill="#fff">FOR SOLAR PV SYSTEM</text>
  <text x="358" y="268" text-anchor="middle" font-size="6.5" fill="#fcc">White on red · reflective · ≥3/8″ · ≤3 ft of switch · 690.12(D)(2)</text>

  <!-- Grounded conductor warning -->
  <rect x="248" y="288" width="220" height="72" fill="#fff" stroke="#111" stroke-width="1.3"/>
  <rect x="248" y="288" width="220" height="22" fill="#e65c00"/>
  <text x="258" y="304" font-size="11" font-weight="800" fill="#fff">⚠ WARNING</text>
  <text x="258" y="326" font-size="7.5">THE DISCONNECTION OF THE GROUNDED</text>
  <text x="258" y="338" font-size="7.5">CONDUCTOR(S) MAY RESULT IN OVERVOLTAGE</text>
  <text x="258" y="350" font-size="7.5">ON THE EQUIPMENT</text>
  <text x="258" y="362" font-size="6.5" fill="#444">LOC: combiner / equip · NEC 690.31</text>

  {ess_block}

  <!-- DC voltage label -->
  <rect x="248" y="528" width="220" height="48" fill="#fff" stroke="#c41e3a" stroke-width="2"/>
  <text x="358" y="548" text-anchor="middle" font-size="10" font-weight="800" fill="#c41e3a">MAXIMUM DC VOLTAGE</text>
  <text x="358" y="564" text-anchor="middle" font-size="9" fill="#c41e3a">OF PV SYSTEM — SEE PV-4</text>

  <!-- ========== COL 3 ========== -->
  <!-- RSD yellow placard -->
  <rect x="484" y="24" width="250" height="150" fill="#ffd100" stroke="#111" stroke-width="2"/>
  <text x="609" y="48" text-anchor="middle" font-size="12" font-weight="900">SOLAR PV SYSTEM EQUIPPED</text>
  <text x="609" y="64" text-anchor="middle" font-size="12" font-weight="900">WITH RAPID SHUTDOWN</text>
  <!-- house icon -->
  <polygon points="580,88 609,68 638,88 638,118 580,118" fill="#fff" stroke="#111" stroke-width="1.5"/>
  <rect x="598" y="98" width="22" height="20" fill="#1a5fb4" stroke="#111"/>
  <text x="609" y="136" text-anchor="middle" font-size="7.5" font-weight="700">TURN RAPID SHUTDOWN SWITCH TO</text>
  <text x="609" y="148" text-anchor="middle" font-size="7.5" font-weight="700">THE “OFF” POSITION TO SHUT DOWN</text>
  <text x="609" y="160" text-anchor="middle" font-size="7.5" font-weight="700">PV SYSTEM AND REDUCE SHOCK</text>
  <text x="609" y="172" text-anchor="middle" font-size="7.5" font-weight="700">HAZARD IN THE ARRAY.</text>

  <!-- Caution multiple sources + directory -->
  <rect x="484" y="186" width="250" height="220" fill="#ffd100" stroke="#111" stroke-width="2"/>
  <text x="609" y="208" text-anchor="middle" font-size="12" font-weight="900">CAUTION !</text>
  <text x="609" y="224" text-anchor="middle" font-size="11" font-weight="900">MULTIPLE SOURCES OF POWER</text>
  <text x="494" y="242" font-size="7">POWER TO THIS BUILDING IS ALSO SUPPLIED FROM</text>
  <text x="494" y="254" font-size="7">THE FOLLOWING SOURCES WITH DISCONNECTS</text>
  <text x="494" y="266" font-size="7">LOCATED AS SHOWN:</text>
  <text x="494" y="284" font-size="7.5" font-weight="700">• (E) {main_a}A MAIN SERVICE / DISCO(S)</text>
  <text x="494" y="298" font-size="7.5" font-weight="700">• (N) {inv_name[:34]}</text>
  {"<text x='494' y='312' font-size='7.5' font-weight='700'>• " + bat_line + "</text>" if bat_line else ""}
  <text x="494" y="326" font-size="7.5" font-weight="700">• (N) {disco_a}A AC DISCONNECT (if used)</text>

  <!-- mini site map -->
  <rect x="520" y="340" width="180" height="50" fill="#fff" stroke="#111"/>
  <text x="610" y="356" text-anchor="middle" font-size="7" font-weight="700">SITE DIRECTORY (orient on site)</text>
  <rect x="560" y="362" width="40" height="22" fill="#e8f0ff" stroke="#111"/>
  <text x="580" y="376" text-anchor="middle" font-size="6">BLDG</text>
  <circle cx="545" cy="373" r="4" fill="#0b5c2e"/>
  <text x="552" y="376" font-size="5.5">MSP</text>
  <circle cx="650" cy="373" r="4" fill="#c41e3a"/>
  <text x="656" y="376" font-size="5.5">INV</text>
  <text x="610" y="400" text-anchor="middle" font-size="6" fill="#444">{street[:28]}</text>

  <text x="494" y="420" font-size="6.5" fill="#333">LOC: service equipment · NEC 690.56 / 705.10</text>
  <text x="494" y="432" font-size="6.5" fill="#333">Plaque correctly oriented to building</text>

  <!-- SOLAR PV DC CIRCUIT -->
  <rect x="484" y="420" width="250" height="36" fill="#fff" stroke="#c41e3a" stroke-width="2"/>
  <text x="609" y="442" text-anchor="middle" font-size="12" font-weight="900" fill="#c41e3a">SOLAR PV DC CIRCUIT</text>

  <rect x="484" y="466" width="250" height="50" fill="#fff" stroke="#111" stroke-width="1"/>
  <text x="494" y="484" font-size="7.5" font-weight="700">INSTALLER CHECKLIST</text>
  <text x="494" y="498" font-size="7">□ All labels permanent &amp; legible</text>
  <text x="494" y="510" font-size="7">□ RSD placard at service · switch labeled</text>

  <text x="8" y="610" font-size="7" fill="#555">Non-proprietary NEC wording · Colors: red/white (disco &amp; RSD switch), yellow/black (RSD placard &amp; multi-source), orange (dual source). See appendix label guide PDF.</text>
</svg>'''
