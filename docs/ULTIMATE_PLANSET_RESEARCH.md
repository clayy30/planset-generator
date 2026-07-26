# Ultimate Planset Generator — Research, Forks, Architecture

**Date:** 2026-07-25  
**Author:** Planset Generator team (clayy30)  
**Engine repo:** https://github.com/clayy30/planset-generator  
**Umbrella plan:** this document  

---

## 1. Executive finding (ruthless)

**There is no production-grade open-source AHJ planset generator on GitHub.**

Searches across solar permit packages, SLD generators, string sizing, roof layout, structural BOM, NEC labels, and hybrid ESS modeling turned up:

| Category | Reality |
|----------|---------|
| Full multi-sheet AHJ plansets | **Absent.** Closest is stale `solarpermit` (permit *requirements tracking*, 2014, not drawings). |
| Hybrid dual-disco / GridBOSS topology | **Absent** in OSS (only commercial / manufacturer PDFs). |
| Temperature-corrected string math | **Present** as libraries (`pvlib`, `vocmax`), not as plansets. |
| Electrical diagram drawing | **Present** as generic diagram libs (`schemdraw`), not solar-permit SLD. |
| Roof module packing | **Thin** hobby DXF tools; nothing fire-setback + attachment BOM grade. |
| NEC labels | **Public code text** + free AHJ PDFs (e.g. MN DLI); no solid generator library. |

**Conclusion:** The existing `planset-generator` is already ahead of the OSS landscape for **US residential hybrid permit packages**. The path to “ultimate” is:

1. **Keep the planset engine as the product core** (what we built).  
2. **Import quality from libraries** (pvlib, schemdraw, pysam, vocmax algorithms)—not rewrite around immature apps.  
3. **Do not absorb low-quality layout toys or abandoned permit trackers.**

---

## 2. Repos forked (under `clayy30`)

