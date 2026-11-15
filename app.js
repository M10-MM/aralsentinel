// AralSentinel frontend. Works in two modes:
//   "live"   : FastAPI backend at  api/fields , api/fields/{id}/report
//   "static" : pre-exported JSON at api/fields.json , api/fields/{id}/report.json
//              (created by backend/export_static.py; used when the live API fails,
//               e.g. offline or when only the frontend folder is deployed)
const LIVE = "api";
const STATIC = "api";
// On known static hosts there is no backend, so skip the live probe
// (avoids a needless 404 in the browser console).
let mode = /\.(netlify\.app|github\.io)$/.test(location.hostname) ? "static" : "live";

let lang = "en";
try { lang = localStorage.getItem("lang") || "en"; } catch {}
let currentField = null;
let lastReport = null;
let waterCut = 20;
const charts = {};

const t = (key) => (I18N[lang] && I18N[lang][key]) || I18N.en[key] || key;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// ---------------------------------------------------------------- messages
function showError(msg) {
  const el = document.getElementById("error-banner");
  el.textContent = msg;
  el.hidden = !msg;
}

// fetch + safe JSON parse. Throws Error with a readable message on any failure.
async function fetchJSON(url) {
  let r;
  try { r = await fetch(url); } catch (e) { throw new Error(`${t("err_network")} (${url})`); }
  const text = await r.text();
  let body = null;
  try { body = JSON.parse(text); } catch { /* not JSON (e.g. HTML 404 page) */ }
  if (!r.ok) {
    const err = new Error((body && body.detail) || `HTTP ${r.status} (${url})`);
    err.apiError = !!(body && body.detail) && r.status < 500; // a real answer from our API (e.g. unknown field)
    throw err;
  }
  if (body === null) throw new Error(`${t("err_badjson")} (${url})`);
  return body;
}

// Try the live API first; on failure switch to static JSON for the rest of the session.
async function getData(livePath, staticPath) {
  if (mode === "live") {
    try { return await fetchJSON(`${LIVE}/${livePath}`); }
    catch (e) {
      if (e.apiError) throw e;            // server is up and answered: do not switch to offline mode
      console.warn("Live API failed, trying static JSON:", e.message);
      mode = "static";
      document.getElementById("offline-banner").hidden = false;
    }
  }
  document.getElementById("offline-banner").hidden = false;
  return fetchJSON(`${STATIC}/${staticPath}`);
}

// ---------------------------------------------------------------- language
function applyLang() {
  document.documentElement.lang = lang;
  document.getElementById("lang").value = lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => (el.textContent = t(el.dataset.i18n)));
  if (lastReport) render(lastReport);
}
document.getElementById("lang").addEventListener("change", (e) => {
  lang = e.target.value;
  try { localStorage.setItem("lang", lang); } catch {}
  applyLang();
});

// ---------------------------------------------------------------- map
const map = L.map("map").setView([40.1, 67.8], 9); // Jizzakh

// Esri imagery first; after a few tile errors fall back to OpenStreetMap.
// Markers are vector circles, so they still show when no tiles load (offline).
const esri = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
  attribution: "Imagery © Esri", maxZoom: 18,
});
const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "© OpenStreetMap contributors", maxZoom: 19,
});
let tileErrors = 0;
esri.on("tileerror", () => {
  if (++tileErrors === 3 && map.hasLayer(esri)) {
    map.removeLayer(esri);
    osm.addTo(map);
  }
});
esri.addTo(map);

const RISK_COLORS = { low: "#2e7d32", medium: "#c98a00", high: "#c62828" };
const markers = {};

