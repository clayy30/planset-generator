"""High-quality starter projects — not toy examples."""

from __future__ import annotations

from .models import (
    Address,
    AmbientDesign,
    ArrayLayout,
    BackupMode,
    BatterySpec,
    CriticalLoad,
    DesignCriteria,
    InterconnectionMethod,
    InverterSpec,
    ModuleSpec,
    ProjectInput,
    ProjectMeta,
    ServiceSpec,
    StringDesign,
    WireSegment,
)


def duracell_400a_half_home() -> ProjectInput:
    return ProjectInput(
        custom_title="PHOTOVOLTAIC / HYBRID ENERGY STORAGE SYSTEM",
        meta=ProjectMeta(
            project_name="DPC Max Hybrid 15 — 400A Dual Disco",
            customer_name="Sample Customer",
            address=Address(
                line1="123 Example Rd",
                city="Guyton",
                state="GA",
                zip="31312",
                apn="TBD",
                latitude=32.34,
                longitude=-81.39,
            ),
            utility="Georgia Power / EMC as applicable",
            ahj="Effingham County",
            designer="Savannah Solar Power — Planset Generator",
            company="Savannah Solar Power",
            company_address="Savannah, GA",
            revision="0",
            revision_note="INITIAL RELEASE",
        ),
        criteria=DesignCriteria(
            roof_frame='2"x6" rafters @ 24" O.C.',
            wind_speed_mph=131,
            wind_exposure="B",
            attic_run_required=True,
        ),
        ambient=AmbientDesign(record_low_c=-5, high_2pct_c=35),
        modules=[
            ModuleSpec(
                manufacturer="Generic Premium",
                model="450W-144HC",
                quantity=24,
                pmax_w=450,
                vmp=41.5,
                imp=10.85,
                voc=49.5,
                isc=11.5,
                voc_temp_coeff_pct_per_c=-0.27,
                length_in=82.4,
                width_in=44.6,
            )
        ],
        inverters=[
            InverterSpec(
                manufacturer="Duracell Power Center",
                model="Max Hybrid 15",
                quantity=1,
                continuous_ac_w=15000,
                continuous_ac_a=62.5,
                max_ac_a=62.5,
                nominal_vac=240,
                max_pv_w=19500,
                max_voc=500,
                mppt_count=3,
                max_imp_per_mppt=26,
                passthrough_a=200,
                battery_cont_w=12000,
                parallel_capable=True,
                max_parallel=12,
                ne_ma="NEMA 3R / IP65",
                listing="UL 1741 / IEEE 1547a",
            )
        ],
        batteries=[
            BatterySpec(
                manufacturer="Duracell Power Center",
                model="Stack 15-30 (30 kWh kit)",
                quantity=1,
                usable_kwh=30,
                nominal_v=48,
            )
        ],
        service=ServiceSpec(
            service_a=400,
            phase="1Ø 3W",
            voltage="120/240V",
            main_breaker_a=400,
            busbar_a=400,
            num_disconnects=2,
            disconnect_rating_a=200,
            interconnection=InterconnectionMethod.DUAL_DISCO_HYBRID,
            backup_mode=BackupMode.HALF_HOME,
            ac_disco_a=200,
            production_meter=False,
        ),
        strings=[
            StringDesign(
                name="MPPT1-S1",
                module_model="450W-144HC",
                modules_in_series=8,
                parallel_strings=1,
                inverter_index=0,
                mppt_index=1,
            ),
            StringDesign(
                name="MPPT2-S1",
                module_model="450W-144HC",
                modules_in_series=8,
                parallel_strings=1,
                inverter_index=0,
                mppt_index=2,
            ),
            StringDesign(
                name="MPPT3-S1",
                module_model="450W-144HC",
                modules_in_series=8,
                parallel_strings=1,
                inverter_index=0,
                mppt_index=3,
            ),
        ],
        array=ArrayLayout(
            roof_planes=2,
            modules_per_plane=[12, 12],
            azimuth_deg=[180, 180],
            tilt_deg=[22, 22],
            racking="IronRidge XR-100 / FlashFoot 2 or AHJ-approved equal",
        ),
        wires=[
            WireSegment(
                name="W1",
                from_equip="Array JBs",
                to_equip="Max Hybrid 15 PV MPPTs",
                conductors="#10 AWG PV wire · 3 strings · outdoor UV",
                ocpd="Per string if required",
                notes="Voc_cold per string on PV-4",
            ),
            WireSegment(
                name="W2",
                from_equip="Battery stack",
                to_equip="Hybrid BAT+/−",
                conductors="Mfr 200A-class DC kit",
                ocpd="Integrated 200A×2 bat disco",
            ),
            WireSegment(
                name="W3",
                from_equip="200A Disco #1",
                to_equip="Hybrid GRID",
                conductors="200A feeder · 4-wire Cu/Al 75°C",
                ocpd="200A disco",
            ),
            WireSegment(
                name="W4",
                from_equip="Hybrid LOAD",
                to_equip="Backed-up Panel #1",
                conductors="200A feeder · 4-wire",
                ocpd="Panel main ≤200A",
            ),
        ],
        critical_loads=[
            CriticalLoad(name="Refrigerator", va=800, continuous=True),
            CriticalLoad(name="Well / pressure", va=1500, continuous=False),
            CriticalLoad(name="Network / ONT", va=200, continuous=True),
            CriticalLoad(name="Selected lighting", va=600, continuous=True),
        ],
    )


