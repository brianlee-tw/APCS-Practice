import { track } from './analytics.js';

const ENRICHMENT_URL = './data/free-7day-enrichment.v1.json';
const STATE_KEY = 'apcs_free7_enrichment_state_v1';
const BASE_STATE_KEY = 'apcs_free7_progress_v1';
let enrichment = null;
let observer = null;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function loadState() {
  try {
    const raw = JSON.parse(localStorage.getItem(STATE_KEY) || '{}');
    return {
      checks: raw.checks && typeof raw.checks === 'object' ? raw.checks : {},
      sandboxes: raw.sandboxes && typeof raw.sandboxes === 'object' ? raw.sandboxes : {},
    };
  } catch (_) {
    return { checks: {}, sandboxes: {} };
  }
}

let state = loadState();

function saveState() {
  localStorage.setItem(STATE_KEY, JSON.stringify(state));
}

function baseCompleted(day) {
  try {
    const base = JSON.parse(localStorage.getItem(BASE_STATE_KEY) || '{}');
    return Array.isArray(base.completedDays) && base.completedDays.includes(day);
  } catch (_) {
    return false;
  }
}

function currentDayNumber() {
  const label = document.querySelector('#lesson-view .lesson-kicker span');
  const match = label?.textContent?.match(/DAY\s+(\d+)/i);
  return match ? Number(match[1]) : null;
}

function section(title, className = '') {
  const box = el('section', `lesson-section lesson-enrichment ${className}`.trim());
  box.append(el('h3', null, title));
  return box;
}

function renderTeaching(day) {
  const box = section('像家教一樣講一次', 'teaching-story');
  const intro = el('p', 'teaching-kicker', '先不要背公式。把今天的問題用人話想清楚。');
  box.append(intro);
  for (const paragraph of day.teaching) box.append(el('p', 'teaching-paragraph', paragraph));
  return box;
}

function renderMicroChecks(day) {
  const box = section('途中停一下', 'micro-checks');
  box.append(el('p', 'micro-check-intro', '先在心裡回答，再展開。這些不是考試，只是確認剛剛的概念有沒有真的進來。'));
  day.microChecks.forEach((item, index) => {
    const details = document.createElement('details');
    details.className = 'micro-check';
    const summary = el('summary', null, `${index + 1}. ${item.question}`);
    const answer = el('p', null, item.answer);
    details.append(summary, answer);
    box.append(details);
  });
  return box;
}

function parseValues(value) {
  const parts = String(value).split(',').map((part) => part.trim()).filter(Boolean);
  if (!parts.length) throw new Error('至少輸入一個整數。');
  if (parts.length > 50) throw new Error('教學執行器最多接受 50 個數字。');
  const numbers = parts.map(Number);
  if (numbers.some((n) => !Number.isFinite(n) || !Number.isInteger(n))) throw new Error('請用逗號分隔整數，例如 3,-1,4,2。');
  return numbers;
}

function numberField(labelText, key, value, options = {}) {
  const label = el('label', 'playground-field');
  label.append(el('span', null, labelText));
  const input = document.createElement('input');
  input.type = 'number'; input.dataset.key = key; input.value = String(value);
  if (options.min !== undefined) input.min = String(options.min);
  if (options.max !== undefined) input.max = String(options.max);
  label.append(input); return label;
}

function textField(labelText, key, value) {
  const label = el('label', 'playground-field playground-field-wide');
  label.append(el('span', null, labelText));
  const input = document.createElement('input'); input.type = 'text'; input.dataset.key = key; input.value = String(value);
  label.append(input); return label;
}

function selectField(labelText, key, value, options) {
  const label = el('label', 'playground-field');
  label.append(el('span', null, labelText));
  const select = document.createElement('select'); select.dataset.key = key;
  options.forEach(([optionValue, text]) => {
    const option = document.createElement('option'); option.value = optionValue; option.textContent = text; option.selected = optionValue === value; select.append(option);
  });
  label.append(select); return label;
}

