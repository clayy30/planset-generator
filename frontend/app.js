/* Planset Generator UI */

let step = 0;
let lastProjectId = null;

const $ = (id) => document.getElementById(id);
const val = (id) => $(id).value;
const num = (id) => {
  const v = $(id).value;
  if (v === "" || v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};

function buildProject() {
  const series = num("str_series") || 8;
  const par = num("str_par") || 1;
  const count = num("str_count") || 1;
  const model = val("mod_model");
  const strings = [];
  for (let i = 0; i < count; i++) {
    strings.push({
      name: `String ${i + 1}`,
      module_model: model,
      modules_in_series: series,
      parallel_strings: par,
      inverter_index: 0,
      mppt_index: i + 1,
    });
  }

  const backfeed = num("backfeed_breaker_a");
  const bus = num("busbar_a");

  const planes = [
    {
      name: val("p1_name") || "ROOF #1",
      eave_width_ft: num("p1_eave") || 32,
      ridge_depth_ft: num("p1_depth") || 16,
      tilt_deg: num("p1_tilt") || 22,
      azimuth_deg: num("p1_az") || 180,
      module_count: num("p1_mods") || 0,
      rafter_size: '2"x6"',
      rafter_spacing_in: num("p1_rafter") || 24,
      setback_ridge_in: num("p1_sb_ridge") || 36,
      setback_eave_in: num("p1_sb_eave") || 18,
      setback_left_in: num("p1_sb_l") || 18,
      setback_right_in: num("p1_sb_r") || 18,
      portrait: true,
    },
  ];
  const p2mods = num("p2_mods") || 0;
  if (p2mods > 0) {
    planes.push({
      name: val("p2_name") || "ROOF #2",
      eave_width_ft: num("p2_eave") || 32,
      ridge_depth_ft: num("p2_depth") || 16,
      tilt_deg: num("p2_tilt") || 22,
      azimuth_deg: num("p2_az") || 180,
      module_count: p2mods,
      rafter_size: '2"x6"',
      rafter_spacing_in: num("p1_rafter") || 24,
      setback_ridge_in: num("p1_sb_ridge") || 36,
      setback_eave_in: num("p1_sb_eave") || 18,
      setback_left_in: 18,
      setback_right_in: 18,
      portrait: true,
    });
  }

  return {
    custom_title: "PHOTOVOLTAIC / ENERGY STORAGE SYSTEM",
    meta: {
      project_name: val("project_name"),
      customer_name: val("customer_name"),
      address: {
        line1: val("line1"),
        line2: "",
        city: val("city"),
        state: val("state"),
        zip: val("zip"),
        apn: val("apn"),
        county: val("county") || "",
        owner_of_record: val("owner_of_record") || "",
        acres: num("acres"),
        latitude: num("latitude"),
        longitude: num("longitude"),
      },
      utility: val("utility"),
      ahj: val("ahj"),
      designer: val("designer"),
      company: val("company"),
      revision: val("revision") || "0",
      revision_note: "INITIAL RELEASE",
    },
    criteria: {
      roof_frame: val("roof_frame"),
      wind_speed_mph: num("wind_speed_mph") || 130,
      wind_exposure: val("wind_exposure") || "B",
      attic_run_required: true,
      fire_setback_ridge_in: num("p1_sb_ridge") || 36,
      fire_setback_eave_in: num("p1_sb_eave") || 18,
    },
    ambient: {
      record_low_c: num("record_low_c") ?? -5,
      high_2pct_c: 35,
    },
    modules: [
      {
        manufacturer: val("mod_mfr"),
        model: model,
        quantity: num("mod_qty") || 1,
        pmax_w: num("mod_pmax") || 400,
        vmp: num("mod_vmp") || 40,
        imp: num("mod_imp") || 10,
        voc: num("mod_voc") || 48,
        isc: num("mod_isc") || 11,
        voc_temp_coeff_pct_per_c: num("mod_coeff") ?? -0.28,
        length_in: 82.4,
        width_in: 44.6,
        weight_lb: 48.5,
      },
    ],
    inverters: [
      {
        manufacturer: val("inv_mfr"),
        model: val("inv_model"),
        quantity: num("inv_qty") || 1,
        continuous_ac_w: num("inv_w") || 10000,
        continuous_ac_a: num("inv_a") || 40,
        max_pv_w: num("inv_max_pv"),
        max_voc: num("inv_max_voc"),
        mppt_count: num("inv_mppt") || 1,
        max_imp_per_mppt: num("inv_imp_mppt"),
        passthrough_a: num("inv_pass"),
        listing: val("inv_listing") || "UL 1741",
        ne_ma: "NEMA 3R",
        parallel_capable: true,
        max_parallel: 12,
      },
    ],
    batteries: [
      {
        manufacturer: val("bat_mfr"),
        model: val("bat_model"),
        quantity: num("bat_qty") || 0,
        usable_kwh: num("bat_kwh") || 0,
        nominal_v: 48,
      },
    ],
    service: {
      service_a: Number(val("service_a")),
      phase: "1Ø 3W",
      voltage: "120/240V",
      main_breaker_a: num("main_breaker_a") || 200,
      busbar_a: bus,
      num_disconnects: num("num_disconnects") || 1,
      disconnect_rating_a: num("disconnect_rating_a") || 200,
      interconnection: val("interconnection"),
      backup_mode: val("backup_mode"),
      backfeed_breaker_a: backfeed,
      ac_disco_a: num("ac_disco_a"),
      production_meter: $("production_meter").checked,
    },
    strings,
    array: {
      planes,
      roof_planes: planes.length,
      modules_per_plane: planes.map((p) => p.module_count),
      azimuth_deg: planes.map((p) => p.azimuth_deg),
      tilt_deg: planes.map((p) => p.tilt_deg),
      racking: val("rack_label") || "IronRidge XR-100 / FlashFoot 2 or AHJ-approved equal",
      attachment: window.__rackAttachment || '5/16" x 4.75" SS lag, min 2-1/2" embedment into rafter',
      structural: {
        racking_mfr: window.__rackMfr || "IronRidge",
        rail_model: window.__rackRail || "XR-100",
        attachment_hardware: window.__rackAttachment || "FlashFoot 2",
        lag_size: window.__rackLag || '5/16" x 4.75" SS',
        lag_embedment_in: 2.5,
        max_attachment_spacing_in: window.__rackSpacing || 48,
        max_dead_load_psf: 5.0,
        span_table_ref: "Manufacturer span tables for site wind/exposure",
      },
    },
  };
}

function applyPreset(data) {
  const p = data;
  $("project_name").value = p.meta.project_name;
  $("customer_name").value = p.meta.customer_name;
  $("line1").value = p.meta.address.line1;
  $("city").value = p.meta.address.city;
  $("state").value = p.meta.address.state;
  $("zip").value = p.meta.address.zip;
  $("apn").value = p.meta.address.apn || "";
  $("county").value = p.meta.address.county || "";
  $("owner_of_record").value = p.meta.address.owner_of_record || "";
  $("acres").value = p.meta.address.acres ?? "";
  $("latitude").value = p.meta.address.latitude ?? "";
  $("longitude").value = p.meta.address.longitude ?? "";
  $("utility").value = p.meta.utility || "";
  $("ahj").value = p.meta.ahj || "";
  $("designer").value = p.meta.designer || "";
  $("company").value = p.meta.company || "";

  $("service_a").value = String(p.service.service_a);
  $("main_breaker_a").value = p.service.main_breaker_a;
  $("busbar_a").value = p.service.busbar_a ?? "";
  $("num_disconnects").value = p.service.num_disconnects;
  $("disconnect_rating_a").value = p.service.disconnect_rating_a;
  $("interconnection").value = p.service.interconnection;
  $("backup_mode").value = p.service.backup_mode;
  $("backfeed_breaker_a").value = p.service.backfeed_breaker_a ?? "";
  $("ac_disco_a").value = p.service.ac_disco_a ?? "";
  $("production_meter").checked = !!p.service.production_meter;

  if (p.criteria) {
    $("roof_frame").value = p.criteria.roof_frame || $("roof_frame").value;
    $("wind_speed_mph").value = p.criteria.wind_speed_mph ?? 130;
    $("wind_exposure").value = p.criteria.wind_exposure || "B";
  }
  if (p.ambient) $("record_low_c").value = p.ambient.record_low_c ?? -5;

  const m = p.modules[0];
  $("mod_mfr").value = m.manufacturer;
  $("mod_model").value = m.model;
  $("mod_qty").value = m.quantity;
  $("mod_pmax").value = m.pmax_w;
  $("mod_vmp").value = m.vmp;
  $("mod_imp").value = m.imp;
  $("mod_voc").value = m.voc;
  $("mod_isc").value = m.isc;
  $("mod_coeff").value = m.voc_temp_coeff_pct_per_c;

  const inv = p.inverters[0];
  $("inv_mfr").value = inv.manufacturer;
  $("inv_model").value = inv.model;
  $("inv_qty").value = inv.quantity;
  $("inv_w").value = inv.continuous_ac_w;
  $("inv_a").value = inv.continuous_ac_a;
  $("inv_max_pv").value = inv.max_pv_w ?? "";
  $("inv_max_voc").value = inv.max_voc ?? "";
  $("inv_mppt").value = inv.mppt_count ?? 1;
  $("inv_imp_mppt").value = inv.max_imp_per_mppt ?? "";
  $("inv_pass").value = inv.passthrough_a ?? "";
  $("inv_listing").value = inv.listing || "";

  if (p.batteries && p.batteries[0]) {
    const b = p.batteries[0];
    $("bat_mfr").value = b.manufacturer;
    $("bat_model").value = b.model;
    $("bat_qty").value = b.quantity;
    $("bat_kwh").value = b.usable_kwh;
  }

  if (p.strings && p.strings.length) {
    $("str_series").value = p.strings[0].modules_in_series;
    $("str_par").value = p.strings[0].parallel_strings;
    $("str_count").value = p.strings.length;
  }
  if (p.array && p.array.planes && p.array.planes.length) {
    const a = p.array.planes[0];
    $("p1_name").value = a.name || "ROOF #1";
    $("p1_mods").value = a.module_count;
    $("p1_eave").value = a.eave_width_ft;
    $("p1_depth").value = a.ridge_depth_ft;
    $("p1_tilt").value = a.tilt_deg;
    $("p1_az").value = a.azimuth_deg;
    $("p1_sb_ridge").value = a.setback_ridge_in ?? 36;
    $("p1_sb_eave").value = a.setback_eave_in ?? 18;
    $("p1_sb_l").value = a.setback_left_in ?? 18;
    $("p1_sb_r").value = a.setback_right_in ?? 18;
    $("p1_rafter").value = a.rafter_spacing_in ?? 24;
    if (p.array.planes[1]) {
      const b = p.array.planes[1];
      $("p2_name").value = b.name || "ROOF #2";
      $("p2_mods").value = b.module_count;
      $("p2_eave").value = b.eave_width_ft;
      $("p2_depth").value = b.ridge_depth_ft;
      $("p2_tilt").value = b.tilt_deg;
      $("p2_az").value = b.azimuth_deg;
    } else {
      $("p2_mods").value = 0;
    }
  }
  updateSnapshot();
}

function setStep(n) {
  step = Math.max(0, Math.min(5, n));
  document.querySelectorAll(".step").forEach((el) => {
    el.classList.toggle("hidden", Number(el.dataset.step) !== step);
  });
  document.querySelectorAll(".steps button").forEach((btn) => {
    btn.classList.toggle("active", Number(btn.dataset.step) === step);
  });
  if (step === 5) updateReview();
  updateSnapshot();
}

function updateSnapshot() {
  try {
    const p = buildProject();
    const dc = (p.modules[0].quantity * p.modules[0].pmax_w) / 1000;
    const ac = (p.inverters[0].quantity * p.inverters[0].continuous_ac_w) / 1000;
    $("snapshot").textContent = [
      p.meta.project_name,
      p.meta.customer_name,
      `${p.meta.address.line1}, ${p.meta.address.city}`,
      `Service ${p.service.service_a}A · ${p.service.num_disconnects}×${p.service.disconnect_rating_a}A`,
      `IC: ${p.service.interconnection}`,
      `Backup: ${p.service.backup_mode}`,
      `Modules: ${p.modules[0].quantity} × ${p.modules[0].pmax_w}W = ${dc.toFixed(2)} kWDC`,
      `Inverter: ${p.inverters[0].model} ×${p.inverters[0].quantity} = ${ac.toFixed(2)} kWAC cont.`,
      `Battery: ${p.batteries[0].quantity} × ${p.batteries[0].usable_kwh} kWh`,
    ].join("\n");
  } catch (e) {
    $("snapshot").textContent = String(e);
  }
}

function updateReview() {
  const p = buildProject();
  const dc = (p.modules[0].quantity * p.modules[0].pmax_w) / 1000;
  $("review-summary").innerHTML = `
    <p><strong>${p.meta.project_name}</strong> — ${p.meta.customer_name}</p>
    <p>${p.meta.address.line1}, ${p.meta.address.city}, ${p.meta.address.state} ${p.meta.address.zip}</p>
    <p>Utility: ${p.meta.utility || "—"} · AHJ: ${p.meta.ahj || "—"}</p>
    <p>Service ${p.service.service_a}A · ${p.service.backup_mode.replaceAll("_", " ")} · ${p.service.interconnection.replaceAll("_", " ")}</p>
    <p>${p.modules[0].quantity} modules · ${dc.toFixed(3)} kWDC · ${p.inverters[0].model} · ${p.batteries[0].usable_kwh * p.batteries[0].quantity} kWh ESS</p>
    <p class="hint">Sheets: PV-0 Cover · PV-1 Site · PV-2 Array · PV-3 SLD · PV-4 Calcs · PV-5 Wire/BOM · PV-6 Labels · PV-7 QA</p>
  `;
}

async function previewCalcs() {
  const p = buildProject();
  $("calc-preview").textContent = "Calculating…";
  try {
    const res = await fetch("/api/preview-calcs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(p),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(JSON.stringify(data, null, 2));
    $("calc-preview").textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    $("calc-preview").textContent = "Error: " + e.message;
  }
}

async function generate() {
  const p = buildProject();
  const box = $("gen-result");
  box.classList.remove("hidden", "err");
  box.innerHTML = "Generating 8-sheet planset…";
  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(p),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(JSON.stringify(data, null, 2));
    lastProjectId = data.project_id;
    const warns =
      data.warnings && data.warnings.length
        ? `<p><strong>Warnings:</strong> ${data.warnings.join(" · ")}</p>`
        : `<p>No critical calc warnings.</p>`;
    const ap = data.appendix;
    const apHtml = ap
      ? `<p><strong>Equipment appendix:</strong> ${ap.count} matched cut sheets
         ${ap.docs && ap.docs.length ? "— " + ap.docs.map((d) => d.filename).slice(0, 6).join(", ") + (ap.docs.length > 6 ? "…" : "") : ""}</p>
         <p class="hint">Full PDFs: output/${data.project_id}/appendix/</p>`
      : "";
    box.innerHTML = `
      <p><strong>Planset ready</strong> (design sheets + auto-matched manufacturer specs).</p>
      <p><a href="${data.url}" target="_blank" rel="noopener">Open planset (print → PDF)</a></p>
      <p class="hint">Project ID: ${data.project_id}</p>
      ${apHtml}
      ${warns}
      <p class="hint">Print · 11×17 ANSI B landscape · includes PV-8 index + PV-A# cut-sheet rasters.</p>
    `;
    loadProjects();
  } catch (e) {
    box.classList.add("err");
    box.innerHTML = `<p><strong>Failed:</strong> ${e.message}</p>`;
  }
}

async function saveProject() {
  const p = buildProject();
  const res = await fetch("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(p),
  });
  const data = await res.json();
  if (!res.ok) {
    alert("Save failed: " + JSON.stringify(data));
    return;
  }
  lastProjectId = data.id;
  alert("Saved project " + data.id);
  loadProjects();
}

