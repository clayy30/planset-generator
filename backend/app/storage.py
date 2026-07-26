"""JSON file storage for projects."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .models import ProjectInput, ProjectRecord

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "projects"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output"


def _ensure() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_projects() -> list[dict]:
    _ensure()
    rows = []
    for p in sorted(DATA_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(p.read_text())
            rows.append(
                {
                    "id": data["id"],
                    "project_name": data["project"]["meta"]["project_name"],
                    "customer_name": data["project"]["meta"]["customer_name"],
                    "updated_at": data["updated_at"],
                    "address": data["project"]["meta"]["address"].get("line1", ""),
                }
            )
        except Exception:
            continue
    return rows


def get_project(project_id: str) -> ProjectRecord | None:
    _ensure()
    path = DATA_DIR / f"{project_id}.json"
    if not path.exists():
        return None
    return ProjectRecord.model_validate_json(path.read_text())


def save_project(project: ProjectInput, project_id: str | None = None) -> ProjectRecord:
    _ensure()
    pid = project_id or str(uuid.uuid4())
    existing = get_project(pid) if project_id else None
    rec = ProjectRecord(
        id=pid,
        created_at=existing.created_at if existing else _now(),
        updated_at=_now(),
        project=project,
    )
    (DATA_DIR / f"{pid}.json").write_text(rec.model_dump_json(indent=2))
    return rec


def delete_project(project_id: str) -> bool:
    path = DATA_DIR / f"{project_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False


def write_output(project_id: str, html: str) -> Path:
    _ensure()
    path = OUTPUT_DIR / f"{project_id}_planset.html"
    path.write_text(html, encoding="utf-8")
    return path