function fieldsFor(playground, values) {
  const wrap = el('div', 'playground-fields');
  switch (playground.type) {
    case 'loopScore':
      wrap.append(numberField('初始 score', 'startScore', values.startScore, { min: -1000, max: 1000 }), numberField('迴圈上限 i <=', 'maxI', values.maxI, { min: 1, max: 20 })); break;
    case 'vectorBoundary':
      wrap.append(textField('vector 內容（逗號分隔）', 'values', values.values), numberField('起始 i', 'start', values.start, { min: 0, max: 50 }), selectField('繼續條件', 'condition', values.condition, [['lt', 'i < v.size()'], ['lte', 'i <= v.size()']])); break;
    case 'conditionFilter':
      wrap.append(textField('資料（逗號分隔）', 'values', values.values), numberField('必須可整除', 'divisibleBy', values.divisibleBy, { min: 1, max: 1000 }), numberField('但不可整除', 'notDivisibleBy', values.notDivisibleBy, { min: 1, max: 1000 })); break;
    case 'complexityCompare':
      wrap.append(numberField('N', 'n', values.n, { min: 1, max: 1000000000 }), numberField('Q', 'q', values.q, { min: 1, max: 1000000000 })); break;
    case 'prefixSum':
      wrap.append(textField('陣列（逗號分隔）', 'values', values.values), numberField('l', 'l', values.l, { min: 0, max: 49 }), numberField('r', 'r', values.r, { min: 0, max: 49 })); break;
    case 'binarySearch':
      wrap.append(textField('遞增陣列（逗號分隔）', 'values', values.values), numberField('target', 'target', values.target, { min: -1000000000, max: 1000000000 }), selectField('a[mid] < target 時', 'update', values.update, [['mid', 'l = mid（故意測錯誤版）'], ['midPlusOne', 'l = mid + 1（修正版）']])); break;
    case 'integerOps':
      wrap.append(numberField('x', 'x', values.x, { min: -1000000, max: 1000000 }), numberField('d', 'd', values.d, { min: 1, max: 1000000 })); break;
  }
  return wrap;
}

function readFields(container) {
  const values = {};
  container.querySelectorAll('[data-key]').forEach((input) => {
    values[input.dataset.key] = input.type === 'number' ? Number(input.value) : input.value;
  });
  return values;
}

function fmt(value) {
  if (!Number.isFinite(value)) return String(value);
  return Math.abs(value) >= 1e9 ? value.toExponential(3) : new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(value);
}

function runLoopScore(v) {
  const start = Math.trunc(v.startScore), maxI = Math.trunc(v.maxI);
  if (maxI < 1 || maxI > 20) throw new Error('迴圈上限請設在 1–20。');
  let score = start; const trace = [`初始 score = ${score}`];
  for (let i = 1; i <= maxI; i += 1) {
    const before = score; score = i % 2 === 0 ? score + i : score - 1;
    trace.push(`i=${i}｜${i % 2 === 0 ? `偶數：+${i}` : '奇數：-1'}｜${before} → ${score}`);
  }
  return { code: `int score = ${start};\nfor (int i = 1; i <= ${maxI}; ++i) {\n  if (i % 2 == 0) score += i;\n  else score -= 1;\n}\ncout << score;`, output: [...trace, `輸出：${score}`] };
}

function runVectorBoundary(v) {
  const values = parseValues(v.values); const start = Math.trunc(v.start); const useLte = v.condition === 'lte';
  if (start < 0 || start > 50) throw new Error('起始索引需在 0–50。');
  const trace = []; let sum = 0; let i = start; let guard = 0;
  const condition = () => useLte ? i <= values.length : i < values.length;
  while (condition() && guard++ < 60) {
    if (i < 0 || i >= values.length) { trace.push(`i=${i} → ❌ 越界：合法索引只有 0..${values.length - 1}`); break; }
    sum += values[i]; trace.push(`i=${i} → v[i]=${values[i]} → sum=${sum}`); i += 1;
  }
  const code = `vector<int> v = {${values.join(', ')}};\nint sum = 0;\nfor (int i = ${start}; i ${useLte ? '<=' : '<'} (int)v.size(); ++i) {\n  sum += v[i];\n}\ncout << sum;`;
  if (!trace.some((line) => line.includes('越界'))) trace.push(`✅ 迴圈結束，輸出：${sum}`);
  return { code, output: trace };
}