def eg4_gridboss_sample() -> ProjectInput:
    return ProjectInput(
        custom_title="PHOTOVOLTAIC ROOF MOUNT + HYBRID ESS (GRIDBOSS)",
        meta=ProjectMeta(
            project_name="EG4 FlexBoss / GridBOSS Sample",
            customer_name="Jason Phillips (template)",
            address=Address(
                line1="30 Houston St",
                city="Savannah",
                state="GA",
                zip="31401",
                apn="20005 13005B",
            ),
            utility="SOCO",
            ahj="City of Savannah",
            designer="Savannah Solar Power — Planset Generator",
            company="Savannah Solar Power",
            revision="0",
            revision_note="GENERATOR PRESET",
        ),
        modules=[
            ModuleSpec(
                manufacturer="Canadian Solar",
                model="CS6.1-54TM-450H",
                quantity=12,
                pmax_w=450,
                vmp=34.0,
                imp=13.24,
                voc=40.5,
                isc=14.0,
                voc_temp_coeff_pct_per_c=-0.26,
            )
        ],
        inverters=[
            InverterSpec(
                manufacturer="EG4",
                model="FlexBoss21 / IV-16000-HYB-AW",
                quantity=1,
                continuous_ac_w=12000,
                continuous_ac_a=50,
                max_pv_w=21000,
                max_voc=600,
                mppt_count=3,
                max_imp_per_mppt=26,
                passthrough_a=200,
                battery_cont_w=12000,
                listing="UL 1741 SB",
                ne_ma="NEMA 4X outdoor hybrid",
            )
        ],
        batteries=[
            BatterySpec(
                manufacturer="EG4",
                model="WallMount Indoor 280Ah",
                quantity=1,
                usable_kwh=14.3,
                nominal_v=51.2,
            )
        ],
        service=ServiceSpec(
            service_a=200,
            main_breaker_a=200,
            busbar_a=200,
            num_disconnects=1,
            disconnect_rating_a=200,
            interconnection=InterconnectionMethod.GRIDBOSS,
            backup_mode=BackupMode.WHOLE_PANEL,
            ac_disco_a=200,
        ),
        strings=[
            StringDesign(
                name="String A",
                module_model="CS6.1-54TM-450H",
                modules_in_series=6,
                parallel_strings=1,
                mppt_index=1,
            ),
            StringDesign(
                name="String B",
                module_model="CS6.1-54TM-450H",
                modules_in_series=6,
                parallel_strings=1,
                mppt_index=2,
            ),
        ],
        array=ArrayLayout(roof_planes=1, modules_per_plane=[12], azimuth_deg=[185], tilt_deg=[20]),
    )