async function loadFields() {
  try {
    const fields = await getData("fields", "fields.json");
    const list = document.getElementById("field-list");
    list.innerHTML = "";
    fields.forEach((f) => {
      markers[f.id] = L.circleMarker([f.lat, f.lon], { radius: 10, color: "#fff", weight: 2, fillColor: "#e4572e", fillOpacity: 0.9 })
        .addTo(map)
        .bindTooltip(f.name)
        .on("click", () => selectField(f.id));
      // buttons too, because some fields are outside the starting map view
      const b = document.createElement("button");
      b.textContent = f.name;
      b.dataset.id = f.id;
      b.addEventListener("click", () => { map.setView([f.lat, f.lon], 9); selectField(f.id); });
      list.appendChild(b);
    });
    // open the Jizzakh report straight away so first-time visitors never see an empty page
    if (!currentField && fields.length) {
      const first = fields.find((f) => f.id.includes("jizzakh")) || fields[0];
      selectField(first.id);
    }
  } catch (e) {
    showError(`${t("err_fields")}: ${e.message}`);
  }
}

function selectField(id) {
  currentField = id;
  document.querySelectorAll("#field-list button").forEach((b) => b.classList.toggle("active", b.dataset.id === id));
  loadReport();
}

// ---------------------------------------------------------------- report
function weights() {
  return {
    water: +document.getElementById("p-water").value,
    soil: +document.getElementById("p-soil").value,
    income: +document.getElementById("p-income").value,
  };
}

let debounceTimer = null;
["p-water", "p-soil", "p-income"].forEach((id) =>
  document.getElementById(id).addEventListener("input", () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => currentField && loadReport(), 250);
  }));

let requestNo = 0;
async function loadReport() {
  const myRequest = ++requestNo;      // ignore late answers from older slider positions
  const w = weights();
  try {
    let rep;
    if (mode === "live") {
      const q = new URLSearchParams(w);
      rep = await getData(`fields/${currentField}/report?${q}`, `fields/${currentField}/report.json`);
    } else {
      rep = await fetchJSON(`${STATIC}/fields/${currentField}/report.json`);
    }
    if (mode === "static") rep = rerankStatic(rep, w);
    if (myRequest !== requestNo) return;
    showError("");
    lastReport = rep;
    render(rep);
  } catch (e) {
    if (myRequest === requestNo) showError(`${t("err_report")}: ${e.message}`);
  }
}

// Same formula as backend/app/scoring.py score_rotation(), applied to pre-exported candidates.
function rerankStatic(rep, w) {
  if (!rep.candidates || !rep.candidates.length) return rep;
  const salt = (rep.risk && rep.risk.score ? rep.risk.score : 0) / 100;
  const total = w.water + w.soil + w.income + salt || 1;
  const ranked = rep.candidates.map((r) => ({
    ...r,
    fit: Math.round(((w.water * r.water_saving + w.soil * r.soil_health + w.income * r.income + salt * r.salt_tolerance) / total) * r.ph_fit),
  })).sort((a, b) => b.fit - a.fit);
  return { ...rep, rotations: ranked.slice(0, 5), water_cut: ranked[0].water_cut };
}

