// AI agronomist: a Gemini language model that answers farmer questions using
// this field's NASA data (risk score, trends, ML forecast, ranked rotations).
// Hidden when no API key is set in config.js, so the site never shows a broken box.
(function () {
  const cfg = window.ARAL_CONFIG || {};
  const KEY = (cfg.GEMINI_API_KEY || "").trim();
  const MODEL = cfg.GEMINI_MODEL || "gemini-2.5-flash";
  if (!KEY) return;

  const TXT = {
    en: { lang: "English", title: "AI agronomist (Gemini)", ph: "Ask about this field…", ask: "Ask AI", wait: "AI is analysing the NASA data…",
          err: "The AI could not answer right now. Please try again.", note: "AI-generated advice based on this field's NASA data. It can make mistakes — check with an agronomist.",
          q: ["Explain this field's risk in simple words", "Which rotation should I choose and why?", "How can I save water on this field?"] },
    ru: { lang: "Russian", title: "ИИ-агроном (Gemini)", ph: "Спросите об этом поле…", ask: "Спросить ИИ", wait: "ИИ анализирует данные NASA…",
          err: "ИИ сейчас не смог ответить. Попробуйте ещё раз.", note: "Совет создан ИИ на основе данных NASA для этого поля. ИИ может ошибаться — уточните у агронома.",
          q: ["Объясни риск этого поля простыми словами", "Какой севооборот выбрать и почему?", "Как сэкономить воду на этом поле?"] },
    uz: { lang: "Uzbek (Latin script)", title: "SI agronom (Gemini)", ph: "Bu dala haqida so'rang…", ask: "SI dan so'rash", wait: "SI NASA ma'lumotlarini tahlil qilmoqda…",
          err: "SI hozir javob bera olmadi. Qayta urinib ko'ring.", note: "SI tomonidan ushbu dalaning NASA ma'lumotlari asosida yaratilgan maslahat. SI xato qilishi mumkin — agronom bilan maslahatlashing.",
          q: ["Bu dalaning xavfini oddiy so'zlar bilan tushuntiring", "Qaysi almashlab ekishni tanlashim kerak va nima uchun?", "Bu dalada suvni qanday tejash mumkin?"] },
  };
  const curLang = () => (typeof lang !== "undefined" && TXT[lang] ? lang : "en");
  const tx = () => TXT[curLang()];
  const escH = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const card = document.createElement("div");
  card.className = "card";
  card.id = "ai-card";
  card.innerHTML = `
    <div class="label" id="ai-title"></div>
    <div id="ai-suggest" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px"></div>
    <div style="display:flex;gap:8px">
      <input id="ai-input" type="text" style="flex:1;padding:8px;border:1px solid #ccc;border-radius:8px" />
      <button id="ai-ask" style="padding:8px 14px;border-radius:8px;border:0;background:#13261f;color:#fff;cursor:pointer"></button>
    </div>
    <div id="ai-answer" style="margin-top:10px;white-space:pre-wrap;line-height:1.5"></div>
    <p class="small" id="ai-note"></p>`;
  const report = document.getElementById("report");
  if (!report) return;
  report.appendChild(card);

  function labels() {
    const m = tx();
    document.getElementById("ai-title").textContent = m.title;
    document.getElementById("ai-input").placeholder = m.ph;
    document.getElementById("ai-ask").textContent = m.ask;
    document.getElementById("ai-note").textContent = m.note;
    document.getElementById("ai-suggest").innerHTML = m.q.map((q) =>
      `<button class="ai-q" style="padding:6px 10px;border-radius:16px;border:1px solid #ccc;background:#fff;cursor:pointer">${escH(q)}</button>`).join("");
  }

  function context() {
    const rep = typeof lastReport !== "undefined" ? lastReport : null;
    if (!rep) return null;
    const pick = (r) => ({ rotation: (r.years || []).map((y) => y.en).join(" -> "), fit: r.fit, water_saving: r.water_saving,
      salt_tolerance: r.salt_tolerance, soil_health: r.soil_health, income_usd_ha_estimate: r.income_usd_ha, water_need_mm: r.water_need_mm });
    let fc = {};
    try { if (typeof forecasts !== "undefined") fc = forecasts; } catch (e) { fc = {}; }
    return {
      field: rep.field,
      salinity_risk_proxy: rep.risk,
      soil: rep.soil_props,
      ml_trend_forecast: fc,
      top_rotations: (rep.rotations || []).slice(0, 3).map(pick),
      water_cut_simulation_for_best: rep.water_cut,
      data_sources: rep.sources,
    };
  }

  async function ask(question) {
    const m = tx();
    const out = document.getElementById("ai-answer");
    const ctx = context();
    if (!question.trim() || !ctx) return;
    out.textContent = m.wait;
    const system = `You are AralSentinel's agronomy assistant for farmers in Uzbekistan. Answer in ${m.lang}. ` +
      "Use ONLY the field data provided (NASA MODIS, NASA POWER, SoilGrids, and the app's computed scores). " +
      "The salinity risk is a proxy index from heat, vegetation and soil moisture; satellites do not measure salt directly, so say this when relevant. " +
      "Income figures are estimates. Be practical and specific, use simple words a farmer understands, at most 150 words. " +
      "If the data cannot answer the question, say so. End by recommending the farmer confirm with a local agronomist.";
    try {
      const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(MODEL)}:generateContent?key=${encodeURIComponent(KEY)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          systemInstruction: { parts: [{ text: system }] },
          contents: [{ role: "user", parts: [{ text: `Field data (JSON):\n${JSON.stringify(ctx)}\n\nFarmer's question: ${question}` }] }],
          generationConfig: { temperature: 0.4, maxOutputTokens: 2048 },
        }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error((data.error && data.error.message) || `HTTP ${r.status}`);
      const text = ((data.candidates || [])[0]?.content?.parts || []).map((p) => p.text || "").join("").trim();
      if (!text) throw new Error("empty answer");
      out.textContent = text.replace(/\*\*/g, "").replace(/^\s*[*-]\s+/gm, "• ");
    } catch (e) {
      console.warn("AI error:", e.message);
      out.textContent = `${m.err} (${e.message})`;
    }
  }

  document.getElementById("ai-ask").addEventListener("click", () => ask(document.getElementById("ai-input").value));
  document.getElementById("ai-input").addEventListener("keydown", (e) => { if (e.key === "Enter") ask(e.target.value); });
  document.getElementById("ai-suggest").addEventListener("click", (e) => {
    if (!e.target.classList.contains("ai-q")) return;
    document.getElementById("ai-input").value = e.target.textContent;
    ask(e.target.textContent);
  });
  const sel = document.getElementById("lang");
  if (sel) sel.addEventListener("change", () => { labels(); document.getElementById("ai-answer").textContent = ""; });
  labels();
})();
