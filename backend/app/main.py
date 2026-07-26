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
    rec = storage.get_project(project_id)
    if not rec:
        raise HTTPException(404, "Project not found")
    html = render_planset_html(rec.project)
    path = storage.write_output(project_id, html)
    return {
        "project_id": project_id,
        "path": str(path),
        "url": f"/api/projects/{project_id}/planset",
        "warnings": compute_system(rec.project).warnings,
    }


@app.post("/api/generate")
def api_generate_ephemeral(project: ProjectInput):
    """Generate without saving — returns HTML directly for preview download."""
    html = render_planset_html(project)
    # also save under ephemeral id for file access
    rec = storage.save_project(project)
    path = storage.write_output(rec.id, html)
    return {
        "project_id": rec.id,
        "path": str(path),
        "url": f"/api/projects/{rec.id}/planset",
        "warnings": compute_system(project).warnings,
        "quality_flags": compute_system(project).quality_flags,
    }


@app.get("/api/projects/{project_id}/planset", response_class=HTMLResponse)
def api_planset_html(project_id: str):
    rec = storage.get_project(project_id)
    if not rec:
        raise HTTPException(404, "Project not found")
    # regenerate fresh each time so template updates apply
    html = render_planset_html(rec.project)
    storage.write_output(project_id, html)
    return HTMLResponse(html)


@app.get("/api/presets/duracell-400a")
def preset_duracell():
    """Seed example: Max Hybrid 15 on 400A dual 200A disco — half-home."""
    from .presets import duracell_400a_half_home

    return duracell_400a_half_home()


@app.get("/api/presets/eg4-gridboss")
def preset_eg4():
    from .presets import eg4_gridboss_sample

    return eg4_gridboss_sample()


# Frontend static last so API routes win
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")