function render(rep) {
  document.getElementById("report").hidden = false;
  document.getElementById("sample-banner").hidden = !rep.sample_data;
  document.getElementById("field-name").textContent = rep.field.name;

  // risk
  const risk = rep.risk || {};
  const scoreEl = document.getElementById("risk-score");
  scoreEl.textContent = risk.score ?? "–";
  scoreEl.className = `score ${risk.level || ""}`;
  document.getElementById("risk-level").textContent = `${t(`level_${risk.level}`)} · ${t("proxy")}`;
  let why = risk.main_driver ? `${t("why")}: ${t(`d_${risk.main_driver}`)}.` : "";
  if (risk.missing && risk.missing.length) why += ` ${t("missing")}: ${risk.missing.map((m) => t(`d_${m}`)).join(", ")}.`;
  document.getElementById("risk-why").textContent = why;
  document.getElementById("risk-inputs").textContent = Object.entries(risk.inputs || {})
    .map(([k, v]) => `${t(`in_${k}`)}: ${v}`).join(" · ");

  // charts (empty series are skipped)
  const s = rep.series || {};
  const empty = [];
  Object.keys(forecasts).forEach((k) => delete forecasts[k]);
  [["ndvi", "#2e7d32"], ["lst", "#e4572e"], ["soil", "#1565c0"], ["rain", "#6a4c93"], ["tmax", "#b25b00"]]
    .forEach(([k, c]) => { if (!drawChart(k, s[k], c)) empty.push(t(`ch_${k}`)); });
  document.getElementById("no-data").textContent = empty.length ? `${t("no_data")}: ${empty.join(", ")}` : "";
  try { renderForecast(); } catch (e) { console.warn("forecast failed", e); }

  const src = Object.entries(rep.sources || {}).map(([k, v]) => `${k}: ${v}`).join(" · ");
  document.getElementById("sources").textContent = src ? `${t("sources")}: ${src}` : "";

  // rotation warnings
  const warns = (rep.rotation_meta && rep.rotation_meta.warnings) || [];
  document.getElementById("rot-warnings").innerHTML = warns.map((wn) => `<p class="warn">⚠ ${esc(t(`w_${wn}`))}</p>`).join("");

  // rotation table
  const rows = rep.rotations || [];
  document.getElementById("rotations").innerHTML = rows.length ? rows.map((r, i) => `
    <tr class="${i === 0 ? "best" : ""}">
      <td>${i + 1}</td>
      <td>${(r.years || []).map((y) => esc(y[lang] || y.en)).join(" → ")}</td>
      <td><b>${r.fit}</b></td>
      <td>${r.water_saving}</td>
      <td>${r.salt_tolerance}</td>
      <td>${r.soil_health}</td>
      <td>${r.income_usd_ha ?? "–"}</td>
    </tr>`).join("") : `<tr><td colspan="7">${esc(t("no_rotations"))}</td></tr>`;

  renderWaterCut(rep);
}

// ---------------------------------------------------------------- water-cut simulator
function renderWaterCut(rep) {
  const sims = rep.water_cut || [];
  const best = (rep.rotations || [])[0];
  document.getElementById("wc-rotation").textContent = best
    ? `${t("wc_for")}: ${(best.years || []).map((y) => y[lang] || y.en).join(" → ")}` : "";
  document.getElementById("wc-buttons").innerHTML = sims.map((s) =>
    `<button data-cut="${s.cut_pct}" class="${s.cut_pct === waterCut ? "active" : ""}">−${s.cut_pct}%</button>`).join("");
  const s = sims.find((x) => x.cut_pct === waterCut) || sims[0];
  document.getElementById("wc-result").innerHTML = s ? `
    <div><span class="big">−${s.yield_loss_pct}%</span><span class="small">${esc(t("wc_yield"))}</span></div>
    <div><span class="big">−$${s.income_loss_usd_ha}</span><span class="small">${esc(t("wc_income"))}</span></div>` : "";
}
document.getElementById("wc-buttons").addEventListener("click", (e) => {
  const cut = e.target.dataset && e.target.dataset.cut;
  if (!cut) return;
  waterCut = +cut;
  if (lastReport) renderWaterCut(lastReport);
});

// ---------------------------------------------------------------- ML trend forecast
// Machine learning in the browser: an ordinary least-squares linear regression is fitted
// to each NASA series (2015-2025) and extrapolated FORECAST_YEARS ahead. R² shows fit quality.
const FORECAST_YEARS = 3;
const forecasts = {};
const ML_TEXT = {
  en: { title: "Machine-learning trend forecast to", fc: "ML trend + forecast", up: "rising", down: "falling", flat: "stable",
        note: "Linear regression model trained on 2015–2025 NASA data for this field. It shows the direction of change, not an exact value for one year. Low R² means a weak trend." },
  ru: { title: "Прогноз тренда (машинное обучение) до", fc: "ML-тренд и прогноз", up: "растёт", down: "снижается", flat: "стабильно",
        note: "Модель линейной регрессии обучена на данных NASA 2015–2025 для этого поля. Показывает направление изменений, а не точное значение за год. Низкий R² — слабый тренд." },
  uz: { title: "Mashinali o'qitish trend prognozi:", fc: "ML trend va prognoz", up: "o'smoqda", down: "kamaymoqda", flat: "barqaror",
        note: "Chiziqli regressiya modeli ushbu dala uchun 2015–2025 yillardagi NASA ma'lumotlarida o'qitilgan. U o'zgarish yo'nalishini ko'rsatadi, aniq yillik qiymatni emas. Past R² — kuchsiz trend." },
};
const ml = () => ML_TEXT[lang] || ML_TEXT.en;

