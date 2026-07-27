"""Planset Generator API — quality above permit-mill CAD exports."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .calcs import compute_system, totals_to_dict
from .models import ProjectInput
from .render import render_planset_html
from . import storage

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"

app = FastAPI(
    title="Planset Generator",
    description="Permit-grade PV / hybrid ESS planset engine — calculations with work shown, hybrid topologies, QA sheet.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "planset-generator",
        "commitment": "Plansets shall exceed Solar-Permit-Solutions-style boilerplate: formula work, hybrid awareness, QA gate.",
    }


@app.get("/api/projects")
def api_list():
    return storage.list_projects()


@app.post("/api/projects")
def api_create(project: ProjectInput):
    rec = storage.save_project(project)
    return rec


@app.get("/api/projects/{project_id}")
def api_get(project_id: str):
    rec = storage.get_project(project_id)
    if not rec:
        raise HTTPException(404, "Project not found")
    return rec


@app.put("/api/projects/{project_id}")
def api_update(project_id: str, project: ProjectInput):
    if not storage.get_project(project_id):
        raise HTTPException(404, "Project not found")
    return storage.save_project(project, project_id=project_id)


@app.delete("/api/projects/{project_id}")
def api_delete(project_id: str):
    if not storage.delete_project(project_id):
        raise HTTPException(404, "Project not found")
    return {"deleted": project_id}


@app.post("/api/preview-calcs")
def api_preview_calcs(project: ProjectInput):
    from .layout import compute_structural, structural_to_dict

    totals = compute_system(project)
    structural = compute_structural(project)
    return {
        "electrical": totals_to_dict(totals),
        "structural": structural_to_dict(structural),
    }


@app.post("/api/projects/{project_id}/generate")
def api_generate(project_id: str):
    from .equipment_lib import appendix_to_dict, build_appendix

    rec = storage.get_project(project_id)
    if not rec:
        raise HTTPException(404, "Project not found")
    html = render_planset_html(rec.project, project_id=project_id, build_spec_appendix=True)
    path = storage.write_output(project_id, html)
    pkg = build_appendix(rec.project, project_id)  # ensure package on disk
    return {
        "project_id": project_id,
        "path": str(path),
        "url": f"/api/projects/{project_id}/planset",
        "warnings": compute_system(rec.project).warnings,
        "appendix": appendix_to_dict(pkg),
    }


@app.post("/api/generate")
def api_generate_ephemeral(project: ProjectInput):
    """Save project, generate planset + matched equipment appendix."""
    from .equipment_lib import appendix_to_dict, build_appendix

    rec = storage.save_project(project)
    html = render_planset_html(rec.project, project_id=rec.id, build_spec_appendix=True)
    path = storage.write_output(rec.id, html)
    pkg = build_appendix(rec.project, rec.id)
    totals = compute_system(project)
    return {
        "project_id": rec.id,
        "path": str(path),
        "url": f"/api/projects/{rec.id}/planset",
        "warnings": totals.warnings,
        "quality_flags": totals.quality_flags,
        "appendix": appendix_to_dict(pkg),
    }


@app.get("/api/projects/{project_id}/planset", response_class=HTMLResponse)
def api_planset_html(project_id: str):
    rec = storage.get_project(project_id)
    if not rec:
        raise HTTPException(404, "Project not found")
    html = render_planset_html(rec.project, project_id=project_id, build_spec_appendix=True)
    storage.write_output(project_id, html)
    return HTMLResponse(html)


@app.get("/api/projects/{project_id}/appendix")
def api_appendix(project_id: str):
    from .equipment_lib import appendix_to_dict, build_appendix

    rec = storage.get_project(project_id)
    if not rec:
        raise HTTPException(404, "Project not found")
    pkg = build_appendix(rec.project, project_id)
    return appendix_to_dict(pkg)


@app.post("/api/preview-equipment")
def api_preview_equipment(project: ProjectInput):
    from .equipment_lib import appendix_to_dict, match_equipment

    docs = match_equipment(project)
    return {
        "count": len(docs),
        "docs": [
            {
                "title": d.title,
                "category": d.category,
                "score": d.score,
                "reason": d.reason,
                "filename": d.path.name,
            }
            for d in docs
        ],
    }


@app.get("/api/gis/lookup")
def api_gis_lookup(
    line1: str,
    city: str = "",
    state: str = "GA",
    zip: str = "",
):
    """Geocode + parcel PIN lookup for title block (public endpoints)."""
    from .gis import lookup_address

    result = lookup_address(line1=line1, city=city, state=state, zip_code=zip)
    return result.to_dict()


@app.post("/api/gis/enrich")
def api_gis_enrich(project: ProjectInput):
    """Fill project address/APN/coords/owner from GIS using current address."""
    from .gis import apply_to_project_dict, lookup_address

    a = project.meta.address
    parcel = lookup_address(a.line1, a.city, a.state, a.zip)
    data = project.model_dump()
    apply_to_project_dict(data, parcel)
    enriched = ProjectInput.model_validate(data)
    return {
        "project": enriched,
        "parcel": parcel.to_dict(),
    }


@app.get("/api/presets/duracell-400a")
def preset_duracell():
    """Seed example: Max Hybrid 15 on 400A dual 200A disco — half-home."""
    from .presets import duracell_400a_half_home

    return duracell_400a_half_home()


@app.get("/api/presets/eg4-gridboss")
def preset_eg4():
    from .presets import eg4_gridboss_sample

    return eg4_gridboss_sample()


@app.post("/api/import/lumen")
def api_import_lumen(payload: dict):
    """Import a Lumen Proposal Studio project → create planset project + optional generate.

    Body: raw ProposalProject JSON, or { "project": ProposalProject, "generate": true }
    """
    from .lumen_bridge import lumen_to_project_input

    generate = True
    body = payload
    if isinstance(payload, dict) and "project" in payload and (
        "primaryContact" in (payload.get("project") or {})
        or "systems" in (payload.get("project") or {})
    ):
        body = payload["project"]
        generate = bool(payload.get("generate", True))
    elif isinstance(payload, dict) and "generate" in payload and "systems" in payload:
        generate = bool(payload.get("generate", True))
        body = {k: v for k, v in payload.items() if k != "generate"}

    try:
        project = lumen_to_project_input(body)
    except Exception as e:
        raise HTTPException(400, f"Import mapping failed: {e}") from e

    rec = storage.save_project(project)
    result = {
        "ok": True,
        "project_id": rec.id,
        "customer": rec.project.meta.customer_name,
        "address": rec.project.meta.address.line1,
        "url_open": f"/?project={rec.id}",
        "url_api": f"/api/projects/{rec.id}",
        "url_planset": f"/api/projects/{rec.id}/planset",
        "warnings": [],
    }

    if generate:
        from .equipment_lib import appendix_to_dict, build_appendix

        html = render_planset_html(rec.project, project_id=rec.id, build_spec_appendix=True)
        path = storage.write_output(rec.id, html)
        pkg = build_appendix(rec.project, rec.id)
        totals = compute_system(rec.project)
        result.update(
            {
                "generated": True,
                "path": str(path),
                "url_planset": f"/api/projects/{rec.id}/planset",
                "warnings": totals.warnings,
                "quality_flags": totals.quality_flags,
                "appendix": appendix_to_dict(pkg),
            }
        )
    else:
        result["generated"] = False

    return result


@app.get("/api/bridge/info")
def api_bridge_info():
    return {
        "ok": True,
        "lumen_import": "/api/import/lumen",
        "method": "POST",
        "accepts": "Lumen ProposalProject JSON",
        "returns": "planset project_id + planset HTML URL",
        "materials": "/api/materials",
        "cors": "open for local studio integration",
    }


@app.get("/api/materials")
def api_materials():
    """Full approved materials catalog for dropdowns (modules, inverters, batteries, racking)."""
    from .materials_catalog import catalog_payload

    return catalog_payload()


@app.get("/api/materials/{category}")
def api_materials_category(category: str):
    from .materials_catalog import catalog_payload

    data = catalog_payload()
    key = category.lower().strip()
    if key not in data or key in ("version", "note"):
        raise HTTPException(404, f"Unknown category: {category}")
    return {"category": key, "items": data[key]}


# Frontend static last so API routes win
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")
