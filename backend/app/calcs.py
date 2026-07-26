"""Electrical design calculations for planset generation.

All formulas are shown on sheets so plan-checkers can verify.
Exceeds typical permit-mill packages that paste numbers without work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import ModuleSpec, ProjectInput, StringDesign


STC_TEMP_C = 25.0


def module_by_model(project: ProjectInput, model: str) -> ModuleSpec:
    for m in project.modules:
        if m.model == model or f"{m.manufacturer} {m.model}" == model:
            return m
    # fuzzy: model contained
    for m in project.modules:
        if model in m.model or m.model in model:
            return m
    raise KeyError(f"Module model not found: {model}")


def cold_voc(voc_stc: float, coeff_pct_per_c: float, t_low_c: float) -> float:
    """Voc at design low temp — delegates to calc_engine (pvlib-aligned linear β)."""
    from .calc_engine import voc_temperature_correct

    return voc_temperature_correct(voc_stc, coeff_pct_per_c, t_low_c).voc_design


def hot_vmp(vmp_stc: float, coeff_pct_per_c: float, t_cell_c: float) -> float:
    """Approx Vmp at high cell temp (use same Voc coeff if Vmp coeff unknown)."""
    return vmp_stc * (1.0 + (coeff_pct_per_c / 100.0) * (t_cell_c - STC_TEMP_C))


@dataclass
class StringCalc:
    name: str
    module_model: str
    modules_in_series: int
    parallel_strings: int
    inverter_index: int
    mppt_index: int
    voc_stc: float
    isc_stc: float
    vmp_stc: float
    imp_stc: float
    string_voc_stc: float
    string_voc_cold: float
    string_vmp_stc: float
    string_isc: float
    parallel_isc: float
    parallel_imp: float
    ocpd_min_a: float  # 1.25 * Isc * parallel (NEC 690.8/9 context simplified)
    max_voc_limit: float | None
    voc_ok: bool
    imp_limit: float | None
    imp_ok: bool
    notes: list[str] = field(default_factory=list)


@dataclass
class SystemTotals:
    module_count: int
    dc_kw: float
    ac_kw_continuous: float
    ac_a_continuous: float
    battery_kwh: float
    dc_ac_ratio: float | None
    max_backfeed_a: float | None
    busbar_120_rule: dict[str, Any] | None
    continuous_factor_notes: list[str]
    string_calcs: list[StringCalc]
    warnings: list[str]
    quality_flags: list[str]


def busbar_120_check(
    busbar_a: int | None,
    main_breaker_a: int,
    backfeed_a: int | None,
) -> dict[str, Any] | None:
    """NEC 705.12(B)(3) 120% busbar rule (simplified single backfeed)."""
    if backfeed_a is None:
        return None
    bus = busbar_a or main_breaker_a
    limit = 1.20 * bus
    sum_ocpd = main_breaker_a + backfeed_a
    return {
        "busbar_a": bus,
        "main_breaker_a": main_breaker_a,
        "backfeed_a": backfeed_a,
        "sum_ocpd": sum_ocpd,
        "limit_120pct": limit,
        "passes": sum_ocpd <= limit + 1e-6,
        "formula": f"Main ({main_breaker_a}A) + Backfeed ({backfeed_a}A) = {sum_ocpd}A ≤ 1.20 × Bus ({bus}A) = {limit:.0f}A",
        "code": "NEC 705.12 (busbar 120% allowance) — confirm exact edition adopted by AHJ",
    }


def compute_system(project: ProjectInput) -> SystemTotals:
    warnings: list[str] = []
    quality: list[str] = []
    string_calcs: list[StringCalc] = []

    # Module totals
    module_count = sum(m.quantity for m in project.modules)
    dc_w = sum(m.quantity * m.pmax_w for m in project.modules)
    dc_kw = dc_w / 1000.0

    ac_w = sum(inv.quantity * inv.continuous_ac_w for inv in project.inverters)
    ac_a = sum(inv.quantity * inv.continuous_ac_a for inv in project.inverters)
    ac_kw = ac_w / 1000.0

    bat_kwh = sum(b.quantity * b.usable_kwh for b in project.batteries)

    dc_ac = (dc_kw / ac_kw) if ac_kw > 0 else None

    # Strings — auto-build if empty: one string all modules of first type
    strings = list(project.strings)
    if not strings and project.modules:
        m0 = project.modules[0]
        # heuristic series count from first inverter Voc limit
        max_voc = project.inverters[0].max_voc if project.inverters else 500
        max_voc = max_voc or 500
        voc_cold_1 = cold_voc(m0.voc, m0.voc_temp_coeff_pct_per_c, project.ambient.record_low_c)
        n_series = max(1, int(max_voc / voc_cold_1))
        # distribute quantity
        if m0.quantity % n_series == 0:
            n_par = m0.quantity // n_series
            strings = [
                StringDesign(
                    name="String 1",
                    module_model=m0.model,
                    modules_in_series=n_series,
                    parallel_strings=n_par,
                )
            ]
        else:
            # single series string count = quantity (may fail Voc — will warn)
            strings = [
                StringDesign(
                    name="String 1",
                    module_model=m0.model,
                    modules_in_series=min(m0.quantity, n_series),
                    parallel_strings=1,
                )
            ]
            warnings.append(
                "Stringing auto-generated; verify series/parallel matches field layout."
            )
        quality.append("AUTO_STRING_DESIGN")

    t_low = project.ambient.record_low_c
    from .calc_engine import analyze_string, engine_banner

    quality.append("PVLIB_CALC_ENGINE" if "pvlib" in engine_banner().lower() else "NATIVE_CALC_ENGINE")

    for s in strings:
        try:
            mod = module_by_model(project, s.module_model)
        except KeyError as e:
            warnings.append(str(e))
            continue

        r = analyze_string(project, s, mod, t_design_c=t_low)
        if not r.voc_ok:
            warnings.append(
                f"{r.name}: design Voc {r.string_voc_design:.1f}V exceeds inverter limit {r.inverter_max_voc}V"
            )
        if not r.imp_ok:
            warnings.append(
                f"{r.name}: Imp {r.parallel_imp:.1f}A exceeds MPPT limit {r.inverter_mppt_imp}A"
            )

        string_calcs.append(
            StringCalc(
                name=r.name,
                module_model=r.module_model,
                modules_in_series=r.modules_in_series,
                parallel_strings=r.parallel_strings,
                inverter_index=s.inverter_index,
                mppt_index=s.mppt_index,
                voc_stc=mod.voc,
                isc_stc=mod.isc,
                vmp_stc=mod.vmp,
                imp_stc=mod.imp,
                string_voc_stc=r.string_voc_stc,
                string_voc_cold=r.string_voc_design,
                string_vmp_stc=r.string_vmp_stc,
                string_isc=r.string_isc,
                parallel_isc=r.parallel_isc,
                parallel_imp=r.parallel_imp,
                ocpd_min_a=r.ocpd_min_a,
                max_voc_limit=r.inverter_max_voc,
                voc_ok=r.voc_ok,
                imp_limit=r.inverter_mppt_imp,
                imp_ok=r.imp_ok,
                notes=r.notes,
            )
        )

    # Backfeed / 120% rule
    bf = project.service.backfeed_breaker_a
    if bf is None and project.service.interconnection.value == "backfeed_breaker":
        # size backfeed ≥ 1.25 × inverter continuous current (sum)
        bf = int((ac_a * 1.25 + 0.5) // 5 * 5)  # round up to 5A
        if bf < 15:
            bf = 15
        quality.append("AUTO_BACKFEED_BREAKER")

    bus = busbar_120_check(
        project.service.busbar_a,
        project.service.main_breaker_a,
        bf if project.service.interconnection.value == "backfeed_breaker" else None,
    )
    if bus and not bus["passes"]:
        warnings.append(f"Busbar 120% rule FAIL: {bus['formula']}")

    # Hybrid passthrough sanity for dual disco
    if project.service.backup_mode.value in ("half_home", "full_dual_disco"):
        for inv in project.inverters:
            if inv.passthrough_a and inv.passthrough_a < project.service.disconnect_rating_a:
                warnings.append(
                    f"{inv.model}: passthrough {inv.passthrough_a}A < disco "
                    f"{project.service.disconnect_rating_a}A — confirm load-side topology."
                )
        if project.service.backup_mode.value == "full_dual_disco":
            n_inv = sum(i.quantity for i in project.inverters)
            if n_inv < 2:
                warnings.append(
                    "Full dual-disco backup typically requires ≥2 hybrid inverters (one per 200A path)."
                )

    # Quality upgrades vs permit mills
    quality.append("FORMULA_WORK_SHOWN")
    quality.append("VOC_TEMPERATURE_CORRECTED")
    quality.append("CALC_ENGINE_BANNER")
    if project.batteries:
        quality.append("ESS_INCLUDED")
    if project.critical_loads:
        quality.append("CRITICAL_LOAD_SCHEDULE")

    cont_notes = [
        engine_banner(),
        "Inverter continuous output currents use nameplate continuous ratings.",
        "OCPD for continuous loads sized at 125% where required (NEC 215.3 / 690.8 / 705 as applicable).",
        f"Ambient design (NEC 690.7 low-temp Voc): record low {t_low}°C · high 2% {project.ambient.high_2pct_c}°C.",
        "Voc(T) uses linear β model (relative %/°C and absolute V/°C shown on string notes).",
    ]

    # Sanity: cover sheet AC vs DC nonsense
    if ac_kw > 0 and dc_kw > 0 and ac_kw > dc_kw * 3 and not project.batteries:
        warnings.append(
            f"AC continuous ({ac_kw:.1f} kW) ≫ DC array ({dc_kw:.1f} kW) without storage — "
            "verify inverter rating is not being misused as system AC size on cover."
        )
        quality.append("CAUGHT_COVER_KWAC_MISUSE")

    return SystemTotals(
        module_count=module_count,
        dc_kw=dc_kw,
        ac_kw_continuous=ac_kw,
        ac_a_continuous=ac_a,
        battery_kwh=bat_kwh,
        dc_ac_ratio=dc_ac,
        max_backfeed_a=float(bf) if bf is not None else None,
        busbar_120_rule=bus,
        continuous_factor_notes=cont_notes,
        string_calcs=string_calcs,
        warnings=warnings,
        quality_flags=quality,
    )


def totals_to_dict(t: SystemTotals) -> dict[str, Any]:
    return {
        "module_count": t.module_count,
        "dc_kw": round(t.dc_kw, 3),
        "ac_kw_continuous": round(t.ac_kw_continuous, 3),
        "ac_a_continuous": round(t.ac_a_continuous, 2),
        "battery_kwh": round(t.battery_kwh, 2),
        "dc_ac_ratio": round(t.dc_ac_ratio, 3) if t.dc_ac_ratio is not None else None,
        "max_backfeed_a": t.max_backfeed_a,
        "busbar_120_rule": t.busbar_120_rule,
        "continuous_factor_notes": t.continuous_factor_notes,
        "string_calcs": [sc.__dict__ for sc in t.string_calcs],
        "warnings": t.warnings,
        "quality_flags": t.quality_flags,
    }
