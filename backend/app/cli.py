"""CLI-first entry: python -m backend.app.cli …"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .calcs import compute_system, totals_to_dict
from .gis import lookup_address
from .models import ProjectInput
from .presets import duracell_400a_half_home, eg4_gridboss_sample
from .render import render_planset_html
from .sld_ir import build_sld_ir
from .storage import write_output


def _load_project(path: str | None, preset: str | None) -> ProjectInput:
    if preset:
        if preset in ("duracell", "duracell-400a"):
            return duracell_400a_half_home()
        if preset in ("eg4", "eg4-gridboss"):
            return eg4_gridboss_sample()
        raise SystemExit(f"Unknown preset: {preset}")
    if not path:
        raise SystemExit("Provide --project PATH or --preset NAME")
    data = json.loads(Path(path).read_text())
    return ProjectInput.model_validate(data)


def cmd_calc(args: argparse.Namespace) -> int:
    project = _load_project(args.project, args.preset)
    totals = compute_system(project)
    out = {
        "electrical": totals_to_dict(totals),
        "sld_ir": build_sld_ir(project, totals).to_dict(),
    }
    text = json.dumps(out, indent=2)
    if args.out:
        Path(args.out).write_text(text)
        print(f"Wrote {args.out}")
    else:
        print(text)
    if totals.warnings:
        print("WARNINGS:", file=sys.stderr)
        for w in totals.warnings:
            print(f"  - {w}", file=sys.stderr)
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    project = _load_project(args.project, args.preset)
    out_dir = Path(args.out or "output/cli")
    out_dir.mkdir(parents=True, exist_ok=True)
    project_id = args.id or out_dir.name
    html = render_planset_html(
        project,
        project_id=project_id,
        build_spec_appendix=not args.no_appendix,
    )
    path = out_dir / "planset.html"
    path.write_text(html, encoding="utf-8")
    # also register under storage output for API compatibility
    write_output(project_id, html)
    ir = build_sld_ir(project)
    (out_dir / "sld_ir.json").write_text(json.dumps(ir.to_dict(), indent=2))
    (out_dir / "project.json").write_text(project.model_dump_json(indent=2))
    print(f"Planset: {path}")
    print(f"SLD IR:  {out_dir / 'sld_ir.json'}")
    print(f"Sheets:  open in browser → Print → PDF (ANSI B 11×17)")
    if ir.warnings:
        print("Warnings:")
        for w in ir.warnings:
            print(f"  - {w}")
    return 0


def cmd_gis(args: argparse.Namespace) -> int:
    r = lookup_address(args.line1, args.city or "", args.state or "GA", args.zip or "")
    print(json.dumps(r.to_dict(), indent=2))
    return 0 if r.latitude is not None else 1


def cmd_preset(args: argparse.Namespace) -> int:
    p = _load_project(None, args.name)
    text = p.model_dump_json(indent=2)
    if args.out:
        Path(args.out).write_text(text)
        print(f"Wrote {args.out}")
    else:
        print(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="planset",
        description="Ultimate Planset Generator — CLI (AHJ solar + hybrid)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_calc = sub.add_parser("calc", help="Run electrical + SLD IR calcs (JSON)")
    p_calc.add_argument("--project", "-p", help="Project JSON path")
    p_calc.add_argument("--preset", choices=["duracell", "duracell-400a", "eg4", "eg4-gridboss"])
    p_calc.add_argument("--out", "-o", help="Write JSON to file")
    p_calc.set_defaults(func=cmd_calc)

    p_gen = sub.add_parser("generate", help="Generate multi-sheet HTML planset")
    p_gen.add_argument("--project", "-p", help="Project JSON path")
    p_gen.add_argument("--preset", choices=["duracell", "duracell-400a", "eg4", "eg4-gridboss"])
    p_gen.add_argument("--out", "-o", default="output/cli", help="Output directory")
    p_gen.add_argument("--id", help="Project id for appendix folder")
    p_gen.add_argument("--no-appendix", action="store_true", help="Skip cut-sheet rasters")
    p_gen.set_defaults(func=cmd_generate)

    p_gis = sub.add_parser("gis", help="Geocode + parcel lookup")
    p_gis.add_argument("line1", help="Street address")
    p_gis.add_argument("--city", default="")
    p_gis.add_argument("--state", default="GA")
    p_gis.add_argument("--zip", default="")
    p_gis.set_defaults(func=cmd_gis)

    p_pre = sub.add_parser("preset", help="Dump a built-in preset as JSON")
    p_pre.add_argument("name", choices=["duracell", "duracell-400a", "eg4", "eg4-gridboss"])
    p_pre.add_argument("--out", "-o")
    p_pre.set_defaults(func=cmd_preset)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
