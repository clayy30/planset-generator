"""Approved materials list — known equipment with electrical nameplates.

This is the source of truth for dropdowns in the planset UI and Lumen import
lookups. Spec sheet filenames match data/equipment/ when present.
"""

from __future__ import annotations

from typing import Any, Optional

# ── Modules ──────────────────────────────────────────────────────────────
MODULES: list[dict[str, Any]] = [
    {
        "id": "cs-cs61-54tm-h-450",
        "manufacturer": "Canadian Solar",
        "model": "CS6.1-54TM-H-450",
        "label": "Canadian Solar CS6.1-54TM-H 450W (TOPHiKu6 All-Black)",
        "pmax_w": 450,
        "vmp": 41.5,
        "imp": 10.85,
        "voc": 49.5,
        "isc": 11.5,
        "voc_temp_coeff_pct_per_c": -0.27,
        "length_in": 82.4,
        "width_in": 44.6,
        "depth_in": 1.4,
        "weight_lb": 48.5,
        "spec_sheet": "modules/CS-Datasheet-TOPHiKu6 (All-Black)_CS6.1-54TM-H_v1.1C25_F23_D1_A_TX (2) 1 (1).pdf",
        "keywords": ["canadian", "cs6.1", "450", "tophiku"],
    },
    {
        "id": "cs-450-blk-texas",
        "manufacturer": "Canadian Solar",
        "model": "450W-BLK-TEXAS",
        "label": "Canadian Solar 450W Black (Texas)",
        "pmax_w": 450,
        "vmp": 41.5,
        "imp": 10.85,
        "voc": 49.5,
        "isc": 11.5,
        "voc_temp_coeff_pct_per_c": -0.27,
        "length_in": 82.4,
        "width_in": 44.6,
        "depth_in": 1.4,
        "weight_lb": 48.5,
        "spec_sheet": "modules/Canadian-450w-BLK-TEXAS.pdf",
        "keywords": ["canadian", "450", "black", "texas"],
    },
    {
        "id": "rec-alpha-pure-400",
        "manufacturer": "REC Group",
        "model": "Alpha Pure 400",
        "label": "REC Alpha Pure 400W",
        "pmax_w": 400,
        "vmp": 37.2,
        "imp": 10.76,
        "voc": 44.8,
        "isc": 11.45,
        "voc_temp_coeff_pct_per_c": -0.26,
        "length_in": 71.7,
        "width_in": 40.9,
        "depth_in": 1.2,
        "weight_lb": 45.0,
        "spec_sheet": None,
        "keywords": ["rec", "alpha", "pure", "400"],
    },
    {
        "id": "qcells-qpeak-duo-400",
        "manufacturer": "Qcells",
        "model": "Q.PEAK DUO 400",
        "label": "Qcells Q.PEAK DUO 400W",
        "pmax_w": 400,
        "vmp": 37.0,
        "imp": 10.81,
        "voc": 45.0,
        "isc": 11.5,
        "voc_temp_coeff_pct_per_c": -0.27,
        "length_in": 74.0,
        "width_in": 41.1,
        "depth_in": 1.26,
        "weight_lb": 46.0,
        "spec_sheet": None,
        "keywords": ["qcells", "q.peak", "400"],
    },
    {
        "id": "qcells-410",
        "manufacturer": "Qcells",
        "model": "Q.PEAK DUO 410",
        "label": "Qcells Q.PEAK DUO 410W",
        "pmax_w": 410,
        "vmp": 37.8,
        "imp": 10.85,
        "voc": 45.5,
        "isc": 11.55,
        "voc_temp_coeff_pct_per_c": -0.27,
        "length_in": 74.4,
        "width_in": 41.1,
        "depth_in": 1.26,
        "weight_lb": 47.0,
        "spec_sheet": None,
        "keywords": ["qcells", "410"],
    },
    {
        "id": "ja-440",
        "manufacturer": "JA Solar",
        "model": "JAM54S31-440/MR",
        "label": "JA Solar 440W",
        "pmax_w": 440,
        "vmp": 32.5,
        "imp": 13.54,
        "voc": 39.0,
        "isc": 14.3,
        "voc_temp_coeff_pct_per_c": -0.28,
        "length_in": 67.8,
        "width_in": 44.6,
        "depth_in": 1.18,
        "weight_lb": 48.0,
        "spec_sheet": None,
        "keywords": ["ja", "440"],
    },
]