async function loadProjects() {
  try {
    const res = await fetch("/api/projects");
    const rows = await res.json();
    const ul = $("project-list");
    ul.innerHTML = "";
    rows.slice(0, 12).forEach((r) => {
      const li = document.createElement("li");
      li.textContent = `${r.project_name} — ${r.customer_name}`;
      li.title = r.id;
      li.onclick = async () => {
        const pr = await fetch("/api/projects/" + r.id).then((x) => x.json());
        applyPreset(pr.project);
        lastProjectId = r.id;
        setStep(5);
      };
      ul.appendChild(li);
    });
    if (!rows.length) ul.innerHTML = "<li style='cursor:default;opacity:0.6'>No saved projects yet</li>";
  } catch {
    /* ignore */
  }
}

/** Approved materials catalog from /api/materials */
let MATERIALS = { modules: [], inverters: [], batteries: [], racking: [] };

async function loadMaterialsCatalog() {
  try {
    const data = await fetch("/api/materials").then((r) => r.json());
    MATERIALS = data;
    fillSelect(
      "mod_catalog",
      data.modules || [],
      (m) => m.id,
      (m) => m.label || `${m.manufacturer} ${m.model}`
    );
    fillSelect(
      "inv_catalog",
      data.inverters || [],
      (m) => m.id,
      (m) => m.label || `${m.manufacturer} ${m.model}`
    );
    fillSelect(
      "bat_catalog",
      data.batteries || [],
      (m) => m.id,
      (m) => m.label || `${m.manufacturer} ${m.model}`
    );
    fillSelect(
      "rack_catalog",
      data.racking || [],
      (m) => m.id,
      (m) => m.label || `${m.manufacturer} ${m.rail_model}`
    );

    // Default selections if empty
    if ($("mod_catalog") && !$("mod_catalog").value && data.modules?.[0]) {
      $("mod_catalog").value = data.modules[0].id;
      applyModuleFromCatalog(data.modules[0].id);
    }
    if ($("inv_catalog") && !$("inv_catalog").value) {
      const dpc = (data.inverters || []).find((i) => i.id === "dpc-max-hybrid-15");
      if (dpc) {
        $("inv_catalog").value = dpc.id;
        applyInverterFromCatalog(dpc.id);
      }
    }
    if ($("bat_catalog") && data.batteries?.length) {
      const dpcBat =
        data.batteries.find((b) => b.id === "dpc-stack-15-30") || data.batteries[0];
      $("bat_catalog").value = dpcBat.id;
      applyBatteryFromCatalog(dpcBat.id);
    }
    if ($("rack_catalog") && data.racking?.[0]) {
      $("rack_catalog").value = data.racking[0].id;
      applyRackingFromCatalog(data.racking[0].id);
    }

    $("mod_catalog")?.addEventListener("change", (e) =>
      applyModuleFromCatalog(e.target.value)
    );
    $("inv_catalog")?.addEventListener("change", (e) =>
      applyInverterFromCatalog(e.target.value)
    );
    $("bat_catalog")?.addEventListener("change", (e) =>
      applyBatteryFromCatalog(e.target.value)
    );
    $("rack_catalog")?.addEventListener("change", (e) =>
      applyRackingFromCatalog(e.target.value)
    );
    updateSnapshot();
  } catch (e) {
    console.warn("Materials catalog failed", e);
  }
}

