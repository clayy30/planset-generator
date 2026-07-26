"""Match local equipment PDFs to a project and prepare appendix packages.

Scans data/equipment/{modules,inverters,batteries,racking,disconnects,structural,labels}
and selects cut sheets relevant to the project's gear + always-on structural/label packs.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .models import ProjectInput

EQUIP_ROOT = Path(__file__).resolve().parents[2] / "data" / "equipment"

# category → keyword patterns for filename + path matching
CATEGORY_HINTS: dict[str, list[str]] = {
    "modules": [
        r"canadian", r"cs6\.1", r"cs7n", r"tophiku", r"qcell", r"q\.peak",
        r"ja.?440", r"seg440", r"trina", r"longi", r"renogy", r"module",
    ],
    "inverters": [
        r"dpc.?max|max.?hybrid.?15|duracell", r"flexboss", r"18kpv", r"12kpv",
        r"12000xp", r"ecoflow", r"enphase", r"iq8", r"sol.?ark|solark",
        r"cps.?sca", r"apower", r"powerwall", r"microinverter", r"inverter",
    ],
    "batteries": [
        r"wallmount", r"powerpro", r"battery", r"chargeverter", r"evault",
        r"ocean.?pro.?battery", r"ess",
    ],
    "racking": [
        r"ironridge", r"flashfoot", r"xr10", r"xr.?100", r"ufo", r"halo",
        r"quickmount", r"unirac", r"chiko", r"rail", r"splice", r"clamp",
    ],
    "disconnects": [
        r"grid.?boss|gridboss", r"disconnect", r"ac.?disco",
    ],
    "structural": [
        r"engineering.?design.?guide", r"span", r"structural", r"pe.?letter",
        r"load", r"asce",
    ],
    "labels": [
        r"label", r"placard", r"sticker", r"690", r"rapid.?shutdown",
    ],
}


@dataclass
class SpecDoc:
    path: Path
    category: str
    title: str
    score: float = 0.0
    reason: str = ""


@dataclass
class AppendixPackage:
    docs: list[SpecDoc] = field(default_factory=list)
    output_dir: Path | None = None
    page_images: list[tuple[SpecDoc, list[Path]]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _iter_pdfs() -> Iterable[tuple[str, Path]]:
    if not EQUIP_ROOT.exists():
        return
    for cat_dir in EQUIP_ROOT.iterdir():
        if not cat_dir.is_dir():
            continue
        cat = cat_dir.name.lower()
        for p in cat_dir.rglob("*.pdf"):
            # skip huge catalogs in matching unless explicitly needed
            if p.stat().st_size > 8_000_000 and "parts_catalog" in p.name.lower():
                continue
            yield cat, p


def _title_from_path(p: Path) -> str:
    name = p.stem
    name = re.sub(r"[_\-]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:90]


def _project_blob(project: ProjectInput) -> str:
    parts: list[str] = []
    for m in project.modules:
        parts += [m.manufacturer, m.model]
    for i in project.inverters:
        parts += [i.manufacturer, i.model, i.listing]
    for b in project.batteries:
        parts += [b.manufacturer, b.model]
    parts += [
        project.array.racking,
        project.array.attachment,
        project.array.structural.racking_mfr,
        project.array.structural.rail_model,
        project.array.structural.attachment_hardware,
        project.array.structural.lag_size,
        project.service.interconnection.value,
        project.service.backup_mode.value,
    ]
    return " ".join(parts).lower()


def _score_doc(cat: str, path: Path, blob: str, project: ProjectInput) -> tuple[float, str]:
    fname = path.name.lower()
    score = 0.0
    reasons: list[str] = []

    # category baseline
    if cat in ("racking", "structural", "labels") and any(
        k in blob for k in ("ironridge", "xr", "flash", "rail", "rack")
    ):
        score += 1.0
        reasons.append("racking system in project")

    # always include core structural pack when IronRidge
    if cat == "structural" and "engineering" in fname:
        score += 5.0
        reasons.append("engineering design guide")
    if cat == "labels":
        score += 4.0
        reasons.append("label guide always attached")

    # racking cut sheets
    if "flashfoot2" in fname or "flashfoot_2" in fname:
        if "flashfoot" in blob or "ironridge" in blob or "flash" in blob:
            score += 8.0
            reasons.append("FlashFoot2 matches attachment")
        else:
            score += 3.0
    if "xr100" in fname or "xr-100" in fname:
        if "xr-100" in blob or "xr100" in blob or "ironridge" in blob:
            score += 7.0
            reasons.append("XR100 rail")
    if "xr10" in fname and "xr100" not in fname:
        if "xr10" in blob or "xr-10" in blob or "ironridge" in blob:
            score += 6.0
            reasons.append("XR10 rail")
    if "ufo" in fname:
        score += 5.0 if "ironridge" in blob else 2.0
        reasons.append("UFO clamp")
    if "halo" in fname or "ultragrip" in fname:
        score += 4.0 if "ironridge" in blob else 1.5
    if "install" in fname and "flashfoot" in fname:
        score += 4.0 if "ironridge" in blob else 1.0
    if "boss" in fname and "splice" in fname:
        score += 3.0 if "ironridge" in blob else 1.0

    # modules
    for m in project.modules:
        tokens = re.findall(r"[a-z0-9\.]+", f"{m.manufacturer} {m.model}".lower())
        for t in tokens:
            if len(t) < 3:
                continue
            if t in fname or t.replace(".", "") in fname:
                score += 6.0
                reasons.append(f"module token {t}")
                break
        if "canadian" in m.manufacturer.lower() and "canadian" in fname:
            score += 5.0
            reasons.append("Canadian Solar")
        if "cs6.1" in m.model.lower() and "cs6.1" in fname:
            score += 8.0
            reasons.append("CS6.1 exact")
        if "qcell" in m.manufacturer.lower() and "qcell" in fname:
            score += 5.0

    # inverters
    for inv in project.inverters:
        manuf = inv.manufacturer.lower()
        model = inv.model.lower()
        if "duracell" in manuf or "max hybrid" in model or "dpc" in manuf:
            if "dpc" in fname or "hybrid" in fname and "15" in fname:
                score += 10.0
                reasons.append("Duracell Max Hybrid 15")
        if "flexboss" in model and "flexboss" in fname:
            score += 10.0
            reasons.append("FlexBoss")
        if "18kpv" in model.replace(" ", "").lower() and "18kpv" in fname.replace(" ", ""):
            score += 10.0
            reasons.append("18kPV")
        if "12000xp" in model.replace(" ", "").lower() and "12000xp" in fname:
            score += 10.0
        if "ecoflow" in manuf and "ecoflow" in fname:
            score += 8.0
        if "enphase" in manuf and "enphase" in fname or "iq8" in fname:
            score += 6.0
        if "eg4" in manuf and "eg4" in fname:
            score += 3.0

    # batteries
    for b in project.batteries:
        if b.quantity <= 0:
            continue
        bm = f"{b.manufacturer} {b.model}".lower()
        if "wallmount" in bm and "wallmount" in fname:
            score += 8.0
            reasons.append("WallMount battery")
        if "powerpro" in bm and "powerpro" in fname:
            score += 8.0
        if "eg4" in bm and "eg4" in fname and "battery" in fname:
            score += 4.0
        if "chargeverter" in bm and "chargeverter" in fname:
            score += 7.0

    # disconnect / GridBOSS
    if project.service.interconnection.value == "gridboss_mid" or "gridboss" in blob:
        if "grid" in fname and "boss" in fname:
            score += 10.0
            reasons.append("GridBOSS")

    # skip customer PE letters by default unless structural category and score high
    if "pe letter" in fname or "bator" in fname:
        score = min(score, 1.0)
        reasons.append("customer PE example (low priority)")

    return score, "; ".join(reasons[:4])


def match_equipment(project: ProjectInput, max_docs: int = 14) -> list[SpecDoc]:
    blob = _project_blob(project)
    scored: list[SpecDoc] = []
    for cat, path in _iter_pdfs() or []:
        score, reason = _score_doc(cat, path, blob, project)
        if score < 3.5:
            continue
        scored.append(
            SpecDoc(
                path=path,
                category=cat,
                title=_title_from_path(path),
                score=score,
                reason=reason or cat,
            )
        )
    scored.sort(key=lambda d: (-d.score, d.category, d.title))

    # de-dupe near-identical names, keep best score
    best: dict[str, SpecDoc] = {}
    for d in scored:
        key = re.sub(r"\s+", "", d.title.lower())[:50]
        if key not in best or d.score > best[key].score:
            best[key] = d
    docs = sorted(best.values(), key=lambda d: (-d.score, d.category))
    return docs[:max_docs]


def render_pdf_pages(
    pdf: Path,
    out_dir: Path,
    prefix: str,
    max_pages: int = 2,
    dpi: int = 110,
) -> list[Path]:
    """Rasterize first pages of a PDF for embedding in the planset HTML."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = out_dir / prefix
    try:
        subprocess.run(
            [
                "pdftoppm",
                "-f",
                "1",
                "-l",
                str(max_pages),
                "-r",
                str(dpi),
                "-png",
                str(pdf),
                str(stem),
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return []
    return sorted(out_dir.glob(f"{prefix}-*.png"))


def build_appendix(
    project: ProjectInput,
    project_id: str,
    output_root: Path | None = None,
) -> AppendixPackage:
    from . import storage

    root = output_root or storage.OUTPUT_DIR
    out = root / project_id / "appendix"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    docs = match_equipment(project)
    pkg = AppendixPackage(docs=docs, output_dir=out)

    if not docs:
        pkg.warnings.append("No matching equipment PDFs found under data/equipment/")
        return pkg

    for i, doc in enumerate(docs, start=1):
        dest = out / f"{i:02d}_{doc.category}_{doc.path.name}"
        try:
            shutil.copy2(doc.path, dest)
        except OSError as e:
            pkg.warnings.append(f"Copy failed {doc.path.name}: {e}")
            continue
        # more pages for cut sheets (short), fewer for long manuals
        max_p = 1 if doc.path.stat().st_size > 2_000_000 else 2
        if "engineering" in doc.path.name.lower():
            max_p = 2
        if "label" in doc.category:
            max_p = 1
        imgs = render_pdf_pages(dest, out / "pages", f"doc{i:02d}", max_pages=max_p)
        if imgs:
            pkg.page_images.append((doc, imgs))
        else:
            pkg.warnings.append(f"Could not rasterize {doc.path.name} (pdftoppm?)")

    # index markdown
    lines = ["# Equipment appendix index", ""]
    for i, d in enumerate(docs, 1):
        lines.append(f"{i}. **{d.title}** (`{d.category}`) — {d.reason}")
        lines.append(f"   - source: `{d.path}`")
    (out / "INDEX.md").write_text("\n".join(lines) + "\n")
    return pkg


def appendix_to_dict(pkg: AppendixPackage) -> dict:
    return {
        "count": len(pkg.docs),
        "docs": [
            {
                "title": d.title,
                "category": d.category,
                "score": d.score,
                "reason": d.reason,
                "filename": d.path.name,
            }
            for d in pkg.docs
        ],
        "warnings": pkg.warnings,
        "output_dir": str(pkg.output_dir) if pkg.output_dir else None,
    }