function runConditionFilter(v) {
  const values = parseValues(v.values); const a = Math.trunc(v.divisibleBy), b = Math.trunc(v.notDivisibleBy);
  if (a <= 0 || b <= 0) throw new Error('除數必須是正整數。');
  const passed = []; const trace = values.map((x) => {
    const p1 = x > 0, p2 = x % a === 0, p3 = x % b !== 0; const ok = p1 && p2 && p3; if (ok) passed.push(x);
    const failed = !p1 ? '不是正整數' : !p2 ? `不能被 ${a} 整除` : !p3 ? `也能被 ${b} 整除` : '通過';
    return `${x} → ${ok ? '✅' : '✗'} ${failed}`;
  });
  return { code: `for (int x : a) {\n  if (x > 0 && x % ${a} == 0 && x % ${b} != 0) ++cnt;\n}\ncout << cnt;`, output: [...trace, `符合：${passed.length ? passed.join(', ') : '沒有'}｜cnt=${passed.length}`] };
}

function runComplexity(v) {
  const n = Math.trunc(v.n), q = Math.trunc(v.q); if (n < 1 || q < 1 || n > 1e9 || q > 1e9) throw new Error('N、Q 請設在 1 到 1,000,000,000。');
  const linear = n * q; const lg = Math.max(1, Math.log2(n)); const sorted = n * lg + q * lg; const ratio = linear / sorted;
  return { code: `// 方案 A：Q 次，每次掃 N 個\n// 約 N*Q\n\n// 方案 B：sort 一次 + Q 次 binary_search\n// 約 N*log2(N) + Q*log2(N)`, output: [`N×Q ≈ ${fmt(linear)} 次量級`, `sort + binary search ≈ ${fmt(sorted)} 次量級`, `粗略比值：約 ${ratio.toFixed(ratio < 10 ? 1 : 0)} 倍`, '注意：這是成長量級比較，不是實際 CPU 秒數。'] };
}

function runPrefix(v) {
  const a = parseValues(v.values); const l = Math.trunc(v.l), r = Math.trunc(v.r);
  if (l < 0 || r < l || r >= a.length) throw new Error(`需要 0 <= l <= r < ${a.length}。`);
  const prefix = [0]; a.forEach((x) => prefix.push(prefix[prefix.length - 1] + x));
  const formula = prefix[r + 1] - prefix[l]; const direct = a.slice(l, r + 1).reduce((sum, x) => sum + x, 0);
  return { code: `vector<long long> prefix(a.size() + 1, 0);\nfor (int i = 0; i < (int)a.size(); ++i)\n  prefix[i + 1] = prefix[i] + a[i];\ncout << prefix[${r + 1}] - prefix[${l}];`, output: [`a = [${a.join(', ')}]`, `prefix = [${prefix.join(', ')}]`, `直接加總 a[${l}..${r}] = ${direct}`, `prefix[${r + 1}] - prefix[${l}] = ${prefix[r + 1]} - ${prefix[l]} = ${formula}`, formula === direct ? '✅ 兩種方法一致。' : '❌ 結果不一致，請重新檢查。'] };
}