# ── Inverters ────────────────────────────────────────────────────────────
INVERTERS: list[dict[str, Any]] = [
    {
        "id": "dpc-max-hybrid-15",
        "manufacturer": "Duracell Power Center",
        "model": "Max Hybrid 15",
        "label": "DPC Max Hybrid 15",
        "quantity_default": 1,
        "continuous_ac_w": 15000,
        "continuous_ac_a": 62.5,
        "max_ac_a": 62.5,
        "nominal_vac": 240,
        "max_pv_w": 19500,
        "max_voc": 500,
        "mppt_count": 3,
        "max_imp_per_mppt": 26,
        "passthrough_a": 200,
        "parallel_capable": True,
        "max_parallel": 12,
        "listing": "UL 1741 / IEEE 1547a",
        "topology": "hybrid",
        "spec_sheet": "inverters/DPC-Max-Hybrid-15-Spec-sheet-11-22-24-2--1-.pdf",
        "keywords": ["dpc", "duracell", "max hybrid", "15"],
    },
    {
        "id": "eg4-18kpv",
        "manufacturer": "EG4",
        "model": "18KPV-12LV",
        "label": "EG4 18kPV",
        "quantity_default": 1,
        "continuous_ac_w": 12000,
        "continuous_ac_a": 50,
        "max_ac_a": 50,
        "nominal_vac": 240,
        "max_pv_w": 18000,
        "max_voc": 600,
        "mppt_count": 3,
        "max_imp_per_mppt": 25,
        "passthrough_a": 200,
        "parallel_capable": True,
        "max_parallel": 10,
        "listing": "UL 1741 SB",
        "topology": "hybrid",
        "spec_sheet": "inverters/EG4-18KPV-12LV-Spec-Sheet.pdf",
        "keywords": ["eg4", "18kpv", "18k"],
    },
    {
        "id": "eg4-flexboss21",
        "manufacturer": "EG4",
        "model": "FlexBoss21",
        "label": "EG4 FlexBoss21",
        "quantity_default": 1,
        "continuous_ac_w": 16000,
        "continuous_ac_a": 66.7,
        "max_ac_a": 66.7,
        "nominal_vac": 240,
        "max_pv_w": 21000,
        "max_voc": 600,
        "mppt_count": 3,
        "max_imp_per_mppt": 26,
        "passthrough_a": 200,
        "parallel_capable": True,
        "max_parallel": 16,
        "listing": "UL 1741 SB",
        "topology": "hybrid",
        "spec_sheet": "inverters/EG4-FlexBoss21-Spec-Sheet.pdf",
        "keywords": ["eg4", "flexboss", "21"],
    },
    {
        "id": "enphase-iq8plus",
        "manufacturer": "Enphase",
        "model": "IQ8+",
        "label": "Enphase IQ8+ (microinverter)",
        "quantity_default": 1,  # per module typically
        "continuous_ac_w": 290,
        "continuous_ac_a": 1.21,
        "max_ac_a": 1.21,
        "nominal_vac": 240,
        "max_pv_w": 440,
        "max_voc": 60,
        "mppt_count": 1,
        "max_imp_per_mppt": 12,
        "passthrough_a": None,
        "parallel_capable": True,
        "max_parallel": 999,
        "listing": "UL 1741",
        "topology": "micro",
        "spec_sheet": None,
        "keywords": ["enphase", "iq8", "micro"],
    },
    {
        "id": "enphase-iq8m",
        "manufacturer": "Enphase",
        "model": "IQ8M",
        "label": "Enphase IQ8M (microinverter)",
        "quantity_default": 1,
        "continuous_ac_w": 325,
        "continuous_ac_a": 1.35,
        "max_ac_a": 1.35,
        "nominal_vac": 240,
        "max_pv_w": 480,
        "max_voc": 60,
        "mppt_count": 1,
        "max_imp_per_mppt": 12,
        "passthrough_a": None,
        "parallel_capable": True,
        "max_parallel": 999,
        "listing": "UL 1741",
        "topology": "micro",
        "spec_sheet": None,
        "keywords": ["enphase", "iq8m", "micro"],
    },
    {
        "id": "solaredge-se7600h",
        "manufacturer": "SolarEdge",
        "model": "SE7600H",
        "label": "SolarEdge SE7600H HD-Wave",
        "quantity_default": 1,
        "continuous_ac_w": 7600,
        "continuous_ac_a": 32,
        "max_ac_a": 32,
        "nominal_vac": 240,
        "max_pv_w": 11850,
        "max_voc": 480,
        "mppt_count": 1,
        "max_imp_per_mppt": 20,
        "passthrough_a": None,
        "parallel_capable": False,
        "max_parallel": 1,
        "listing": "UL 1741",
        "topology": "string_optimizer",
        "spec_sheet": None,
        "keywords": ["solaredge", "se7600", "hd-wave"],
    },
]

