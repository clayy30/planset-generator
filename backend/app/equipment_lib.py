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

    # batteries — require brand alignment (don't attach EG4 PDF to Duracell job)
    for b in project.batteries:
        if b.quantity <= 0:
            continue
        bm = f"{b.manufacturer} {b.model}".lower()
        brand_ok = False
        if "eg4" in bm and "eg4" in fname:
            brand_ok = True
        if "duracell" in bm and "duracell" in fname:
            brand_ok = True
        if "ecoflow" in bm and "ecoflow" in fname:
            brand_ok = True
        if brand_ok and "wallmount" in fname:
            score += 8.0
            reasons.append("WallMount battery")
        if brand_ok and "powerpro" in fname:
            score += 8.0
            reasons.append("PowerPro battery")
        if brand_ok and ("battery" in fname or "ess" in fname):
            score += 5.0
        if "chargeverter" in bm and "chargeverter" in fname:
            score += 7.0

    # disconnect / GridBOSS — only if topology uses it
    if project.service.interconnection.value == "gridboss_mid":
        if "grid" in fname and "boss" in fname:
            score += 10.0
            reasons.append("GridBOSS")

    # skip customer PE letters by default unless structural category and score high
    if "pe letter" in fname or "bator" in fname:
        score = min(score, 1.0)
        reasons.append("customer PE example (low priority)")

    return score, "; ".join(reasons[:4])


def _part_slot(path: Path, cat: str) -> str:
    """One physical part type → one slot. Prevents 4× FlashFoot sheets."""
    n = path.name.lower()
    if cat == "modules":
        return "MODULE"
    if cat == "inverters":
        return "INVERTER"
    if cat == "batteries":
        if "chargeverter" in n:
            return "CHARGEVERTER"
        return "BATTERY"
    if cat == "disconnects":
        return "DISCONNECT"
    if cat == "labels":
        return "LABEL_GUIDE"
    if cat == "structural":
        if "engineering" in n or "design" in n:
            return "STRUCT_GUIDE"
        return "STRUCT_OTHER"
    if cat == "racking":
        if "flashfoot" in n:
            # Prefer cut sheet over install/tech brief
            return "ATTACHMENT_FOOT"
        if "xr100" in n or "xr-100" in n:
            if "boss" in n or "splice" in n:
                return "RAIL_SPLICE"
            return "RAIL"
        if "xr10" in n and "xr100" not in n:
            return "RAIL"  # same slot — one rail cut sheet only
        if "ufo" in n or "clamp" in n:
            return "CLAMP"
        if "halo" in n or "ultragrip" in n or "quickmount" in n:
            return "ALT_MOUNT"
        if "splice" in n:
            return "RAIL_SPLICE"
        return "RACKING_OTHER"
    return cat.upper()


def _slot_preference(path: Path, slot: str) -> float:
    """Within a slot, prefer cut sheets over manuals/briefs."""
    n = path.name.lower()
    bonus = 0.0
    if "cut_sheet" in n or "cut-sheet" in n or "datasheet" in n or "spec" in n:
        bonus += 3.0
    if "install" in n or "manual" in n:
        bonus -= 2.0
    if "tech_brief" in n or "brochure" in n:
        bonus -= 1.5
    if slot == "ATTACHMENT_FOOT" and "cut_sheet" in n and "flashfoot2" in n:
        bonus += 5.0  # lag bolt lives on this sheet
    if slot == "RAIL" and "xr100" in n and "us" in n:
        bonus += 1.0
    if slot == "RAIL" and "xr10" in n and "xr100" not in n:
        bonus -= 0.5  # prefer XR100 when both score
    if slot == "STRUCT_GUIDE" and "engineering" in n:
        bonus += 4.0
    if "pe letter" in n or "bator" in n:
        bonus -= 10.0
    return bonus


def match_equipment(project: ProjectInput, max_docs: int = 9) -> list[SpecDoc]:
    """Exactly one PDF per equipment section (module, inverter, foot, rail, …)."""
    blob = _project_blob(project)
    # score every file
    candidates: list[SpecDoc] = []
    for cat, path in _iter_pdfs() or []:
        base, reason = _score_doc(cat, path, blob, project)
        # Require a real project match before cut-sheet preference can promote a file
        if base < 3.5:
            continue
        slot = _part_slot(path, cat)
        score = base + _slot_preference(path, slot)
        candidates.append(
            SpecDoc(
                path=path,
                category=cat,
                title=_title_from_path(path),
                score=score,
                reason=(reason or cat) + f" · slot={slot}",
            )
        )

    # keep best score per slot
    by_slot: dict[str, SpecDoc] = {}
    for d in candidates:
        slot = _part_slot(d.path, d.category)
        if slot not in by_slot or d.score > by_slot[slot].score:
            by_slot[slot] = d

    # preferred order for appendix (one of each)
    order = [
        "MODULE",
        "INVERTER",
        "BATTERY",
        "DISCONNECT",
        "RAIL",
        "ATTACHMENT_FOOT",
        "CLAMP",
        "RAIL_SPLICE",
        "STRUCT_GUIDE",
        "LABEL_GUIDE",
        "CHARGEVERTER",
        "ALT_MOUNT",
    ]
    docs: list[SpecDoc] = []
    for slot in order:
        if slot in by_slot:
            docs.append(by_slot.pop(slot))
    # any remaining slots
    for slot, d in sorted(by_slot.items(), key=lambda kv: -kv[1].score):
        docs.append(d)
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
        # ONE page per equipment cut sheet (cleaner appendix)
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
