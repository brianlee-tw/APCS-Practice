// Curated learning content on the existing route. No REC/EV or measurement API.
export const DP03_SLUG = "dp03-iteration-direction-stepper";
export const DP03_REVISION = "dp03-direction-20261023-v1";

export function simulateExactItem(weight = 2, value = 3, capacity = 4, direction = "desc") {
  if (!Number.isInteger(weight) || weight <= 0 || !Number.isInteger(capacity) || capacity < weight || !["desc", "asc"].includes(direction)) throw new Error("Invalid teaching model");
  const dp = Array(capacity + 1).fill(null); dp[0] = 0;
  const changed = new Set();
  const states = [{ capacity: null, source: null, dp: [...dp], reused: false, note: "恰重：只有重量 0 可達，其他為 NEG。" }];
  const order = Array.from({ length: capacity - weight + 1 }, (_, i) => direction === "desc" ? capacity - i : weight + i);
  for (const c of order) {
    const from = c - weight, source = dp[from], reused = changed.has(from) && source !== null;
    if (source !== null) { dp[c] = Math.max(dp[c] ?? -Infinity, source + value); changed.add(c); }
    states.push({ capacity: c, source: from, sourceValue: source, dp: [...dp], reused,
      note: reused ? "首次非法重用：來源已被本件更新；同一件被取了兩次。" : source === null ? "來源不可達，不做加法。" : "來源仍是處理本件前的狀態。" });
  }
  const result = dp[capacity] === null ? "不可達" : String(dp[capacity]);
  states.push({ capacity: null, source: null, dp: [...dp], reused: false,
    note: direction === "desc" ? `0/1 恰重 ${capacity}：${result}。倒序只讀舊層，不重用本件。` : states.some((s) => s.reused) ? `升序得到 ${result}，但曾讀本件更新值；不能當合法 0/1 解。` : `本例結果 ${result}；仍須檢查來源是否為舊層。` });
  return states;
}