function fillSelect(id, items, valueFn, labelFn) {
  const el = $(id);
  if (!el) return;
  const keep = el.value;
  el.innerHTML = `<option value="">— Select —</option>`;
  items.forEach((it) => {
    const opt = document.createElement("option");
    opt.value = valueFn(it);
    opt.textContent = labelFn(it);
    el.appendChild(opt);
  });
  if (keep) el.value = keep;
}

function applyModuleFromCatalog(id) {
  const m = (MATERIALS.modules || []).find((x) => x.id === id);
  if (!m) return;
  $("mod_mfr").value = m.manufacturer;
  $("mod_model").value = m.model;
  $("mod_pmax").value = m.pmax_w;
  $("mod_vmp").value = m.vmp;
  $("mod_imp").value = m.imp;
  $("mod_voc").value = m.voc;
  $("mod_isc").value = m.isc;
  $("mod_coeff").value = m.voc_temp_coeff_pct_per_c;
  if ($("mod_spec")) $("mod_spec").value = m.spec_sheet || "(no local PDF linked)";
  updateSnapshot();
}

function applyInverterFromCatalog(id) {
  const inv = (MATERIALS.inverters || []).find((x) => x.id === id);
  if (!inv) return;
  $("inv_mfr").value = inv.manufacturer;
  $("inv_model").value = inv.model;
  $("inv_qty").value = inv.quantity_default || 1;
  $("inv_w").value = inv.continuous_ac_w;
  $("inv_a").value = inv.continuous_ac_a;
  $("inv_max_pv").value = inv.max_pv_w ?? "";
  $("inv_max_voc").value = inv.max_voc ?? "";
  $("inv_mppt").value = inv.mppt_count ?? 1;
  $("inv_imp_mppt").value = inv.max_imp_per_mppt ?? "";
  $("inv_pass").value = inv.passthrough_a ?? "";
  $("inv_listing").value = inv.listing || "UL 1741";
  updateSnapshot();
}

