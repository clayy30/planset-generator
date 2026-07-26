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
      roof_planes: 1,
      modules_per_plane: [num("mod_qty") || 1],
      azimuth_deg: [180],
      tilt_deg: [22],
      racking: "IronRidge XR / FlashFoot 2 or AHJ-approved equal",
      attachment: '5/16" x 4.75" SS lag, min 2-1/2" embedment into rafter',
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
    box.innerHTML = `
      <p><strong>Planset ready.</strong></p>
      <p><a href="${data.url}" target="_blank" rel="noopener">Open planset (print → PDF)</a></p>
      <p class="hint">Project ID: ${data.project_id}</p>
      ${warns}
      <p class="hint">Print from browser · paper size 11×17 (ANSI B) landscape · or Save as PDF.</p>
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
  };
  $("btn-preset-eg4").onclick = async () => {
    const p = await fetch("/api/presets/eg4-gridboss").then((r) => r.json());
    applyPreset(p);
  };

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
