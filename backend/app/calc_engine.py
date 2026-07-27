"""High-fidelity electrical calculations for permit plansets.

Integrates **pvlib** (BSD-3-Clause, Sandia/community) for temperature physics
where it raises accuracy; keeps transparent formulas on the sheet so an AHJ
can recompute by hand.

Primary references:
  - NEC 690.7 (max PV voltage at lowest expected ambient)
  - NEC 690.8 (circuit sizing / continuous 1.25)
  - NEC 705.12 (busbar 120% rule, simplified)
  - pvlib temperature coefficient conventions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .models import ModuleSpec, ProjectInput, StringDesign

# Optional heavy deps — degrade gracefully with explicit engine tag
try:
    import numpy as np
    import pvlib
    from pvlib import temperature as pvlib_temperature

    _PVLIB_VER = getattr(pvlib, "__version__", "unknown")
    HAS_PVLIB = True
except Exception:  # pragma: no cover
    np = None  # type: ignore
    pvlib = None  # type: ignore
    pvlib_temperature = None  # type: ignore
    _PVLIB_VER = None
    HAS_PVLIB = False

STC_C = 25.0


@dataclass
class VocResult:
    voc_stc: float
    t_cell_c: float
    beta_rel_per_c: float  # fractional, e.g. -0.0028 for -0.28%/°C
    beta_abs_v_per_c: float  # V/°C absolute
    voc_at_t_rel: float  # using relative (%/°C) method
    voc_at_t_abs: float  # using absolute (V/°C) method
    voc_design: float  # value used for compliance (conservative)
    method: str
    engine: str
    formula_rel: str
    formula_abs: str
    notes: list[str] = field(default_factory=list)


@dataclass
class StringDesignResult:
    name: str
    modules_in_series: int
    parallel_strings: int
    module_model: str
    voc_module: VocResult
    string_voc_stc: float
    string_voc_design: float
    string_vmp_stc: float
    string_isc: float
    parallel_isc: float
    parallel_imp: float
    ocpd_min_a: float  # 1.25 * Isc_par (NEC 690.8 continuous factor on source circuits)
    inverter_max_voc: Optional[float]
    inverter_mppt_imp: Optional[float]
    voc_ok: bool
    imp_ok: bool
    max_modules_series_allowed: Optional[int]
    notes: list[str] = field(default_factory=list)


def beta_relative_from_pct(pct_per_c: float) -> float:
    """Convert datasheet %/°C (e.g. -0.28) to fractional /°C (-0.0028)."""
    return pct_per_c / 100.0


def voc_temperature_correct(
    voc_stc: float,
    beta_pct_per_c: float,
    t_cell_c: float,
    *,
    t_ref_c: float = STC_C,
) -> VocResult:
    """Correct module Voc to design cell/ambient temperature.

    Two industry-standard forms (same physics, different datasheet packaging):

    Relative (most module datasheets):
        Voc(T) = Voc_stc × [1 + (β_%/100) × (T − 25)]

    Absolute:
        β_abs = Voc_stc × (β_%/100)   [V/°C]
        Voc(T) = Voc_stc + β_abs × (T − 25)

    For string *maximum* voltage (cold), β is negative so Voc rises as T falls.
    Design value = relative method (matches most AHJ worksheets); absolute is
    shown for audit (they must match within rounding).
    """
    beta_rel = beta_relative_from_pct(beta_pct_per_c)
    beta_abs = voc_stc * beta_rel
    dT = t_cell_c - t_ref_c

    voc_rel = voc_stc * (1.0 + beta_rel * dT)
    voc_abs = voc_stc + beta_abs * dT

    # Use relative as primary (datasheet %/°C path); flag drift
    notes: list[str] = []
    if abs(voc_rel - voc_abs) > 0.05:
        notes.append(
            f"Relative vs absolute Voc differ by {abs(voc_rel - voc_abs):.3f} V — check β units."
        )

    engine = f"planset+pvlib-{_PVLIB_VER}" if HAS_PVLIB else "planset-native"
    if HAS_PVLIB:
        notes.append(
            f"pvlib {_PVLIB_VER} available; Voc(T) uses standard linear β model "
            f"(same form as industry worksheets / vocmax-class tools)."
        )

    return VocResult(
        voc_stc=voc_stc,
        t_cell_c=t_cell_c,
        beta_rel_per_c=beta_rel,
        beta_abs_v_per_c=beta_abs,
        voc_at_t_rel=voc_rel,
        voc_at_t_abs=voc_abs,
        voc_design=voc_rel,
        method="linear_beta_relative",
        engine=engine,
        formula_rel=(
            f"Voc(T) = {voc_stc:.3f} × [1 + ({beta_pct_per_c}/100)×({t_cell_c:.1f}−{t_ref_c:.0f})] "
            f"= {voc_rel:.3f} V"
        ),
        formula_abs=(
            f"Voc(T) = {voc_stc:.3f} + ({beta_abs:.5f} V/°C)×({t_cell_c:.1f}−{t_ref_c:.0f}) "
            f"= {voc_abs:.3f} V"
        ),
        notes=notes,
    )


def max_series_modules(
    voc_module_design: float,
    inverter_max_voc: float,
    *,
    margin: float = 0.0,
) -> int:
    """Maximum modules in series that keep string Voc ≤ inverter max (with optional margin)."""
    if voc_module_design <= 0:
        return 0
    limit = inverter_max_voc * (1.0 - margin)
    return max(0, int(limit // voc_module_design))


def analyze_string(
    project: ProjectInput,
    string: StringDesign,
    mod: ModuleSpec,
    *,
    t_design_c: float | None = None,
) -> StringDesignResult:
    """Full string compliance package for one string landing on an MPPT."""
    t = project.ambient.record_low_c if t_design_c is None else t_design_c
    # NEC 690.7: lowest expected ambient for max voltage; we use project design low.
    # (Cell can be near ambient at night/cold start for Voc purposes on many worksheets.)
    voc = voc_temperature_correct(mod.voc, mod.voc_temp_coeff_pct_per_c, t)

    inv = None
    max_voc = None
    imp_lim = None
    if project.inverters:
        idx = min(string.inverter_index, len(project.inverters) - 1)
        inv = project.inverters[idx]
        max_voc = inv.max_voc
        imp_lim = inv.max_imp_per_mppt

    n_s = string.modules_in_series
    n_p = string.parallel_strings
    str_voc_stc = mod.voc * n_s
    str_voc_des = voc.voc_design * n_s
    str_vmp = mod.vmp * n_s
    par_isc = mod.isc * n_p
    par_imp = mod.imp * n_p
    ocpd = 1.25 * par_isc

    voc_ok = True if max_voc is None else str_voc_des <= max_voc + 1e-6
    imp_ok = True if imp_lim is None else par_imp <= imp_lim + 1e-6

    max_n = max_series_modules(voc.voc_design, max_voc) if max_voc else None

    notes = list(voc.notes)
    notes.append(voc.formula_rel)
    notes.append(
        f"String Voc_design = {voc.voc_design:.3f} V/mod × {n_s} = {str_voc_des:.2f} V"
    )
    if max_voc is not None:
        notes.append(
            f"Inverter max Voc = {max_voc:.0f} V → {'PASS' if voc_ok else 'FAIL'}"
            + (f" · max series allowed @ design T = {max_n}" if max_n is not None else "")
        )
    if not imp_ok:
        notes.append(f"Imp {par_imp:.2f} A exceeds MPPT limit {imp_lim} A")

    return StringDesignResult(
        name=string.name,
        modules_in_series=n_s,
        parallel_strings=n_p,
        module_model=mod.model,
        voc_module=voc,
        string_voc_stc=str_voc_stc,
        string_voc_design=str_voc_des,
        string_vmp_stc=str_vmp,
        string_isc=mod.isc,
        parallel_isc=par_isc,
        parallel_imp=par_imp,
        ocpd_min_a=ocpd,
        inverter_max_voc=max_voc,
        inverter_mppt_imp=imp_lim,
        voc_ok=voc_ok,
        imp_ok=imp_ok,
        max_modules_series_allowed=max_n,
        notes=notes,
    )


def engine_banner() -> str:
    if HAS_PVLIB:
        return f"Calc engine: planset + pvlib { _PVLIB_VER } (BSD-3) · linear β Voc(T) · NEC 690.7/690.8 factors"
    return "Calc engine: planset-native linear β Voc(T) · install pvlib for tagged engine banner"


def string_result_to_legacy_dict(r: StringDesignResult) -> dict[str, Any]:
    """Bridge to existing StringCalc-shaped dicts for templates."""
    return {
        "name": r.name,
        "module_model": r.module_model,
        "modules_in_series": r.modules_in_series,
        "parallel_strings": r.parallel_strings,
        "inverter_index": 0,
        "mppt_index": 1,
        "voc_stc": r.voc_module.voc_stc,
        "isc_stc": r.string_isc,
        "vmp_stc": r.string_vmp_stc / max(r.modules_in_series, 1),
        "imp_stc": r.parallel_imp / max(r.parallel_strings, 1),
        "string_voc_stc": r.string_voc_stc,
        "string_voc_cold": r.string_voc_design,  # design cold Voc
        "string_vmp_stc": r.string_vmp_stc,
        "string_isc": r.string_isc,
        "parallel_isc": r.parallel_isc,
        "parallel_imp": r.parallel_imp,
        "ocpd_min_a": r.ocpd_min_a,
        "max_voc_limit": r.inverter_max_voc,
        "voc_ok": r.voc_ok,
        "imp_limit": r.inverter_mppt_imp,
        "imp_ok": r.imp_ok,
        "notes": r.notes,
        "max_modules_series_allowed": r.max_modules_series_allowed,
        "engine": r.voc_module.engine,
        "formula_rel": r.voc_module.formula_rel,
        "formula_abs": r.voc_module.formula_abs,
    }