function applyBatteryFromCatalog(id) {
  const b = (MATERIALS.batteries || []).find((x) => x.id === id);
  if (!b) return;
  $("bat_mfr").value = b.manufacturer === "—" ? "" : b.manufacturer;
  $("bat_model").value = b.model === "None" ? "" : b.model;
  $("bat_qty").value = b.usable_kwh > 0 ? 1 : 0;
  $("bat_kwh").value = b.usable_kwh || 0;
  updateSnapshot();
}

function applyRackingFromCatalog(id) {
  const r = (MATERIALS.racking || []).find((x) => x.id === id);
  if (!r) return;
  if ($("rack_label")) $("rack_label").value = r.label;
  window.__rackMfr = r.manufacturer;
  window.__rackRail = r.rail_model;
  window.__rackAttachment = r.attachment;
  window.__rackLag = r.lag_size;
  window.__rackSpacing = r.max_attachment_spacing_in;
  updateSnapshot();
}

function syncCatalogSelectsFromFields() {
  const modModel = ($("mod_model")?.value || "").toLowerCase();
  const invModel = ($("inv_model")?.value || "").toLowerCase();
  const batModel = ($("bat_model")?.value || "").toLowerCase();
  const mod = (MATERIALS.modules || []).find(
    (m) =>
      m.model.toLowerCase() === modModel ||
      (m.keywords || []).some((k) => modModel.includes(k))
  );
  if (mod && $("mod_catalog")) $("mod_catalog").value = mod.id;
  const inv = (MATERIALS.inverters || []).find(
    (m) =>
      m.model.toLowerCase() === invModel ||
      (m.keywords || []).some((k) => invModel.includes(k))
  );
  if (inv && $("inv_catalog")) $("inv_catalog").value = inv.id;
  const bat = (MATERIALS.batteries || []).find(
    (m) =>
      m.model.toLowerCase() === batModel ||
      (m.keywords || []).some((k) => batModel.includes(k))
  );
  if (bat && $("bat_catalog")) $("bat_catalog").value = bat.id;
}