function runBinary(v) {
  const a = parseValues(v.values); const target = Math.trunc(v.target); const fixed = v.update === 'midPlusOne';
  if (a.some((x, i) => i && a[i - 1] > x)) throw new Error('這個教學版本要求陣列為非遞減排序。');
  if (a[a.length - 1] < target) throw new Error('本課函式規格保證至少一個元素 >= target；請調整 target。');
  let l = 0, r = a.length - 1; const trace = []; const seen = new Set(); let step = 0;
  while (l < r && step < 20) {
    const stateKey = `${l},${r}`; if (seen.has(stateKey)) { trace.push(`❌ 狀態重複：l=${l}, r=${r}，搜尋區間沒有縮小。`); break; } seen.add(stateKey);
    const mid = l + Math.floor((r - l) / 2); const before = `[${l},${r}]`; const value = a[mid];
    if (value < target) l = fixed ? mid + 1 : mid; else r = mid;
    trace.push(`Step ${++step}｜${before}｜mid=${mid}, a[mid]=${value} → [${l},${r}]`);
  }
  if (l === r) trace.push(`✅ 結束：index=${l}, value=${a[l]}`);
  else if (step >= 20) trace.push('❌ 超過 20 步，可能沒有嚴格縮小區間。');
  return { code: `while (l < r) {\n  int mid = l + (r - l) / 2;\n  if (a[mid] < target) l = ${fixed ? 'mid + 1' : 'mid'};\n  else r = mid;\n}`, output: trace };
}

function runIntegerOps(v) {
  const x = Math.trunc(v.x), d = Math.trunc(v.d); if (d === 0) throw new Error('除數不能是 0。');
  const quotient = Math.trunc(x / d); const remainder = x % d; return { code: `int x = ${x};\nint d = ${d};\ncout << x / d + x % d;`, output: [`x / d = ${quotient}`, `x % d = ${remainder}`, `輸出：${quotient + remainder}`] };
}

function execute(playground, values) {
  switch (playground.type) {
    case 'loopScore': return runLoopScore(values);
    case 'vectorBoundary': return runVectorBoundary(values);
    case 'conditionFilter': return runConditionFilter(values);
    case 'complexityCompare': return runComplexity(values);
    case 'prefixSum': return runPrefix(values);
    case 'binarySearch': return runBinary(values);
    case 'integerOps': return runIntegerOps(values);
    default: throw new Error('未知的教學執行器。');
  }
}

function renderPlayground(day) {
  const p = day.playground; const box = section('動手改一改', 'lesson-playground');
  box.append(el('div', 'playground-headline', p.title), el('p', 'playground-description', p.description));
  const notice = el('p', 'playground-notice', '本工具完全在瀏覽器本機運算，不會把程式或輸入送到外部編譯服務。'); box.append(notice);
  const saved = state.sandboxes[String(day.day)] || {}; const values = { ...p.defaults, ...saved };
  const fields = fieldsFor(p, values); box.append(fields);
  const code = el('pre', 'playground-code'); const output = el('pre', 'playground-output'); output.setAttribute('aria-live', 'polite');
  const controls = el('div', 'playground-actions'); const run = el('button', 'primary', '執行'); run.type = 'button'; const reset = el('button', 'secondary', '重設'); reset.type = 'button'; controls.append(run, reset); box.append(controls, code, output);

  const runNow = () => {
    const current = readFields(fields); state.sandboxes[String(day.day)] = current; saveState();
    try {
      const result = execute(p, current); code.textContent = result.code; output.textContent = result.output.join('\n'); output.classList.remove('is-error');
      track('free7_playground_run', { day: day.day, type: p.type });
    } catch (error) {
      code.textContent = '// 請先修正輸入'; output.textContent = `⚠ ${error.message}`; output.classList.add('is-error');
    }
  };
  run.addEventListener('click', runNow);
  reset.addEventListener('click', () => { state.sandboxes[String(day.day)] = { ...p.defaults }; saveState(); applyEnhancement(true); });
  fields.querySelectorAll('input,select').forEach((input) => input.addEventListener('change', () => { state.sandboxes[String(day.day)] = readFields(fields); saveState(); }));
  runNow(); return box;
}

