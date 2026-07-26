"""SLD intermediate representation — single source of truth for diagram + wire schedule.

Topology → IR → SVG (and later schemdraw / PDF).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .calcs import SystemTotals, compute_system
from .models import ProjectInput
from .sld import build_segments, generate_sld_svg


class NodeKind(str, Enum):
    UTILITY = "utility"
    METER = "meter"
    SERVICE = "service"
    DISCO = "disco"
    INVERTER = "inverter"
    PANEL = "panel"
    PV_ARRAY = "pv_array"
    BATTERY = "battery"
    RSD = "rsd"
    GROUND = "ground"


class EdgeKind(str, Enum):
    AC = "ac"
    PV_DC = "pv_dc"
    BAT_DC = "bat_dc"
    COMM = "comm"
    GROUND = "ground"


@dataclass
class SldNode:
    id: str
    kind: NodeKind
    label: str
    existing: bool = False
    rating: str = ""
    notes: str = ""


@dataclass
class SldEdge:
    id: str
    kind: EdgeKind
    source: str
    target: str
    conductors: str = ""
    ocpd: str = ""
    notes: str = ""


@dataclass
class SldIR:
    topology: str
    nodes: list[SldNode] = field(default_factory=list)
    edges: list[SldEdge] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    island_continuous_a: float = 0.0
    island_continuous_kw: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology": self.topology,
            "island_continuous_a": self.island_continuous_a,
            "island_continuous_kw": self.island_continuous_kw,
            "warnings": self.warnings,
            "nodes": [
                {
                    "id": n.id,
                    "kind": n.kind.value,
                    "label": n.label,
                    "existing": n.existing,
                    "rating": n.rating,
                    "notes": n.notes,
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "kind": e.kind.value,
                    "source": e.source,
                    "target": e.target,
                    "conductors": e.conductors,
                    "ocpd": e.ocpd,
                    "notes": e.notes,
                }
                for e in self.edges
            ],
        }


def _topology_name(project: ProjectInput) -> str:
    b = project.service.backup_mode.value
    ic = project.service.interconnection.value
    if ic == "backfeed_breaker" and b not in ("half_home", "full_dual_disco"):
        return "backfeed_breaker"
    if b == "full_dual_disco":
        return "full_dual_disco"
    if b == "critical_loads":
        return "critical_loads"
    if b == "half_home" or project.service.num_disconnects >= 2:
        return "half_home_dual_disco"
    if ic == "gridboss_mid":
        return "gridboss"
    return ic


def build_sld_ir(project: ProjectInput, totals: SystemTotals | None = None) -> SldIR:
    """Build IR from project + calcs; edges mirror conductor schedule."""
    totals = totals or compute_system(project)
    topo = _topology_name(project)
    inv = project.inverters[0] if project.inverters else None
    cont_a = (inv.continuous_ac_a * inv.quantity) if inv else totals.ac_a_continuous
    disco = project.service.disconnect_rating_a
    pass_a = inv.passthrough_a if inv and inv.passthrough_a else disco

    ir = SldIR(
        topology=topo,
        island_continuous_a=float(cont_a),
        island_continuous_kw=float(totals.ac_kw_continuous),
        warnings=list(totals.warnings),
    )

    # Core nodes (all topologies)
    ir.nodes.append(SldNode("utility", NodeKind.UTILITY, "UTILITY", existing=True, rating=project.service.voltage))
    ir.nodes.append(SldNode("meter", NodeKind.METER, "UTILITY METER", existing=True))
    ir.nodes.append(
        SldNode(
            "service",
            NodeKind.SERVICE,
            f"{project.service.service_a}A SERVICE",
            existing=True,
            rating=f"Main {project.service.main_breaker_a}A",
        )
    )

    if topo in ("half_home_dual_disco", "full_dual_disco", "critical_loads"):
        ir.nodes.append(
            SldNode("disco1", NodeKind.DISCO, f"{disco}A DISCO #1", existing=True, rating=f"{disco}A")
        )
        ir.nodes.append(
            SldNode("disco2", NodeKind.DISCO, f"{disco}A DISCO #2", existing=True, rating=f"{disco}A")
        )
        ir.nodes.append(
            SldNode(
                "inverter",
                NodeKind.INVERTER,
                f"{inv.manufacturer} {inv.model}" if inv else "HYBRID",
                rating=f"pass {pass_a}A · island {cont_a:.0f}A",
            )
        )
        load_label = "CRITICAL LOADS" if topo == "critical_loads" else "BACKED-UP PANEL #1"
        ir.nodes.append(SldNode("panel_bu", NodeKind.PANEL, load_label))
        ir.nodes.append(SldNode("panel2", NodeKind.PANEL, "PANEL #2 (non-BU)", existing=True))
        ir.edges.extend(
            [
                SldEdge("e_u_m", EdgeKind.AC, "utility", "meter"),
                SldEdge("e_m_s", EdgeKind.AC, "meter", "service"),
                SldEdge("e_s_d1", EdgeKind.AC, "service", "disco1"),
                SldEdge("e_s_d2", EdgeKind.AC, "service", "disco2"),
                SldEdge("e_d2_p2", EdgeKind.AC, "disco2", "panel2", notes="utility only"),
            ]
        )
    elif topo == "backfeed_breaker":
        ir.nodes.append(
            SldNode(
                "msp",
                NodeKind.PANEL,
                "MAIN SERVICE PANEL",
                existing=True,
                rating=f"Main {project.service.main_breaker_a}A",
            )
        )
        ir.nodes.append(
            SldNode(
                "inverter",
                NodeKind.INVERTER,
                f"{inv.manufacturer} {inv.model}" if inv else "INVERTER",
                rating=f"{cont_a:.0f}A cont",
            )
        )
        ir.edges.extend(
            [
                SldEdge("e_u_m", EdgeKind.AC, "utility", "meter"),
                SldEdge("e_m_msp", EdgeKind.AC, "meter", "msp"),
            ]
        )
    else:
        ir.nodes.append(
            SldNode(
                "inverter",
                NodeKind.INVERTER,
                f"{inv.manufacturer} {inv.model}" if inv else "INVERTER",
            )
        )
        ir.edges.append(SldEdge("e_u_m", EdgeKind.AC, "utility", "meter"))
        ir.edges.append(SldEdge("e_m_s", EdgeKind.AC, "meter", "service"))

    # PV / battery / RSD always if present
    ir.nodes.append(
        SldNode(
            "pv",
            NodeKind.PV_ARRAY,
            f"PV ARRAY {totals.dc_kw:.2f} kWDC",
            rating=f"{totals.module_count} modules",
        )
    )
    if totals.battery_kwh > 0:
        ir.nodes.append(
            SldNode("battery", NodeKind.BATTERY, f"BATTERY {totals.battery_kwh:.0f} kWh")
        )
    ir.nodes.append(SldNode("rsd", NodeKind.RSD, "RSD INITIATOR", notes="NEC 690.12"))
    ir.nodes.append(SldNode("ges", NodeKind.GROUND, "GEC / GES", notes="NEC 250"))

    # Attach schedule segments as edges (source of truth for conductors)
    for seg in build_segments(project, totals):
        kind = EdgeKind.AC
        if seg.tag.startswith("PV"):
            kind = EdgeKind.PV_DC
        elif seg.tag.startswith("BAT"):
            kind = EdgeKind.BAT_DC
        elif seg.tag == "GND":
            kind = EdgeKind.GROUND
        ir.edges.append(
            SldEdge(
                id=seg.tag,
                kind=kind,
                source=seg.from_eq,
                target=seg.to_eq,
                conductors=seg.conductors,
                ocpd=seg.ocpd,
                notes=seg.notes,
            )
        )

    if cont_a and disco and cont_a < disco * 0.5:
        ir.warnings.append(
            f"Island continuous ~{cont_a:.0f}A is far below {disco}A disco rating — load management required."
        )

    return ir


def render_sld_from_ir(project: ProjectInput, ir: SldIR | None = None) -> str:
    """Render SVG; currently delegates to existing generator (IR is source for schedule/API)."""
    totals = compute_system(project)
    if ir is None:
        ir = build_sld_ir(project, totals)
    # SVG path still uses battle-tested diagrams; IR drives JSON/CLI/tests
    return generate_sld_svg(project, totals)