function wire() {
  document.querySelectorAll(".steps button").forEach((btn) => {
    btn.addEventListener("click", () => setStep(Number(btn.dataset.step)));
  });
  $("btn-prev").onclick = () => setStep(step - 1);
  $("btn-next").onclick = () => setStep(step + 1);
  $("btn-preview-calcs").onclick = previewCalcs;
  $("btn-generate").onclick = () => {
    setStep(5);
    generate();
  };
  $("btn-generate-2").onclick = generate;
  $("btn-save").onclick = saveProject;
  $("btn-load-list").onclick = loadProjects;
  $("btn-health").onclick = async () => {
    const h = await fetch("/api/health").then((r) => r.json());
    alert(h.commitment || JSON.stringify(h));
  };
  $("btn-preset-duracell").onclick = async () => {
    const p = await fetch("/api/presets/duracell-400a").then((r) => r.json());
    applyPreset(p);
    syncCatalogSelectsFromFields();
  };
  $("btn-preset-eg4").onclick = async () => {
    const p = await fetch("/api/presets/eg4-gridboss").then((r) => r.json());
    applyPreset(p);
    syncCatalogSelectsFromFields();
  };
  $("btn-gis").onclick = async () => {
    const box = $("gis-status");
    box.style.display = "block";
    box.textContent = "Querying GIS (geocode + county parcel layers)…";
    try {
      const q = new URLSearchParams({
        line1: val("line1"),
        city: val("city"),
        state: val("state"),
        zip: val("zip"),
      });
      const res = await fetch("/api/gis/lookup?" + q.toString());
      const data = await res.json();
      if (!res.ok) throw new Error(JSON.stringify(data));
      if (data.line1) $("line1").value = data.line1;
      if (data.city) $("city").value = data.city;
      if (data.state && data.state.length <= 2) $("state").value = data.state;
      if (data.zip) $("zip").value = data.zip;
      if (data.apn) $("apn").value = data.apn;
      if (data.county) $("county").value = data.county;
      if (data.owner) {
        $("owner_of_record").value = data.owner;
        if (!$("customer_name").value || $("customer_name").value === "Sample Customer") {
          $("customer_name").value = data.owner;
        }
      }
      if (data.acres != null) $("acres").value = data.acres;
      if (data.latitude != null) $("latitude").value = data.latitude;
      if (data.longitude != null) $("longitude").value = data.longitude;
      if (data.county) $("ahj").value = data.county;
      box.textContent = JSON.stringify(
        {
          matched: data.matched_address,
          apn: data.apn,
          owner: data.owner,
          county: data.county,
          acres: data.acres,
          lat: data.latitude,
          lon: data.longitude,
          source: data.source,
          warnings: data.warnings,
        },
        null,
        2
      );
      updateSnapshot();
    } catch (e) {
      box.textContent = "GIS lookup failed: " + e.message;
    }
  };

  loadMaterialsCatalog();

  [
    "project_name",
    "mod_qty",
    "mod_pmax",
    "inv_w",
    "service_a",
    "backup_mode",
  ].forEach((id) => {
    const el = $(id);
    if (el) el.addEventListener("input", updateSnapshot);
  });

  setStep(0);
  updateSnapshot();
  loadProjects();
}

wire();