function enhanceSelfCheck(day) {
  const sections = [...document.querySelectorAll('#lesson-view .lesson-section')];
  const target = sections.find((s) => s.querySelector(':scope > h3')?.textContent === 'Self-check');
  if (!target) return;
  target.classList.add('interactive-self-check');
  [...target.children].slice(1).forEach((child) => child.remove());
  const items = day.baseSelfCheck || [];
  let checks = Array.isArray(state.checks[day.unitId]) ? state.checks[day.unitId].slice(0, items.length) : null;
  if (!checks || checks.length !== items.length) checks = Array(items.length).fill(baseCompleted(day.day));
  state.checks[day.unitId] = checks; saveState();
  const status = el('p', 'self-check-status'); const list = el('div', 'self-check-options');
  const updateStatus = () => { const count = state.checks[day.unitId].filter(Boolean).length; status.textContent = `${count}/${items.length} 已確認 · 可以隨時取消勾選`; };
  items.forEach((text, index) => {
    const label = el('label', 'self-check-option'); const input = document.createElement('input'); input.type = 'checkbox'; input.checked = Boolean(checks[index]);
    input.addEventListener('change', () => { state.checks[day.unitId][index] = input.checked; saveState(); updateStatus(); track('free7_selfcheck_toggle', { day: day.day, checked: input.checked }); });
    label.append(input, el('span', null, text)); list.append(label);
  });
  updateStatus(); target.append(status, list);
}

function applyEnhancement(force = false) {
  if (!enrichment) return;
  const host = document.getElementById('lesson-view'); const dayNumber = currentDayNumber();
  if (!host || !dayNumber) return;
  if (!force && host.dataset.enrichmentDay === String(dayNumber) && host.querySelector('.teaching-story')) return;
  host.querySelectorAll('.lesson-enrichment').forEach((n) => n.remove());
  const enrich = enrichment.days.find((d) => d.day === dayNumber); if (!enrich) return;
  const baseData = window.__free7BaseSelfChecks?.[dayNumber] || null;
  const existingSelf = [...host.querySelectorAll('.lesson-section')].find((s) => s.querySelector(':scope > h3')?.textContent === 'Self-check');
  const fallbackSelf = existingSelf ? [...existingSelf.querySelectorAll('li span')].map((n) => n.textContent) : [];
  const day = { ...enrich, unitId: `F7D-D${String(dayNumber).padStart(2, '0')}`, baseSelfCheck: baseData || fallbackSelf };

  const head = host.querySelector('.lesson-head'); const firstSection = host.querySelector('.lesson-section');
  const teaching = renderTeaching(day); if (head) head.after(teaching); else host.prepend(teaching);
  const micro = renderMicroChecks(day); const core = [...host.querySelectorAll('.lesson-section')].find((s) => s.querySelector(':scope > h3')?.textContent === '核心概念');
  if (core) core.after(micro); else teaching.after(micro);
  const playground = renderPlayground(day); const task = host.querySelector('.task-box');
  const checkpoint = [...host.querySelectorAll('.lesson-section')].find((s) => s.querySelector(':scope > h3')?.textContent === '五能力 checkpoint');
  if (task) task.before(playground); else if (checkpoint) checkpoint.before(playground); else (firstSection || micro).after(playground);
  enhanceSelfCheck(day);

  const time = host.querySelector('.lesson-kicker span:last-child'); if (time) time.textContent = `${enrich.estimatedMinutes} 分鐘`;
  host.dataset.enrichmentDay = String(dayNumber);
}

async function init() {
  const response = await fetch(ENRICHMENT_URL, { cache: 'no-store' });
  if (!response.ok) throw new Error(`FREE-7DAY enrichment HTTP ${response.status}`);
  enrichment = await response.json();
  window.__free7BaseSelfChecks = {};
  try {
    const base = await fetch('./data/free-7day.v1.json', { cache: 'no-store' }).then((r) => r.json());
    base.days.forEach((day) => { window.__free7BaseSelfChecks[day.day] = day.selfCheck; });
  } catch (_) {}
  observer = new MutationObserver(() => queueMicrotask(() => applyEnhancement()));
  const host = document.getElementById('lesson-view'); if (host) observer.observe(host, { childList: true, subtree: true });
  applyEnhancement();
}

init().catch((error) => console.error('FREE-7DAY enrichment failed:', error));