| Upstream | Fork | License | Stars (approx) | Why forked | How we use it |
|----------|------|---------|----------------|------------|---------------|
| [pvlib/pvlib-python](https://github.com/pvlib/pvlib-python) | [clayy30/pvlib-python](https://github.com/clayy30/pvlib-python) | BSD-3-Clause | ~1.6k | Gold standard PV models, temp coeffs, irradiance | Optional dependency: site temp extremes, future yield appendix |
| [cdelker/schemdraw](https://github.com/cdelker/schemdraw) | [clayy30/schemdraw](https://github.com/clayy30/schemdraw) | MIT | ~255 | Electrical symbol drawing in pure Python | Phase 2: replace hand-SVG SLD with symbol library |
| [openpvtools/openpvtools](https://github.com/openpvtools/openpvtools) | [clayy30/openpvtools](https://github.com/clayy30/openpvtools) | MIT | ~58 | Curated catalog of OSS PV tools | Living roadmap / dependency radar |
| [NatLabRockies/pysam](https://github.com/NatLabRockies/pysam) | [clayy30/pysam](https://github.com/clayy30/pysam) | BSD-3-Clause | ~144 | NREL SAM Python API | Phase 3: optional energy production appendix sheet |
| [SunPower/pvfactors](https://github.com/SunPower/pvfactors) | [clayy30/pvfactors](https://github.com/clayy30/pvfactors) | BSD-3-Clause | ~89 | Bifacial view-factor model | Phase 3: bifacial array notes only |
| [toddkarin/vocmax](https://github.com/toddkarin/vocmax) | [clayy30/vocmax](https://github.com/clayy30/vocmax) | Unclear (NOASSERTION) | ~12 | String length / cold Voc focus | **Algorithms only**—reimplement under our license; do not vendor blindly |

### Forked but **not** used as product foundations

| Repo | Why discarded as core |
|------|------------------------|
| `nivaaz/SLD-website` | Unlicensed, stale (2019), building-services not solar hybrid |
| `jmypk/Solar-Dxf-Studio` | No license, immature |
| `solarpermit/solarpermit` | BSD but abandoned (2014); tracks codes, doesn’t draw plansets |
| Home-Assistant / inverter telemetry projects | Wrong domain (ops, not permit drawings) |

---

## 3. Current engine strengths (keep)

From `clayy30/planset-generator` (local production system):

| Strength | Module(s) | Keep? |
|----------|-----------|-------|
| Hybrid topologies (half-home, dual disco, backfeed, GridBOSS path) | `sld.py`, `sld_diagrams.py`, models | **Yes — unique in OSS** |
| Voc_cold / string PASS-FAIL with work shown | `calcs.py` | **Yes** |
| Continuous vs surge / island amp honesty | SLD + calcs | **Yes** |
| Geometry roof packer + fire setbacks | `layout.py` | **Yes** |
| Attachment BOM from placed grid | `layout.py` | **Yes** |
| One cut-sheet per equipment slot | `equipment_lib.py` | **Yes** |
| NEC-colored label sheet (permit practice) | `labels_page.py` | **Yes** |
| GIS title block (APN, owner, lat/lon) | `gis.py` | **Yes** |
| QA / AHJ checklist sheet | template PV-7 | **Yes** |
| Materials catalog + presets | `materials_catalog.py`, `presets.py` | **Yes** |
| ANSI B multi-sheet HTML → print PDF | `render.py`, `planset.html` | **Yes** (until true PDF engine) |

### Weaknesses to fix (honest)

| Gap | Severity | Fix |
|-----|----------|-----|
| SVG hand-drawn SLD (no symbol library) | High for PE polish | schemdraw / standard IEEE symbols |
| Wire sizes are design-basis heuristics, not full NEC tables | Medium | Wire tables module + VD |
| Few county parcel layers | Medium | Expand GIS registry |
| No CLI-first entrypoint | Medium | `python -m planset` generate |
| HTML not CAD/DXF | Medium for some AHJs | Optional DXF export later |
| No automated tests | High | pytest for calcs + SLD segments |
| Appendix HTML huge (base64 rasters) | Medium | Link PDFs + optional raster |
| Layout quality regressions (overlap) | Ongoing | Snapshot tests |

---

## 4. Recommended architecture

```
ultimate-planset / planset-generator
├── planset/                      # installable Python package (CLI-first)
│   ├── domain/                   # pure models (Pydantic)
│   │   ├── project.py
│   │   ├── electrical.py
│   │   ├── structural.py
│   │   └── topology.py           # interconnection enums + rules
│   ├── calc/                     # pure functions, fully tested
│   │   ├── string_voc.py         # absorb vocmax ideas + pvlib temp
│   │   ├── busbar_705.py
│   │   ├── wire_nec.py
│   │   └── island_capacity.py
│   ├── layout/                   # roof packer, BOM
│   ├── sld/                      # topology → diagram IR → SVG/PDF
│   │   ├── ir.py                 # intermediate representation
│   │   ├── render_svg.py
│   │   └── render_schemdraw.py   # optional backend
│   ├── labels/                   # NEC placard IR → SVG
│   ├── gis/                      # geocode + parcel adapters
│   ├── equipment/                # library index + matcher
│   ├── sheets/                   # one renderer per sheet type
│   ├── export/                   # HTML, PDF (weasy/playwright), ZIP
│   └── cli.py                    # `planset generate project.json`
├── web/                          # optional FastAPI + static UI
├── data/equipment/               # cut sheets (git-lfs optional)
├── tests/
└── docs/
```

### Design principles

1. **Domain first** — topology rules live outside templates.  
2. **Calc purity** — every number on a sheet has a function + unit test.  
3. **Diagram IR** — SLD is a graph of components/edges, not f-string soup.  
4. **CLI-first** — web is a client of the same library.  
5. **Permissive stack only** — BSD/MIT deps; reimplement unclear-license algorithms.  
6. **Electrician-readable** — if a crew can’t pull wire from PV-3, it fails QA.

### Stack choice

| Layer | Choice | Why |
|-------|--------|-----|
| Language | **Python 3.12/3.13** | pvlib, schemdraw, existing engine |
| Models | Pydantic v2 | Already proven |
| API | FastAPI (optional) | Existing UI |
| Diagrams | SVG now → schemdraw IR later | Quality path |
| PDF | Playwright/Chromium print or WeasyPrint | AHJ wants PDF |
| CLI | Typer or argparse | Operator-friendly |
| Tests | pytest | Non-negotiable |

---

## 5. Phased implementation plan

### Phase 0 — Stabilize (1 week) ✅ largely done
- [x] Multi-sheet ANSI B output  
- [x] Hybrid SLD paths  
- [x] Voc math + QA  
- [x] Labels + GIS + equipment library  
- [ ] **pytest** for `calcs.py` / segments  
- [ ] Snapshot HTML for PV-2A / PV-3 (catch overlaps)  

### Phase 1 — CLI-first package (1–2 weeks)
- Extract `planset` package from `backend/app`  
- `planset generate project.json -o out/`  
- `planset calc project.json` (JSON math only)  
- `planset gis "30 Houston St, Savannah GA"`  
- Pin Python 3.12/3.13; document poppler for appendix  

### Phase 2 — SLD IR + schemdraw (2–3 weeks)
- Define SLD intermediate representation (nodes, edges, ratings, conductors)  
- Port half-home / backfeed / dual-disco to IR  
- Optional schemdraw backend for IEEE-ish symbols  
- Wire schedule **generated only from IR** (single source of truth)  

### Phase 3 — NEC wire + temperature fidelity (2 weeks)
- NEC 310.16 / 250.122 tables as data  
- Voltage drop option  
- Optional pvlib for Tmin from site lat/lon (TMY)  
- Reimplement vocmax-style max modules/string with tests  

### Phase 4 — Structural + counties (2 weeks)
- Attachment spacing from span-table CSV (manufacturer published)  
- Expand GIS parcel registry (Effingham, Liberty, Bryan, …)  
- PE letter attachment hook  

### Phase 5 — Export & AHJ pack (2 weeks)
- One-click multi-page PDF  
- ZIP: planset.pdf + appendix cut sheets + calcs.json  
- Version stamp + revision history on every sheet  

### Phase 6 — Optional yield appendix
- pysam or pvlib production estimate sheet (clearly labeled “energy estimate, not permit electrical”)  

---

## 6. Key improvements over current generator

| Area | Today | Ultimate |
|------|-------|----------|
| Productization | Web app in a folder | Installable CLI package + optional web |
| SLD | Hand-tuned SVG f-strings | Topology IR → multiple renderers |
| Wire | Heuristic AWG | Table-driven NEC + VD |
| Tests | Manual smoke | Automated calc + layout regression |
| Deps | Custom only | pvlib/schemdraw where they raise quality |
| Hybrid | Strong | Same + IR makes new topologies cheap |
| Export | Browser print | Headless PDF + zip pack |
| Ecosystem | Isolated | Forks tracked; openpvtools radar |

---

## 7. First working prototype (next build)

**Do this next (concrete):**

1. **`tests/test_calcs_voc.py`** — freeze Voc_cold formulas; fail on silent regression.  
2. **`planset/cli.py`** —  
   `planset generate examples/duracell_400a.json --out dist/`  
3. **`planset/sld/ir.py`** — represent half-home as nodes/edges; render from IR only.  
4. **Delete** marketing fluff from sheets; keep electrician sequence.  
5. **Document** dependency map: engine vs forked research repos.

**Do not do next:**  
- Rewrite in JS/TS  
- Absorb abandoned permit trackers  
- Vendor entire pvlib into the monorepo (use PyPI dependency)  
- Fake PE stamps or span tables  

---

## 8. License posture

- Engine: keep **clear OSS license** (recommend **MIT** or **Apache-2.0** for the product).  
- Dependencies: BSD/MIT preferred.  
- `vocmax`: **study only** until license clarified; reimplement algorithms.  
- Equipment PDFs: manufacturer docs; ship under “for permit submittal,” not relicense.  
- NEC text: public code language; labels are not proprietary sticker art.

---

## 9. Competitive honesty

| Competitor type | What they win | What we win |
|-----------------|---------------|-------------|
| Permit mills (SPS-style CAD) | Roof CAD aesthetics, PE relationships | Hybrid topology honesty, calc transparency, automation, OSS |
| OpenSolar / Aurora | Sales UX, finance | Field electrical truth, dual-disco ESS, local control |
| Manufacturer tools | Equipment accuracy | Multi-vendor, multi-topology, full planset |

**Bar to ship “ultimate”:** an electrician who has never seen the job can land wire from PV-3 + PV-5 alone, and an AHJ can verify Voc/busbar from PV-4 without calling the designer.

---

## 10. Links

| Resource | URL |
|----------|-----|
| Engine | https://github.com/clayy30/planset-generator |
| Fork: pvlib | https://github.com/clayy30/pvlib-python |
| Fork: schemdraw | https://github.com/clayy30/schemdraw |
| Fork: openpvtools | https://github.com/clayy30/openpvtools |
| Fork: pysam | https://github.com/clayy30/pysam |
| Fork: pvfactors | https://github.com/clayy30/pvfactors |
| Fork: vocmax | https://github.com/clayy30/vocmax |
| Share / Codespaces | https://codespaces.new/clayy30/planset-generator |