function fitTrend(pts) {
  const n = pts.length;
  if (n < 3) return null;
  const mx = pts.reduce((a, p) => a + p.year, 0) / n;
  const my = pts.reduce((a, p) => a + p.value, 0) / n;
  let sxy = 0, sxx = 0, syy = 0;
  pts.forEach((p) => { const dx = p.year - mx, dy = p.value - my; sxy += dx * dy; sxx += dx * dx; syy += dy * dy; });
  if (!sxx) return null;
  const slope = sxy / sxx, intercept = my - slope * mx;
  return { slope, r2: syy ? (sxy * sxy) / (sxx * syy) : 0, predict: (x) => intercept + slope * x };
}

function renderForecast() {
  let el = document.getElementById("ml-forecast");
  if (!el) {
    el = document.createElement("div");
    el.id = "ml-forecast";
    el.className = "card";
    const anchor = document.getElementById("no-data");
    anchor.parentNode.insertBefore(el, anchor.nextSibling);
  }
  const keys = Object.keys(forecasts);
  if (!keys.length) { el.hidden = true; return; }
  el.hidden = false;
  const m = ml();
  el.innerHTML = `<div class="label">${esc(m.title)} ${forecasts[keys[0]].year}</div><ul>` + keys.map((k) => {
    const f = forecasts[k];
    const d = f.to - f.from;
    const dir = Math.abs(d) < Math.abs(f.from) * 0.01 ? m.flat : d > 0 ? m.up : m.down;
    return `<li><b>${esc(t(`ch_${k}`))}</b>: ${f.from.toFixed(f.dec)} → ${f.to.toFixed(f.dec)} (${esc(dir)}, R² ${f.r2.toFixed(2)})</li>`;
  }).join("") + `</ul><p class="small">${esc(m.note)}</p>`;
}

// ---------------------------------------------------------------- charts
// Returns false (and hides the chart) when the series is empty.
function drawChart(key, series, color) {
  const ctx = document.getElementById(`c-${key}`);
  if (!ctx) return false;
  if (charts[key]) { charts[key].destroy(); delete charts[key]; }
  const pts = (series || []).filter((p) => p && p.value !== null && p.value !== undefined);
  ctx.parentElement.hidden = pts.length === 0;
  if (!pts.length || typeof Chart === "undefined") return pts.length > 0;
  // ML trend forecast: regression fitted in the browser, extended FORECAST_YEARS ahead
  const fit = fitTrend(pts);
  const lastYear = pts[pts.length - 1].year;
  const future = fit ? Array.from({ length: FORECAST_YEARS }, (_, i) => lastYear + i + 1) : [];
  const labels = pts.map((p) => p.year).concat(future);
  const datasets = [{ label: t(`ch_${key}`), data: pts.map((p) => p.value).concat(future.map(() => null)), borderColor: color, tension: 0.3, pointRadius: 2 }];
  if (fit) {
    const dec = Math.abs(fit.predict(lastYear)) < 2 ? 3 : 1;
    datasets.push({ label: ml().fc, data: labels.map((y) => +fit.predict(y).toFixed(dec)), borderColor: color, borderDash: [6, 4], borderWidth: 1.5, pointRadius: 0, tension: 0 });
    forecasts[key] = { from: fit.predict(lastYear), to: fit.predict(lastYear + FORECAST_YEARS), year: lastYear + FORECAST_YEARS, r2: fit.r2, dec };
  }
  charts[key] = new Chart(ctx, {
    type: "line",
    data: { labels, datasets },
    options: { responsive: true, animation: false, plugins: { legend: { labels: { boxWidth: 10 } } }, scales: { x: { ticks: { maxTicksLimit: 6 } } } },
  });
  return true;
}

applyLang();
loadFields();
