"""Bridge: Lumen Proposal Studio → Planset Generator ProjectInput.

Accepts the proposal studio's canonical ProposalProject JSON (or a thin wrapper)
and maps customer, address, modules, inverters, batteries, and array groups into
a permit-grade ProjectInput the planset engine already understands.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .models import (
    Address,
    AmbientDesign,
    ArrayLayout,
    BackupMode,
    BatterySpec,
    DesignCriteria,
    InterconnectionMethod,
    InverterSpec,
    ModuleSpec,
    ProjectInput,
    ProjectMeta,
    RoofPlane,
    ServiceSpec,
    StringDesign,
    StructuralSystem,
)


def _pick_module_defaults(code: str, manufacturer: str, watts: float | None) -> dict[str, float]:
    """Prefer materials_catalog match, then fall back to scaled defaults."""
    from .materials_catalog import find_module

    hit = find_module(f"{code} {manufacturer}")
    if hit:
        return {
            "pmax_w": float(hit["pmax_w"]),
            "vmp": float(hit["vmp"]),
            "imp": float(hit["imp"]),
            "voc": float(hit["voc"]),
            "isc": float(hit["isc"]),
            "voc_temp_coeff_pct_per_c": float(hit["voc_temp_coeff_pct_per_c"]),
            "length_in": float(hit["length_in"]),
            "width_in": float(hit["width_in"]),
            "weight_lb": float(hit.get("weight_lb") or 46),
            "manufacturer": hit["manufacturer"],
            "model": hit["model"],
        }

    d = {
        "pmax_w": 400.0,
        "vmp": 37.0,
        "imp": 10.8,
        "voc": 45.0,
        "isc": 11.5,
        "voc_temp_coeff_pct_per_c": -0.28,
        "length_in": 74.0,
        "width_in": 41.0,
        "weight_lb": 46.0,
    }
    if watts and watts > 0:
        scale = watts / d["pmax_w"]
        d["pmax_w"] = watts
        d["imp"] = round(d["imp"] * scale, 2)
        d["isc"] = round(d["isc"] * scale, 2)
    return d


def _unwrap(payload: dict[str, Any]) -> dict[str, Any]:
    """Accept raw ProposalProject, {project: ...}, or OpenSolar-ish wrapper."""
    if "primaryContact" in payload or "systems" in payload:
        return payload
    if "project" in payload and isinstance(payload["project"], dict):
        inner = payload["project"]
        if "primaryContact" in inner or "systems" in inner:
            return inner
    if "proposal" in payload and isinstance(payload["proposal"], dict):
        return payload["proposal"]
    return payload


def lumen_to_project_input(payload: dict[str, Any]) -> ProjectInput:
    p = _unwrap(payload)
    contact = p.get("primaryContact") or (p.get("contacts") or [{}])[0] or {}
    addr = p.get("address") or {}
    org = p.get("org") or {}
    systems = p.get("systems") or []
    if not systems:
        raise ValueError("Lumen proposal has no systems to import")
    selected_id = p.get("selectedSystemId")
    system = next((s for s in systems if s.get("id") == selected_id), systems[0])

    hw = system.get("hardware") or {}
    mod = hw.get("modules") or {}
    inv = hw.get("inverter") or {}
    bat = hw.get("battery") or {}
    groups = system.get("panelGroups") or []
    bills = system.get("bills") or {}

    customer = contact.get("fullName") or "Homeowner"
    street = addr.get("street") or addr.get("line1") or "Address TBD"
    city = addr.get("city") or ""
    state = (addr.get("state") or "GA")[:2].upper()
    zip_code = str(addr.get("zip") or "")
    lat = addr.get("lat")
    lon = addr.get("lon")

    kw_stc = float(system.get("kwStc") or 0)
    panel_count = int(
        system.get("panelCount")
        or mod.get("quantity")
        or sum(int(g.get("panels") or 0) for g in groups)
        or 1
    )
    watts = float(mod.get("watts") or (kw_stc * 1000 / panel_count if panel_count else 400))
    mod_code = mod.get("code") or "PV Module"
    mod_mfr = mod.get("manufacturer") or "Tier-1"
    defaults = _pick_module_defaults(mod_code, mod_mfr, watts)
    mod_mfr = str(defaults.get("manufacturer") or mod_mfr)
    mod_code = str(defaults.get("model") or mod_code)

    modules = [
        ModuleSpec(
            manufacturer=mod_mfr,
            model=mod_code,
            quantity=panel_count,
            pmax_w=defaults["pmax_w"],
            vmp=defaults["vmp"],
            imp=defaults["imp"],
            voc=defaults["voc"],
            isc=defaults["isc"],
            voc_temp_coeff_pct_per_c=defaults["voc_temp_coeff_pct_per_c"],
            length_in=defaults["length_in"],
            width_in=defaults["width_in"],
            weight_lb=defaults["weight_lb"],
        )
    ]

    from .materials_catalog import find_battery, find_inverter, find_racking

    inv_code = inv.get("code") or "Inverter"
    inv_mfr = inv.get("manufacturer") or "Inverter OEM"
    inv_qty = int(inv.get("quantity") or 1)
    inv_hit = find_inverter(f"{inv_code} {inv_mfr}")
    has_battery = bool(system.get("hasBattery") or bat)

    if inv_hit:
        inv_mfr = inv_hit["manufacturer"]
        inv_code = inv_hit["model"]
        is_micro = inv_hit.get("topology") == "micro"
        cont_w = float(inv_hit["continuous_ac_w"])
        cont_a = float(inv_hit["continuous_ac_a"])
        inv_qty = panel_count if is_micro else int(inv_hit.get("quantity_default") or 1)
        max_pv = inv_hit.get("max_pv_w")
        max_voc = inv_hit.get("max_voc")
        mppt = int(inv_hit.get("mppt_count") or 1)
        max_imp = inv_hit.get("max_imp_per_mppt")
        passthrough = inv_hit.get("passthrough_a")
        listing = inv_hit.get("listing") or "UL 1741"
    else:
        is_micro = any(x in inv_code.lower() for x in ("iq8", "enphase", "micro"))
        if is_micro:
            cont_w = min(watts * 0.96, 380)
            cont_a = round(cont_w / 240, 2)
            inv_qty = panel_count
            max_pv = watts
            max_voc = defaults["voc"] * 1.1
            mppt = 1
        else:
            cont_w = max(kw_stc * 1000 * 0.95, 3000)
            cont_a = round(cont_w / 240, 2)
            max_pv = kw_stc * 1000 * 1.3
            max_voc = 500
            mppt = 2 if has_battery else 1
        max_imp = defaults["imp"] * 1.25
        passthrough = 200 if has_battery else None
        listing = "UL 1741"

    inverters = [
        InverterSpec(
            manufacturer=inv_mfr,
            model=inv_code,
            quantity=inv_qty,
            continuous_ac_w=cont_w,
            continuous_ac_a=cont_a,
            max_ac_a=cont_a,
            nominal_vac=240,
            max_pv_w=max_pv,
            max_voc=max_voc,
            mppt_count=mppt,
            max_imp_per_mppt=max_imp,
            passthrough_a=passthrough,
            battery_cont_w=(float(bat.get("kwh") or system.get("batteryKwh") or 0) * 1000 * 0.5)
            if has_battery
            else None,
            listing=listing,
        )
    ]

    batteries: list[BatterySpec] = []
    if has_battery:
        bat_hit = find_battery(str(bat.get("code") or system.get("batteryKwh") or "powerwall"))
        if bat_hit and bat_hit.get("id") != "none":
            batteries.append(
                BatterySpec(
                    manufacturer=bat_hit["manufacturer"],
                    model=bat_hit["model"],
                    quantity=int(bat.get("quantity") or 1),
                    usable_kwh=float(bat_hit["usable_kwh"]),
                    nominal_v=float(bat_hit.get("nominal_v") or 48),
                    max_charge_a=bat_hit.get("max_charge_a"),
                    max_discharge_a=bat_hit.get("max_discharge_a"),
                )
            )
        else:
            batteries.append(
                BatterySpec(
                    manufacturer=(bat.get("code") or "Battery").split()[0]
                    if bat.get("code")
                    else "ESS",
                    model=bat.get("code") or "Home Battery",
                    quantity=int(bat.get("quantity") or 1),
                    usable_kwh=float(
                        system.get("batteryKwh") or bat.get("kwh") or 13.5
                    ),
                    nominal_v=48,
                )
            )

    rack_hit = find_racking("ironridge xr-100 flashfoot")

    # Roof planes from panel groups
    planes: list[RoofPlane] = []
    if groups:
        for i, g in enumerate(groups):
            n = int(g.get("panels") or 0)
            if n <= 0:
                continue
            # Rough plan footprint: ~2 ft module width × count along eave
            eave_w = max(12.0, min(48.0, n * 1.75))
            ridge_d = max(10.0, min(24.0, (n / max(eave_w / 3.5, 1)) * 3.5))
            planes.append(
                RoofPlane(
                    name=g.get("orientation") or f"ROOF #{i + 1}",
                    eave_width_ft=round(eave_w, 1),
                    ridge_depth_ft=round(ridge_d, 1),
                    tilt_deg=float(g.get("tilt") or 22),
                    azimuth_deg=float(g.get("azimuth") or 180),
                    module_count=n,
                    setback_ridge_in=36,
                    setback_eave_in=18,
                    portrait=True,
                    notes=f"Imported from Lumen proposal array {g.get('id') or i + 1}",
                )
            )
    if not planes:
        planes = [
            RoofPlane(
                name="ROOF #1",
                eave_width_ft=max(16.0, panel_count * 1.6),
                ridge_depth_ft=18.0,
                tilt_deg=22,
                azimuth_deg=180,
                module_count=panel_count,
            )
        ]

    notes = [
        "Imported from Lumen Proposal Studio.",
        "Equipment matched from materials catalog when possible — verify datasheets before stamp/submit.",
        f"Lumen project id: {p.get('id') or 'unknown'}",
    ]
    if p.get("solarResource"):
        sr = p["solarResource"]
        notes.append(
            f"Site solar resource: {sr.get('peakSunHoursAnnual')} PSH/day · "
            f"{sr.get('specificYieldKwhPerKw')} kWh/kW/yr ({sr.get('source')})"
        )

    # Simple string design for non-micros; micros use 1 module per "string" abstractly
    strings: list[StringDesign] = []
    if is_micro:
        # MLPE: do not invent 24 parallel strings (blows Imp checks).
        # Engineer finalizes branch circuits in the planset UI.
        strings.append(
            StringDesign(
                name="MLPE — finalize branch design in planset",
                module_model=mod_code,
                modules_in_series=1,
                parallel_strings=1,
                inverter_index=0,
                mppt_index=1,
            )
        )
        notes.append(
            f"Enphase/MLPE system: {panel_count} micros assumed 1:1 with modules. "
            "Complete AC branch / OCPD design in Plan Set Builder before submit."
        )
    else:
        # Target ~8–12 modules per string
        series = min(12, max(6, panel_count // max(1, mppt)))
        if series < 1:
            series = 1
        parallels = max(1, round(panel_count / series))
        strings.append(
            StringDesign(
                name="String bank A",
                module_model=mod_code,
                modules_in_series=series,
                parallel_strings=parallels,
                inverter_index=0,
                mppt_index=1,
            )
        )

    utility = bills.get("utilityName") or "Georgia Power"
    company = org.get("name") or "Savannah Solar Power"
    project_name = f"{customer} — {system.get('title') or system.get('name') or f'{kw_stc:.2f} kW'}"

    return ProjectInput(
        custom_title="PHOTOVOLTAIC SYSTEM — PRELIMINARY FROM SALES PROPOSAL",
        meta=ProjectMeta(
            project_name=project_name[:120],
            customer_name=customer,
            address=Address(
                line1=street,
                city=city,
                state=state,
                zip=zip_code,
                latitude=float(lat) if lat is not None else None,
                longitude=float(lon) if lon is not None else None,
            ),
            utility=utility,
            ahj="TBD — verify county/city",
            designer=company,
            company=company,
            prepared_date=date.today().isoformat(),
            revision="0",
            revision_note="IMPORTED FROM LUMEN PROPOSAL — ENGINEERING REVIEW REQUIRED",
        ),
        criteria=DesignCriteria(
            wind_speed_mph=130,
            wind_exposure="B",
            attic_run_required=True,
        ),
        ambient=AmbientDesign(record_low_c=-5, high_2pct_c=35),
        modules=modules,
        inverters=inverters,
        batteries=batteries,
        service=ServiceSpec(
            service_a=200,
            main_breaker_a=200,
            busbar_a=200,
            interconnection=(
                InterconnectionMethod.LOAD_SIDE_HYBRID
                if has_battery
                else InterconnectionMethod.BACKFEED
            ),
            backup_mode=BackupMode.CRITICAL_LOADS if has_battery else BackupMode.NONE,
            backfeed_breaker_a=None if has_battery else min(60, max(20, int(cont_a * inv_qty * 1.25))),
            ac_disco_a=60,
        ),
        strings=strings,
        array=ArrayLayout(
            planes=planes,
            structural=StructuralSystem(
                racking_mfr=(rack_hit or {}).get("manufacturer", "IronRidge"),
                rail_model=(rack_hit or {}).get("rail_model", "XR-100"),
                attachment_hardware=(rack_hit or {}).get("attachment", "FlashFoot 2"),
                lag_size=(rack_hit or {}).get("lag_size", '5/16" x 4.75" SS'),
                max_attachment_spacing_in=float(
                    (rack_hit or {}).get("max_attachment_spacing_in") or 48
                ),
            ),
            roof_planes=len(planes),
            modules_per_plane=[pl.module_count for pl in planes],
            azimuth_deg=[pl.azimuth_deg for pl in planes],
            tilt_deg=[pl.tilt_deg for pl in planes],
            racking=(rack_hit or {}).get("label")
            or "IronRidge XR-100 / FlashFoot 2 or AHJ-approved equal",
            attachment=(rack_hit or {}).get("attachment")
            or '5/16" x 4.75" SS lag, min 2-1/2" embedment into rafter',
        ),
        notes_construction=notes,
        notes_electrical=[
            "Confirm string sizing Voc_cold against inverter max input.",
            "Confirm interconnection topology with utility / AHJ.",
        ],
    )