# ── Batteries ────────────────────────────────────────────────────────────
BATTERIES: list[dict[str, Any]] = [
    {
        "id": "eg4-powerpro-14-3",
        "manufacturer": "EG4",
        "model": "PowerPro 14.3 kWh WallMount AW",
        "label": "EG4 PowerPro 14.3 kWh All-Weather",
        "usable_kwh": 14.3,
        "nominal_v": 48,
        "max_charge_a": 200,
        "max_discharge_a": 200,
        "spec_sheet": "batteries/EG4-14.3kWh-PowerPro-WallMount-AW-Spec-Sheet.pdf",
        "keywords": ["eg4", "powerpro", "14.3", "wallmount"],
    },
    {
        "id": "eg4-wallmount-314",
        "manufacturer": "EG4",
        "model": "WallMount 314Ah Indoor",
        "label": "EG4 WallMount 314Ah Indoor",
        "usable_kwh": 14.3,
        "nominal_v": 51.2,
        "max_charge_a": 200,
        "max_discharge_a": 200,
        "spec_sheet": "batteries/EG4-WallMount-314Ah-Indoor-Battery-Spec-Sheet.pdf",
        "keywords": ["eg4", "314", "wallmount", "indoor"],
    },
    {
        "id": "tesla-powerwall-3",
        "manufacturer": "Tesla",
        "model": "Powerwall 3",
        "label": "Tesla Powerwall 3",
        "usable_kwh": 13.5,
        "nominal_v": 50,
        "max_charge_a": None,
        "max_discharge_a": None,
        "spec_sheet": None,
        "keywords": ["tesla", "powerwall", "pw3"],
    },
    {
        "id": "dpc-stack-15-30",
        "manufacturer": "Duracell Power Center",
        "model": "Stack 15-30",
        "label": "DPC Stack 15–30 kWh",
        "usable_kwh": 30.0,
        "nominal_v": 48,
        "max_charge_a": None,
        "max_discharge_a": None,
        "spec_sheet": None,
        "keywords": ["duracell", "dpc", "stack"],
    },
    {
        "id": "none",
        "manufacturer": "—",
        "model": "None",
        "label": "No battery",
        "usable_kwh": 0,
        "nominal_v": 0,
        "max_charge_a": None,
        "max_discharge_a": None,
        "spec_sheet": None,
        "keywords": ["none", "grid-tie"],
    },
]

# ── Racking ──────────────────────────────────────────────────────────────
RACKING: list[dict[str, Any]] = [
    {
        "id": "ironridge-xr100-ff2",
        "manufacturer": "IronRidge",
        "rail_model": "XR-100",
        "attachment": "FlashFoot 2",
        "label": "IronRidge XR-100 + FlashFoot 2",
        "lag_size": '5/16" x 4.75" SS',
        "max_attachment_spacing_in": 48,
        "spec_sheets": [
            "racking/IronRidge_Cut_Sheet_XR100_Rail.pdf",
            "racking/IronRidge_Cut_Sheet_FlashFoot2.pdf",
            "racking/IronRidge_FlashFoot2_Installation_Manual.pdf",
        ],
        "keywords": ["ironridge", "xr100", "flashfoot"],
    },
    {
        "id": "ironridge-xr10-ff2",
        "manufacturer": "IronRidge",
        "rail_model": "XR-10",
        "attachment": "FlashFoot 2",
        "label": "IronRidge XR-10 + FlashFoot 2",
        "lag_size": '5/16" x 4.75" SS',
        "max_attachment_spacing_in": 48,
        "spec_sheets": [
            "racking/IronRidge_Cut_Sheet_XR10_Rail.pdf",
            "racking/IronRidge_Cut_Sheet_FlashFoot2.pdf",
        ],
        "keywords": ["ironridge", "xr10", "flashfoot"],
    },
    {
        "id": "ironridge-xr100-halo",
        "manufacturer": "IronRidge",
        "rail_model": "XR-100",
        "attachment": "QuickMount HUG Halo UltraGrip",
        "label": "IronRidge XR-100 + Halo UltraGrip",
        "lag_size": '5/16" x 4.75" SS',
        "max_attachment_spacing_in": 48,
        "spec_sheets": [
            "racking/IronRidge_Cut_Sheet_XR100_Rail.pdf",
            "racking/IronRidge_QuickMount_Cut_Sheet_HUG_Halo_UltraGrip.pdf",
        ],
        "keywords": ["ironridge", "halo", "hug"],
    },
]


def catalog_payload() -> dict[str, Any]:
    return {
        "modules": MODULES,
        "inverters": INVERTERS,
        "batteries": BATTERIES,
        "racking": RACKING,
        "version": "1.0.0",
        "note": "Approved materials for dropdown selection — electrical nameplates baked in",
    }


def find_module(query: str) -> Optional[dict[str, Any]]:
    return _find(MODULES, query)


def find_inverter(query: str) -> Optional[dict[str, Any]]:
    return _find(INVERTERS, query)


def find_battery(query: str) -> Optional[dict[str, Any]]:
    return _find(BATTERIES, query)


def find_racking(query: str) -> Optional[dict[str, Any]]:
    return _find(RACKING, query)


def _find(items: list[dict[str, Any]], query: str) -> Optional[dict[str, Any]]:
    if not query:
        return None
    q = query.lower().strip()
    # exact id
    for it in items:
        if it.get("id") == q:
            return it
    # model / label
    for it in items:
        if it.get("model", "").lower() == q or it.get("label", "").lower() == q:
            return it
    # keywords / contains
    best = None
    best_score = 0
    for it in items:
        score = 0
        hay = " ".join(
            [
                it.get("id", ""),
                it.get("model", ""),
                it.get("label", ""),
                it.get("manufacturer", ""),
                " ".join(it.get("keywords") or []),
            ]
        ).lower()
        if q in hay:
            score += 5
        for kw in it.get("keywords") or []:
            if kw in q or q in kw:
                score += 2
        if score > best_score:
            best_score = score
            best = it
    return best if best_score > 0 else None
