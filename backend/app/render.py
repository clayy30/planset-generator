"""Render multi-sheet ANSI B plansets as self-contained HTML (print → PDF)."""

from __future__ import annotations

import base64
from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from .calcs import compute_system, totals_to_dict
from .equipment_lib import AppendixPackage, appendix_to_dict, build_appendix, match_equipment
from .layout import compute_structural, structural_to_dict
from .models import ProjectInput, WireSegment
from .labels_page import generate_labels_svg
from .sld import generate_sld_svg, segments_as_wires

TEMPLATES = Path(__file__).parent / "templates"


def _img_data_uri(path: Path) -> str:
    raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def build_context(
    project: ProjectInput,
    appendix: AppendixPackage | None = None,
) -> dict[str, Any]:
    totals = compute_system(project)
    structural = compute_structural(project)
    matched = appendix.docs if appendix else match_equipment(project)
    sld_svg = generate_sld_svg(project, totals)
    labels_svg = generate_labels_svg(project, totals)
    # Prefer explicit project wires; else auto from SLD schedule
    wire_rows = project.wires
    if not wire_rows:
        wire_rows = [
            WireSegment(
                name=w["name"],
                from_equip=w["from_equip"],
                to_equip=w["to_equip"],
                conductors=w["conductors"],
                ocpd=w["ocpd"],
                notes=w["notes"],
            )
            for w in segments_as_wires(project, totals)
        ]
    meta = project.meta
    addr = meta.address
    full_address = ", ".join(
        x
        for x in [
            addr.line1,
            addr.line2,
            f"{addr.city}, {addr.state} {addr.zip}",
        ]
        if x
    )
    modules_summary = [
        f"(N) {m.quantity} — {m.manufacturer} {m.model} ({m.pmax_w:.0f}W)"
        for m in project.modules
    ]
    inv_summary = [
        f"(N) {i.quantity} — {i.manufacturer} {i.model} ({i.continuous_ac_w/1000:.1f} kWac cont.)"
        for i in project.inverters
    ]
    bat_summary = [
        f"(N) {b.quantity} — {b.manufacturer} {b.model} ({b.usable_kwh:.1f} kWh ea.)"
        for b in project.batteries
        if b.quantity
    ]
    service_lines = [
        f"Service: {project.service.service_a}A {project.service.phase} {project.service.voltage}",
        f"Main breaker: {project.service.main_breaker_a}A"
        + (
            f" · Bus: {project.service.busbar_a}A"
            if project.service.busbar_a
            else ""
        ),
        f"Disconnects: {project.service.num_disconnects} × {project.service.disconnect_rating_a}A",
        f"Interconnection: {project.service.interconnection.value.replace('_', ' ')}",
        f"Backup mode: {project.service.backup_mode.value.replace('_', ' ')}",
    ]

    default_construction = project.notes_construction or [
        "A ladder shall be in place for inspection of roof-mounted equipment.",
        "PV modules are non-combustible. System is utility interactive per UL 1741 listing of inverter(s).",
        "Grounding electrode system per NEC 250 and 690.47. Existing electrodes may be used if adequate; otherwise install supplemental 8 ft ground rod with listed clamp.",
        "Exposed non–current-carrying metal parts grounded per NEC 250.134 / 250.136(A).",
        "Working clearances per NEC 110.26 around all new and existing electrical equipment.",
        "All signage installed per NEC Articles 690, 705, 706 and AHJ requirements. Labels permanent, not handwritten.",
        "Installer to verify all dimensions and roof structure on site. Drawings not necessarily to scale unless noted.",
        "Exterior raceways painted to match adjacent surfaces where required by HOA/AHJ.",
        "Roof penetrations flashed and sealed per racking manufacturer and roofing best practice.",
    ]
    default_electrical = project.notes_electrical or [
        "All equipment listed by UL or other NRTL and labeled for the application.",
        "Conductors copper unless noted, 600 V, 90°C insulation / 75°C terminations as applicable.",
        "Rooftop wiring routed toward ridge/hip/valley per NEC 690.31 where applicable.",
        "Junction boxes, raceways, and supports sized and listed for the environment (NEMA 3R outdoor).",
        "Wire terminations labeled and torque per manufacturer.",
        "Module grounding clips / WEEB or equivalent per racking listing.",
        "Rapid shutdown per NEC 690.12 when required for the array type.",
        "Energy storage installed per NEC 706 and manufacturer ESS instructions.",
    ]

    sheets = [
        {"id": "PV-0", "name": "Cover Sheet"},
        {"id": "PV-1", "name": "Site & Project Data"},
        {"id": "PV-2", "name": "Roof Plan with Modules"},
        {"id": "PV-2A", "name": "Attachment / Structural"},
        {"id": "PV-3", "name": "Single-Line Diagram"},
        {"id": "PV-4", "name": "Electrical Calculations"},
        {"id": "PV-5", "name": "Wire Schedule & BOM"},
        {"id": "PV-6", "name": "Labels & Placards"},
        {"id": "PV-7", "name": "QA / AHJ Checklist"},
        {"id": "PV-8", "name": "Equipment Spec Appendix Index"},
    ]
    # one sheet id per rasterized page
    appendix_pages: list[dict[str, Any]] = []
    if appendix and appendix.page_images:
        n = 0
        for doc, imgs in appendix.page_images:
            for pi, img in enumerate(imgs, start=1):
                n += 1
                sid = f"PV-A{n}"
                sheets.append({"id": sid, "name": f"Spec: {doc.title[:40]}"})
                appendix_pages.append(
                    {
                        "id": sid,
                        "title": doc.title,
                        "category": doc.category,
                        "reason": doc.reason,
                        "page": pi,
                        "pages": len(imgs),
                        "filename": doc.path.name,
                        "img_uri": _img_data_uri(img),
                    }
                )

    return {
        "project": project,
        "meta": meta,
        "addr": addr,
        "full_address": full_address,
        "criteria": project.criteria,
        "service": project.service,
        "modules": project.modules,
        "inverters": project.inverters,
        "batteries": project.batteries,
        "array": project.array,
        "wires": wire_rows,
        "sld_svg": sld_svg,
        "labels_svg": labels_svg,
        "critical_loads": project.critical_loads,
        "totals": totals,
        "t": totals_to_dict(totals),
        "structural": structural,
        "st": structural_to_dict(structural),
        "matched_specs": matched,
        "appendix_pages": appendix_pages,
        "appendix_meta": appendix_to_dict(appendix) if appendix else {"count": len(matched), "docs": [], "warnings": []},
        "modules_summary": modules_summary,
        "inv_summary": inv_summary,
        "bat_summary": bat_summary,
        "service_lines": service_lines,
        "notes_construction": default_construction,
        "notes_electrical": default_electrical,
        "calc_engine": next(
            (n for n in totals.continuous_factor_notes if n.startswith("Calc engine")),
            "planset calc engine",
        ),
        "sheets": sheets,
        "custom_title": project.custom_title,
        "generated": date.today().isoformat(),
        "prepared_date": meta.prepared_date or date.today().isoformat(),
    }


def render_planset_html(
    project: ProjectInput,
    project_id: str | None = None,
    build_spec_appendix: bool = True,
) -> str:
    env = _env()
    tmpl = env.get_template("planset.html")
    appendix = None
    if build_spec_appendix and project_id:
        appendix = build_appendix(project, project_id)
    elif build_spec_appendix:
        # ephemeral id for preview packages
        import uuid

        appendix = build_appendix(project, str(uuid.uuid4())[:8])
    ctx = build_context(project, appendix=appendix)
    # SVG must not be HTML-escaped
    ctx["svg_roof"] = Markup(ctx["structural"].svg_roof)
    ctx["svg_attachment"] = Markup(ctx["structural"].svg_attachment)
    ctx["svg_sld"] = Markup(ctx["sld_svg"])
    ctx["svg_labels"] = Markup(ctx["labels_svg"])
    return tmpl.render(**ctx)
