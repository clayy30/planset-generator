"""Project data model for permit-grade PV / hybrid ESS plansets."""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class InterconnectionMethod(str, Enum):
    BACKFEED = "backfeed_breaker"
    LOAD_SIDE_HYBRID = "load_side_hybrid"
    SUPPLY_SIDE_TAP = "supply_side_tap"
    FEEDER_TAP = "feeder_tap"
    GRIDBOSS = "gridboss_mid"
    DUAL_DISCO_HYBRID = "dual_disco_hybrid"


class BackupMode(str, Enum):
    NONE = "none"
    CRITICAL_LOADS = "critical_loads"
    WHOLE_PANEL = "whole_panel"
    HALF_HOME = "half_home"  # one of two 200A discos
    FULL_DUAL_DISCO = "full_dual_disco"  # both 200A paths


class RoofType(str, Enum):
    COMP_SHINGLE = "comp_shingle"
    METAL = "metal"
    TILE = "tile"
    FLAT = "flat"
    OTHER = "other"


class Address(BaseModel):
    line1: str
    line2: str = ""
    city: str
    state: str = "GA"
    zip: str
    apn: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ProjectMeta(BaseModel):
    project_name: str
    customer_name: str
    address: Address
    utility: str = ""
    ahj: str = ""
    designer: str = "Savannah Solar Power"
    company: str = "Savannah Solar Power"
    company_address: str = ""
    prepared_date: str = ""
    revision: str = "0"
    revision_note: str = "INITIAL RELEASE"
    governing_codes: list[str] = Field(
        default_factory=lambda: [
            "2018 International Building Code (IBC)",
            "2018 International Residential Code (IRC)",
            "2018 International Fire Code (IFC)",
            "2020 / 2023 National Electrical Code (NEC) as adopted by AHJ",
        ]
    )


class DesignCriteria(BaseModel):
    roof_type: RoofType = RoofType.COMP_SHINGLE
    roof_layers: int = 1
    roof_frame: str = '2"x6" rafters @ 24" O.C.'
    stories: int = 1
    snow_load_psf: float = 0
    wind_speed_mph: float = 130
    wind_exposure: str = "B"
    risk_category: str = "II"
    attic_run_required: bool = True
    fire_setback_ridge_in: float = 36
    fire_setback_eave_in: float = 18
    fire_setback_hip_valley_in: float = 18


class ModuleSpec(BaseModel):
    manufacturer: str
    model: str
    quantity: int = Field(gt=0)
    pmax_w: float
    vmp: float
    imp: float
    voc: float
    isc: float
    voc_temp_coeff_pct_per_c: float = -0.28  # %/°C
    length_in: float = 89.7
    width_in: float = 44.6
    depth_in: float = 1.4
    bifacial: bool = False


class InverterSpec(BaseModel):
    manufacturer: str
    model: str
    quantity: int = 1
    continuous_ac_w: float
    continuous_ac_a: float
    max_ac_a: float | None = None
    nominal_vac: float = 240
    max_pv_w: float | None = None
    max_voc: float | None = None
    mppt_count: int = 1
    max_imp_per_mppt: float | None = None
    passthrough_a: float | None = None  # hybrid grid passthrough
    battery_cont_w: float | None = None
    parallel_capable: bool = False
    max_parallel: int = 1
    ne_ma: str = "NEMA 3R"
    listing: str = "UL 1741"


class BatterySpec(BaseModel):
    manufacturer: str
    model: str
    quantity: int = 0
    usable_kwh: float = 0
    nominal_v: float = 48
    max_charge_a: float | None = None
    max_discharge_a: float | None = None


class ServiceSpec(BaseModel):
    service_a: int = 200
    phase: str = "1Ø 3W"
    voltage: str = "120/240V"
    main_breaker_a: int = 200
    busbar_a: int | None = None  # if known
    num_disconnects: int = 1
    disconnect_rating_a: int = 200
    existing_main_panel: bool = True
    interconnection: InterconnectionMethod = InterconnectionMethod.BACKFEED
    backup_mode: BackupMode = BackupMode.NONE
    backfeed_breaker_a: int | None = None
    ac_disco_a: int | None = None
    production_meter: bool = False
    export_limit_a: float | None = None


class StringDesign(BaseModel):
    """One PV string landing on an MPPT."""
    name: str = "String 1"
    module_model: str
    modules_in_series: int
    parallel_strings: int = 1
    inverter_index: int = 0
    mppt_index: int = 1


class WireSegment(BaseModel):
    name: str
    from_equip: str
    to_equip: str
    conductors: str  # e.g. "(2) #6 AWG Cu THHN + #10 EGC in 3/4\" EMT"
    ocpd: str = ""
    notes: str = ""


class CriticalLoad(BaseModel):
    name: str
    va: float
    continuous: bool = True


class ArrayLayout(BaseModel):
    roof_planes: int = 1
    modules_per_plane: list[int] = Field(default_factory=lambda: [12])
    azimuth_deg: list[float] = Field(default_factory=lambda: [180.0])
    tilt_deg: list[float] = Field(default_factory=lambda: [22.0])
    racking: str = "IronRidge XR / FlashFoot 2 or AHJ-approved equal"
    attachment: str = '5/16" x 4.75" SS lag, min 2-1/2" embedment into rafter'


class AmbientDesign(BaseModel):
    record_low_c: float = -5.0
    high_2pct_c: float = 35.0
    roof_adder_c: float = 30.0  # rooftop raceway temp adder context


class ProjectInput(BaseModel):
    meta: ProjectMeta
    criteria: DesignCriteria = Field(default_factory=DesignCriteria)
    ambient: AmbientDesign = Field(default_factory=AmbientDesign)
    modules: list[ModuleSpec]
    inverters: list[InverterSpec]
    batteries: list[BatterySpec] = Field(default_factory=list)
    service: ServiceSpec = Field(default_factory=ServiceSpec)
    strings: list[StringDesign] = Field(default_factory=list)
    array: ArrayLayout = Field(default_factory=ArrayLayout)
    wires: list[WireSegment] = Field(default_factory=list)
    critical_loads: list[CriticalLoad] = Field(default_factory=list)
    notes_construction: list[str] = Field(default_factory=list)
    notes_electrical: list[str] = Field(default_factory=list)
    custom_title: str = "PHOTOVOLTAIC / ENERGY STORAGE SYSTEM"

    @field_validator("modules")
    @classmethod
    def need_modules(cls, v: list[ModuleSpec]) -> list[ModuleSpec]:
        if not v:
            raise ValueError("At least one module type required")
        return v


class ProjectRecord(BaseModel):
    id: str
    created_at: str
    updated_at: str
    project: ProjectInput