// Standalone client, also usable when browser storage is unavailable. A new
// content namespace prevents prior placeholder clicks from completing this task.
function client(model) {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? "NEG").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const key = `apcs-lab-v3:${model.slug}:${model.revision}`;
  let state = { mode: "desc", step: 0, firstPrediction: null, predictionDone: false, finals: { desc: false, asc: false } };
  try { const saved = JSON.parse(localStorage.getItem(key) || "null"); if (saved) state = { ...state, ...saved, finals: { ...state.finals, ...saved.finals } }; } catch {}
  if (!["desc", "asc"].includes(state.mode)) state.mode = "desc";
  state.step = Math.max(0, Math.min(Number.isInteger(state.step) ? state.step : 0, model.states[state.mode].length - 1));
  const save = () => { try { localStorage.setItem(key, JSON.stringify(state)); } catch {} };
  let feedback = "";
  function render() {
    const rows = model.states[state.mode], row = rows[state.step];
    const complete = state.predictionDone && state.finals.desc && state.finals.asc;
    const done = Number(state.predictionDone) + Number(state.finals.desc && state.finals.asc);
    $("#familyName").textContent = "Iteration Direction Stepper";
    $("#whyHtml").textContent = "追同一件物品，分開 old 來源與本輪 new 來源。";
    $("#labProgressText").textContent = `${done}/2`;
    $("#labProgressFill").style.width = `${done * 50}%`;
    $("#labState").textContent = complete ? "已比較兩種方向；用自己的話解釋第一次重用" : "先判斷，再逐步比較降序與升序";
    $("#debrief").hidden = !complete;
    $("#debrief").innerHTML = "<h2>整理</h2><p>倒序讀舊物品層，升序可能讀到本件剛更新的格子。恰重不可達與真實 0 分開。下一次改 w=3、W=6，用單件反例重新追蹤。</p><p class='small'>本機 Lab 學習狀態，不是 Independent AC，不寫入 REC／EV，也不提升 Mastery。</p>";
    $("#labApp").innerHTML = `<section class="card labPrediction"><h2>只有一件 w=2、v=3，0/1 恰重 W=4，正確結果是？</h2><p>先留下第一次判斷，再操作。</p><div class="labChoices">${["6", "3", "不可達", "0"].map((x, i) => `<button type="button" class="labChoice" data-answer="${i}">${x}</button>`).join("")}</div><p role="status">${esc(feedback)}</p><p>第一次選擇：${state.firstPrediction === null ? "尚未作答" : esc(["6", "3", "不可達", "0"][state.firstPrediction])}</p></section>
      <section class="card"><h2>同一初始狀態，切換迭代方向</h2><div class="labActions"><button type="button" class="btn ${state.mode === "desc" ? "primary" : ""}" data-mode="desc" aria-pressed="${state.mode === "desc"}">降序：0/1</button><button type="button" class="btn ${state.mode === "asc" ? "primary" : ""}" data-mode="asc" aria-pressed="${state.mode === "asc"}">升序：重用反例</button></div><p>Step ${state.step + 1} / ${rows.length} · ${row.capacity === null ? "來源層契約" : `c=${row.capacity}，讀 dp[${row.source}]=${row.sourceValue ?? "NEG"}`}</p><table><thead><tr><th>容量</th>${row.dp.map((_, i) => `<th>${i}</th>`).join("")}</tr></thead><tbody><tr><th>dp</th>${row.dp.map((v, i) => `<td${i === row.capacity ? ' style="outline:2px solid currentColor"' : ""}>${esc(v)}</td>`).join("")}</tr></tbody></table><p role="status">${esc(row.note)}</p><div class="labActions"><button type="button" class="btn" id="directionPrev"${state.step === 0 ? " disabled" : ""}>← 上一步</button><button type="button" class="btn primary" id="directionNext"${state.step === rows.length - 1 ? " disabled" : ""}>下一步 →</button></div><p>已看完：降序 ${state.finals.desc ? "✓" : "—"}；升序 ${state.finals.asc ? "✓" : "—"}</p></section>`;
    document.querySelectorAll("[data-answer]").forEach((b) => b.onclick = () => {
      const choice = Number(b.dataset.answer); if (state.firstPrediction === null) state.firstPrediction = choice;
      if (choice === 2) { state.predictionDone = true; feedback = "正確：只能選一次；請在兩種方向找第一次來源層差異。"; }
      else feedback = "先分清恰重與至多，並確認物品是否被重用。保留第一次判斷。";
      save(); render();
    });
    document.querySelectorAll("[data-mode]").forEach((b) => b.onclick = () => { state.mode = b.dataset.mode; state.step = 0; save(); render(); });
    $("#directionPrev").onclick = () => { state.step = Math.max(0, state.step - 1); save(); render(); };
    $("#directionNext").onclick = () => { state.step = Math.min(rows.length - 1, state.step + 1); if (state.step === rows.length - 1) state.finals[state.mode] = true; save(); render(); };
  }
  $("#resetLab").onclick = () => { if (!confirm("重設此版本 Lab 的本機練習？")) return; state = { mode: "desc", step: 0, firstPrediction: null, predictionDone: false, finals: { desc: false, asc: false } }; feedback = ""; save(); render(); };
  render();
}

export function curateDp03Iteration(html) {
  const pattern = /<script>window\.APCS_LAB_CONFIG=([\s\S]*?);<\/script>/;
  const match = html.match(pattern);
  const runtime = '<script src="/assets/apcs-lab-runtime-v3.js"></script>';
  if (!match || !html.includes(runtime)) throw new Error("DP03 curation requires the verified v3 asset template");
  const config = JSON.parse(match[1]);
  if (config.slug !== DP03_SLUG || config.lesson !== "L-DP-03") throw new Error("DP03 curation identity mismatch");
  const model = { slug: DP03_SLUG, revision: DP03_REVISION, states: { desc: simulateExactItem(2, 3, 4, "desc"), asc: simulateExactItem(2, 3, 4, "asc") } };
  const script = `(${client.toString()})(${JSON.stringify(model).replace(/</g, "\\u003c")});`;
  const { predict, operate, debrief, ...identityConfig } = config;
  return html.replace(pattern, `<script>window.APCS_LAB_CONFIG=${JSON.stringify({ ...identityConfig, contentRevision: DP03_REVISION }).replace(/</g, "\\u003c")};</script>`).replace(runtime, `<script>${script}</script>`);
}
