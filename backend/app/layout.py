"""Roof plane geometry + module placement engine.

This is the gap vs Solar Permit Solutions plans: they draw modules on a roof.
We generate a dimensioned plan with fire setbacks, module grid, coverage %,
and racking attachment counts — from measured plane inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import ModuleSpec, ProjectInput, RoofPlane, StructuralSystem


IN2_FT = 12.0
IN2_SF = 144.0


@dataclass
class PlacedModule:
    index: int  # 1-based on plane
    global_index: int
    row: int
    col: int
    x_in: float  # from plane origin (left rake + setback)
    y_in: float  # from eave toward ridge
    w_in: float
    h_in: float
    portrait: bool


@dataclass
class PlaneLayout:
    plane: RoofPlane
    module: ModuleSpec
    usable_w_in: float
    usable_h_in: float
    cols: int
    rows: int
    placed: list[PlacedModule]
    requested: int
    fit_count: int
    array_area_sf: float
    roof_area_sf: float
    coverage_pct: float
    gap_in: float
    portrait: bool
    warnings: list[str] = field(default_factory=list)

    @property
    def shortfall(self) -> int:
        return max(0, self.requested - self.fit_count)


@dataclass
class AttachmentBOM:
    rails: int
    mid_clamps: int
    end_clamps: int
    attachments: int  # flashfeet / lags
    splices: int
    grounding_lugs: int
    rail_length_ft_each: float
    attachment_spacing_in: float
    notes: list[str] = field(default_factory=list)


@dataclass
class StructuralTotals:
    planes: list[PlaneLayout]
    bom: AttachmentBOM
    module_weight_lb: float
    array_dead_load_psf: float
    unit_weight_psf: float
    total_array_sf: float
    total_roof_sf: float
    coverage_pct: float
    dead_load_ok: bool
    warnings: list[str]
    svg_roof: str
    svg_attachment: str


def _primary_module(project: ProjectInput) -> ModuleSpec:
    return project.modules[0]


def _module_footprint(mod: ModuleSpec, portrait: bool) -> tuple[float, float]:
    """Return (width along eave, height toward ridge) in inches."""
    # Module length is long side, width is short side typically
    long_in, short_in = mod.length_in, mod.width_in
    if portrait:
        # short side along eave (narrow face to ridge direction)
        return short_in, long_in
    return long_in, short_in


def place_modules_on_plane(
    plane: RoofPlane,
    mod: ModuleSpec,
    start_global: int = 1,
    gap_in: float = 0.5,
) -> PlaneLayout:
    warnings: list[str] = []
    roof_w = plane.eave_width_ft * IN2_FT
    roof_h = plane.ridge_depth_ft * IN2_FT  # plan depth eave→ridge

    usable_w = roof_w - plane.setback_left_in - plane.setback_right_in
    usable_h = roof_h - plane.setback_eave_in - plane.setback_ridge_in

    if usable_w <= 0 or usable_h <= 0:
        warnings.append(f"{plane.name}: setbacks exceed roof dimensions — no usable area.")
        return PlaneLayout(
            plane=plane,
            module=mod,
            usable_w_in=max(0, usable_w),
            usable_h_in=max(0, usable_h),
            cols=0,
            rows=0,
            placed=[],
            requested=plane.module_count,
            fit_count=0,
            array_area_sf=0,
            roof_area_sf=plane.plan_area_sf,
            coverage_pct=0,
            gap_in=gap_in,
            portrait=plane.portrait,
            warnings=warnings,
        )

    mw, mh = _module_footprint(mod, plane.portrait)
    # how many fit
    cols = int((usable_w + gap_in) // (mw + gap_in)) if mw > 0 else 0
    rows = int((usable_h + gap_in) // (mh + gap_in)) if mh > 0 else 0
    capacity = cols * rows

    n = min(plane.module_count, capacity)
    if plane.module_count > capacity:
        warnings.append(
            f"{plane.name}: requested {plane.module_count} modules, "
            f"only {capacity} fit in usable area ({usable_w/12:.1f}' × {usable_h/12:.1f}') "
            f"with setbacks ridge={plane.setback_ridge_in}\", eave={plane.setback_eave_in}\"."
        )

    placed: list[PlacedModule] = []
    gi = start_global
    # pack row-major from eave (bottom) upward, left to right
    for i in range(n):
        r = i // cols if cols else 0
        c = i % cols if cols else 0
        x = plane.setback_left_in + c * (mw + gap_in)
        y = plane.setback_eave_in + r * (mh + gap_in)
        placed.append(
            PlacedModule(
                index=i + 1,
                global_index=gi,
                row=r,
                col=c,
                x_in=x,
                y_in=y,
                w_in=mw,
                h_in=mh,
                portrait=plane.portrait,
            )
        )
        gi += 1

    array_sf = n * (mod.length_in * mod.width_in) / IN2_SF
    roof_sf = plane.plan_area_sf
    cov = (100.0 * array_sf / roof_sf) if roof_sf > 0 else 0.0

    return PlaneLayout(
        plane=plane,
        module=mod,
        usable_w_in=usable_w,
        usable_h_in=usable_h,
        cols=cols,
        rows=rows,
        placed=placed,
        requested=plane.module_count,
        fit_count=n,
        array_area_sf=array_sf,
        roof_area_sf=roof_sf,
        coverage_pct=cov,
        gap_in=gap_in,
        portrait=plane.portrait,
        warnings=warnings,
    )


def compute_attachment_bom(
    layouts: list[PlaneLayout],
    struct: StructuralSystem,
    rafter_spacing_in: float,
) -> AttachmentBOM:
    """Estimate racking BOM from placed modules and attachment spacing rules."""
    notes: list[str] = []
    # Attachment spacing: max of rafter spacing and design max (e.g. 48")
    att_space = max(rafter_spacing_in, 1.0)
    # IronRidge-style: typically attachments at each rafter under rails, max 48" OC
    design_max = struct.max_attachment_spacing_in
    att_space = min(att_space, design_max) if design_max else att_space
    # Actually attachments land on rafters — spacing = rafter OC
    att_space = rafter_spacing_in

    total_rails = 0
    total_mid = 0
    total_end = 0
    total_att = 0
    total_splice = 0
    rail_len = struct.rail_length_ft

    for lay in layouts:
        if not lay.placed or lay.cols == 0:
            continue
        # 2 rails per row of modules (portrait or landscape both typically 2 rails)
        rows = lay.rows
        cols = lay.cols
        n = lay.fit_count
        # rails: 2 per module row
        rails_this = rows * 2
        # if modules span longer than rail length, add splices
        row_length_ft = (lay.placed[0].w_in * cols + lay.gap_in * max(0, cols - 1)) / 12.0
        splices_per_rail = max(0, int(row_length_ft // rail_len))
        total_splice += splices_per_rail * rails_this
        total_rails += rails_this

        # clamps: end clamps 2 per rail, mid clamps ≈ modules_per_row - 1 per rail side... 
        # Industry: mid clamps between modules (cols-1)*2 per row, end clamps 4 per row (2 rails × 2 ends)
        total_end += rows * 4
        total_mid += rows * max(0, cols - 1) * 2

        # attachments along each rail at rafter spacing
        for _ in range(rails_this):
            n_att = max(2, int(row_length_ft * 12 / att_space) + 1)
            total_att += n_att

        notes.append(
            f"{lay.plane.name}: {n} modules → {rails_this} rails, "
            f"row length ~{row_length_ft:.1f}', attachments @ {att_space:.0f}\" OC (rafter)"
        )

    # grounding lugs: ~1 per rail run group, min 2 per array, +1 per plane
    g_lugs = max(2, len(layouts) + total_rails // 4)

    # residual modules not in full rows already handled by fit_count

    return AttachmentBOM(
        rails=total_rails,
        mid_clamps=total_mid,
        end_clamps=total_end,
        attachments=total_att,
        splices=total_splice,
        grounding_lugs=g_lugs,
        rail_length_ft_each=rail_len,
        attachment_spacing_in=att_space,
        notes=notes,
    )


def _parse_rafter_spacing_in(criteria_frame: str, plane: RoofPlane | None = None) -> float:
    if plane and plane.rafter_spacing_in:
        return plane.rafter_spacing_in
    # parse "24\" O.C." from string
    import re

    m = re.search(r"(\d+)\s*[\"']?\s*O\.?C", criteria_frame, re.I)
    if m:
        return float(m.group(1))
    return 24.0


def build_roof_svg(layouts: list[PlaneLayout], north_angle: float = 0) -> str:
    """Multi-plane roof plan SVG with modules, setbacks, dimensions."""
    if not layouts:
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 400"><text x="20" y="40">No roof planes defined</text></svg>'

    # Layout planes side by side with padding
    pad = 40
    label_h = 50
    gap = 60
    scale = 2.0  # px per inch — will normalize to viewBox

    # First pass: compute sizes
    blocks = []
    for lay in layouts:
        w = lay.plane.eave_width_ft * 12
        h = lay.plane.ridge_depth_ft * 12
        blocks.append((lay, w, h))

    max_h = max(h for _, _, h in blocks)
    total_w = sum(w for _, w, _ in blocks) + gap * (len(blocks) - 1)
    # scale to fit ~1000 x 480 drawing area
    target_w, target_h = 980, 460
    s = min(target_w / max(total_w, 1), target_h / max(max_h, 1)) * 0.92

    svg_w = total_w * s + pad * 2
    svg_h = max_h * s + pad * 2 + label_h + 30

    parts = [
        f'<svg class="sld" viewBox="0 0 {svg_w:.1f} {svg_h:.1f}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="100%" height="100%" fill="#fafbfc"/>',
        f'<text x="{pad}" y="22" font-size="13" font-weight="700" font-family="Segoe UI,Arial">ROOF PLAN WITH MODULES — GENERATED FROM PLANE GEOMETRY</text>',
        f'<text x="{pad}" y="38" font-size="10" fill="#444" font-family="Segoe UI,Arial">Fire setbacks shown · modules packed in usable area · scale approx (verify field)</text>',
    ]

    x0 = pad
    y0 = pad + label_h

    for lay, w_in, h_in in blocks:
        pw, ph = w_in * s, h_in * s
        # roof outline
        parts.append(
            f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{pw:.1f}" height="{ph:.1f}" '
            f'fill="#fff" stroke="#111" stroke-width="2"/>'
        )
        # setback zone (ridge hatched band)
        rs = lay.plane.setback_ridge_in * s
        es = lay.plane.setback_eave_in * s
        ls = lay.plane.setback_left_in * s
        rks = lay.plane.setback_right_in * s
        # ridge setback at top
        parts.append(
            f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{pw:.1f}" height="{rs:.1f}" '
            f'fill="#f5e6e6" stroke="#8b0000" stroke-width="0.8" stroke-dasharray="4 2"/>'
        )
        parts.append(
            f'<text x="{x0 + pw/2:.1f}" y="{y0 + rs/2 + 4:.1f}" text-anchor="middle" '
            f'font-size="9" fill="#8b0000" font-family="Segoe UI,Arial">'
            f'{lay.plane.setback_ridge_in:.0f}" FIRE / RIDGE SETBACK</text>'
        )
        # eave setback at bottom
        parts.append(
            f'<rect x="{x0:.1f}" y="{y0 + ph - es:.1f}" width="{pw:.1f}" height="{es:.1f}" '
            f'fill="#f5e6e6" stroke="#8b0000" stroke-width="0.8" stroke-dasharray="4 2"/>'
        )
        # left/right rakes
        if ls > 0:
            parts.append(
                f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{ls:.1f}" height="{ph:.1f}" '
                f'fill="#f5e6e6" stroke="none" opacity="0.7"/>'
            )
        if rks > 0:
            parts.append(
                f'<rect x="{x0 + pw - rks:.1f}" y="{y0:.1f}" width="{rks:.1f}" height="{ph:.1f}" '
                f'fill="#f5e6e6" stroke="none" opacity="0.7"/>'
            )

        # modules (y_in is from eave — bottom of roof rect)
        for m in lay.placed:
            mx = x0 + m.x_in * s
            # convert eave-origin y to SVG (top origin): bottom - eave_offset - height
            my = y0 + ph - (m.y_in + m.h_in) * s
            mw, mh = m.w_in * s, m.h_in * s
            parts.append(
                f'<rect x="{mx:.1f}" y="{my:.1f}" width="{mw:.1f}" height="{mh:.1f}" '
                f'fill="#1a5fb4" stroke="#0b3d91" stroke-width="1"/>'
            )
            if mw > 18 and mh > 14:
                parts.append(
                    f'<text x="{mx + mw/2:.1f}" y="{my + mh/2 + 3:.1f}" text-anchor="middle" '
                    f'fill="#fff" font-size="8" font-family="Segoe UI,Arial">M{m.global_index}</text>'
                )

        # dimension: width
        parts.append(
            f'<line x1="{x0:.1f}" y1="{y0 + ph + 14:.1f}" x2="{x0 + pw:.1f}" y2="{y0 + ph + 14:.1f}" '
            f'stroke="#111" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x0 + pw/2:.1f}" y="{y0 + ph + 26:.1f}" text-anchor="middle" font-size="10" '
            f'font-family="Segoe UI,Arial">{lay.plane.eave_width_ft:.1f}\' EAVE</text>'
        )
        # depth dim
        parts.append(
            f'<line x1="{x0 + pw + 10:.1f}" y1="{y0:.1f}" x2="{x0 + pw + 10:.1f}" y2="{y0 + ph:.1f}" '
            f'stroke="#111" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x0 + pw + 14:.1f}" y="{y0 + ph/2:.1f}" font-size="10" '
            f'font-family="Segoe UI,Arial">{lay.plane.ridge_depth_ft:.1f}\'</text>'
        )

        # plane label
        parts.append(
            f'<text x="{x0:.1f}" y="{y0 - 8:.1f}" font-size="11" font-weight="700" '
            f'font-family="Segoe UI,Arial">{lay.plane.name} · AZ {lay.plane.azimuth_deg:.0f}° · '
            f'TILT {lay.plane.tilt_deg:.0f}° · {lay.fit_count}/{lay.requested} MOD</text>'
        )
        # ridge label
        parts.append(
            f'<text x="{x0 + pw/2:.1f}" y="{y0 - 2:.1f}" text-anchor="middle" font-size="8" '
            f'fill="#666" font-family="Segoe UI,Arial">← RIDGE</text>'
        )

        x0 += pw + gap

    # north arrow
    parts.append(
        f'<g transform="translate({svg_w - 50:.1f},70)">'
        f'<circle r="16" fill="none" stroke="#111" stroke-width="1.5"/>'
        f'<polygon points="0,-12 5,8 -5,8" fill="#111"/>'
        f'<text y="28" text-anchor="middle" font-size="10" font-weight="700">N</text></g>'
    )

    parts.append("</svg>")
    return "\n".join(parts)


def build_attachment_svg(struct: StructuralSystem, criteria_frame: str) -> str:
    """Cross-section attachment detail superior to generic IronRidge callout mill sheets."""
    return f'''<svg class="sld" viewBox="0 0 900 340" xmlns="http://www.w3.org/2000/svg">
  <text x="20" y="24" font-size="13" font-weight="700" font-family="Segoe UI,Arial">ATTACHMENT DETAIL — SECTION THRU RAIL / FLASHING / RAFTER</text>
  <text x="20" y="40" font-size="10" fill="#444" font-family="Segoe UI,Arial">Install per {struct.racking_mfr} span tables · {struct.attachment_hardware}</text>

  <!-- roof slope representation -->
  <line x1="80" y1="220" x2="820" y2="160" stroke="#888" stroke-width="2"/>
  <rect x="100" y="200" width="700" height="18" fill="#e8dcc8" stroke="#666" transform="rotate(-5 100 200)"/>
  <text x="450" y="250" text-anchor="middle" font-size="10" fill="#666" font-family="Segoe UI,Arial">(E) ROOFING · {criteria_frame}</text>

  <!-- rafter -->
  <rect x="400" y="218" width="28" height="70" fill="#c4a574" stroke="#5c4033" stroke-width="1.5"/>
  <text x="414" y="310" text-anchor="middle" font-size="9" font-family="Segoe UI,Arial">RAFTER</text>

  <!-- lag -->
  <line x1="414" y1="200" x2="414" y2="270" stroke="#333" stroke-width="3"/>
  <text x="430" y="255" font-size="9" font-family="Segoe UI,Arial">{struct.lag_size} LAG</text>
  <text x="430" y="268" font-size="9" font-family="Segoe UI,Arial">MIN {struct.lag_embedment_in}" THREAD EMBED</text>

  <!-- flash foot -->
  <rect x="390" y="188" width="48" height="16" fill="#ddd" stroke="#111" stroke-width="1.5"/>
  <text x="480" y="200" font-size="10" font-weight="700" font-family="Segoe UI,Arial">FLASHING / FOOT</text>
  <text x="480" y="212" font-size="9" fill="#444" font-family="Segoe UI,Arial">sealed penetration · match roofing warranty practice</text>

  <!-- rail -->
  <rect x="300" y="168" width="240" height="14" fill="#555" stroke="#111" stroke-width="1.5"/>
  <text x="560" y="178" font-size="10" font-weight="700" font-family="Segoe UI,Arial">{struct.rail_model} RAIL</text>

  <!-- clamp + module -->
  <rect x="380" y="150" width="50" height="12" fill="#222"/>
  <text x="560" y="158" font-size="9" font-family="Segoe UI,Arial">MID/END CLAMP (LISTED)</text>
  <rect x="320" y="120" width="200" height="28" fill="#1a5fb4" stroke="#0b3d91" stroke-width="1.5"/>
  <text x="420" y="138" text-anchor="middle" fill="#fff" font-size="11" font-weight="700" font-family="Segoe UI,Arial">PV MODULE</text>

  <!-- callout bubbles -->
  <rect x="40" y="60" width="260" height="90" fill="#fff" stroke="#111" stroke-width="1"/>
  <text x="50" y="78" font-size="10" font-weight="700" font-family="Segoe UI,Arial">STRUCTURAL REQUIREMENTS</text>
  <text x="50" y="96" font-size="9" font-family="Segoe UI,Arial">• Lag into solid rafter / truss chord only</text>
  <text x="50" y="110" font-size="9" font-family="Segoe UI,Arial">• Min embedment {struct.lag_embedment_in}" of thread</text>
  <text x="50" y="124" font-size="9" font-family="Segoe UI,Arial">• Max attachment spacing per PE / mfr tables</text>
  <text x="50" y="138" font-size="9" font-family="Segoe UI,Arial">• Do not overdrive · seal all penetrations</text>

  <rect x="620" y="60" width="250" height="90" fill="#fff" stroke="#111" stroke-width="1"/>
  <text x="630" y="78" font-size="10" font-weight="700" font-family="Segoe UI,Arial">BONDING</text>
  <text x="630" y="96" font-size="9" font-family="Segoe UI,Arial">• Integrated rail grounding or WEEB</text>
  <text x="630" y="110" font-size="9" font-family="Segoe UI,Arial">• Module frames bonded to rail</text>
  <text x="630" y="124" font-size="9" font-family="Segoe UI,Arial">• XR-LUG / listed lug to EGC</text>
  <text x="630" y="138" font-size="9" font-family="Segoe UI,Arial">• Continuous EGC to service GES</text>
</svg>'''


def compute_structural(project: ProjectInput) -> StructuralTotals:
    mod = _primary_module(project)
    planes = list(project.array.planes) if project.array.planes else []

    # Back-compat: synthesize one plane from legacy ArrayLayout fields
    if not planes:
        n_planes = max(1, project.array.roof_planes)
        for i in range(n_planes):
            n_mod = (
                project.array.modules_per_plane[i]
                if i < len(project.array.modules_per_plane)
                else project.array.modules_per_plane[-1]
            )
            az = project.array.azimuth_deg[i] if i < len(project.array.azimuth_deg) else 180
            tilt = project.array.tilt_deg[i] if i < len(project.array.tilt_deg) else 22
            # default residential plane large enough for modules
            planes.append(
                RoofPlane(
                    name=f"ROOF #{i+1}",
                    eave_width_ft=32.0,
                    ridge_depth_ft=16.0,
                    tilt_deg=tilt,
                    azimuth_deg=az,
                    module_count=n_mod,
                    setback_ridge_in=project.criteria.fire_setback_ridge_in,
                    setback_eave_in=project.criteria.fire_setback_eave_in,
                    setback_left_in=18,
                    setback_right_in=18,
                    portrait=True,
                )
            )

    layouts: list[PlaneLayout] = []
    warnings: list[str] = []
    g = 1
    for pl in planes:
        # inherit setbacks from criteria if still defaults? keep plane values
        lay = place_modules_on_plane(pl, mod, start_global=g)
        g += lay.fit_count
        layouts.append(lay)
        warnings.extend(lay.warnings)

    # module count check vs project modules
    placed_total = sum(l.fit_count for l in layouts)
    declared = sum(m.quantity for m in project.modules)
    if placed_total != declared:
        warnings.append(
            f"Placed modules on roof ({placed_total}) ≠ declared module qty ({declared}). "
            "Adjust plane sizes, setbacks, or module_count per plane."
        )

    rafter_sp = _parse_rafter_spacing_in(
        project.criteria.roof_frame,
        planes[0] if planes else None,
    )
    bom = compute_attachment_bom(layouts, project.array.structural, rafter_sp)

    # dead load
    # typical module weight ~ weight_lb if provided else estimate 2.5-3 psf of module area
    w_each = mod.weight_lb if mod.weight_lb else (mod.length_in * mod.width_in / IN2_SF) * 2.8
    total_w = w_each * placed_total
    # racking allowance ~0.5-1 psf of array area
    total_array_sf = sum(l.array_area_sf for l in layouts)
    total_roof_sf = sum(l.roof_area_sf for l in layouts)
    racking_psf = 0.75
    unit_psf = (total_w / total_array_sf + racking_psf) if total_array_sf > 0 else 0
    # distributed over roof plan area (more conservative for framing check is array-area psf)
    array_dead = unit_psf
    dead_ok = array_dead <= project.array.structural.max_dead_load_psf + 1e-6
    if not dead_ok:
        warnings.append(
            f"Array unit dead load ~{array_dead:.2f} psf exceeds design max "
            f"{project.array.structural.max_dead_load_psf} psf — PE review required."
        )

    cov = (100.0 * total_array_sf / total_roof_sf) if total_roof_sf > 0 else 0.0

    svg_roof = build_roof_svg(layouts)
    svg_att = build_attachment_svg(project.array.structural, project.criteria.roof_frame)

    return StructuralTotals(
        planes=layouts,
        bom=bom,
        module_weight_lb=w_each,
        array_dead_load_psf=array_dead,
        unit_weight_psf=unit_psf,
        total_array_sf=total_array_sf,
        total_roof_sf=total_roof_sf,
        coverage_pct=cov,
        dead_load_ok=dead_ok,
        warnings=warnings,
        svg_roof=svg_roof,
        svg_attachment=svg_att,
    )


def structural_to_dict(st: StructuralTotals) -> dict[str, Any]:
    return {
        "module_weight_lb": round(st.module_weight_lb, 1),
        "array_dead_load_psf": round(st.array_dead_load_psf, 2),
        "total_array_sf": round(st.total_array_sf, 1),
        "total_roof_sf": round(st.total_roof_sf, 1),
        "coverage_pct": round(st.coverage_pct, 2),
        "dead_load_ok": st.dead_load_ok,
        "bom": {
            "rails": st.bom.rails,
            "mid_clamps": st.bom.mid_clamps,
            "end_clamps": st.bom.end_clamps,
            "attachments": st.bom.attachments,
            "splices": st.bom.splices,
            "grounding_lugs": st.bom.grounding_lugs,
            "attachment_spacing_in": st.bom.attachment_spacing_in,
            "notes": st.bom.notes,
        },
        "planes": [
            {
                "name": p.plane.name,
                "eave_width_ft": p.plane.eave_width_ft,
                "ridge_depth_ft": p.plane.ridge_depth_ft,
                "tilt_deg": p.plane.tilt_deg,
                "azimuth_deg": p.plane.azimuth_deg,
                "requested": p.requested,
                "fit_count": p.fit_count,
                "cols": p.cols,
                "rows": p.rows,
                "array_area_sf": round(p.array_area_sf, 1),
                "roof_area_sf": round(p.roof_area_sf, 1),
                "coverage_pct": round(p.coverage_pct, 2),
                "setbacks_in": {
                    "ridge": p.plane.setback_ridge_in,
                    "eave": p.plane.setback_eave_in,
                    "left": p.plane.setback_left_in,
                    "right": p.plane.setback_right_in,
                },
            }
            for p in st.planes
        ],
        "warnings": st.warnings,
    }
