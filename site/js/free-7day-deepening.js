import { track } from './analytics.js';

const DATA_URL = './data/free-7day-deepening.v1.json';
const STATE_KEY = 'apcs_free7_deepening_state_v1';
let deepening = null;
let observer = null;
let state = loadState();

function loadState() {
  try {
    const raw = JSON.parse(localStorage.getItem(STATE_KEY) || '{}');
    return { notes: raw.notes && typeof raw.notes === 'object' ? raw.notes : {} };
  } catch (_) {
    return { notes: {} };
  }
}
function saveState() { localStorage.setItem(STATE_KEY, JSON.stringify(state)); }
function el(tag, className, text) {
  const n = document.createElement(tag);
  if (className) n.className = className;
  if (text !== undefined) n.textContent = text;
  return n;
}
function section(title, className='') {
  const s = el('section', `lesson-section deepening-layer ${className}`.trim());
  s.append(el('h3', null, title));
  return s;
}
function currentDayNumber() {
  const text = document.querySelector('#lesson-view .lesson-kicker span')?.textContent || '';
  const m = text.match(/DAY\s+(\d+)/i);
  return m ? Number(m[1]) : null;
}
function findSection(title) {
  return [...document.querySelectorAll('#lesson-view .lesson-section')].find((s) => s.querySelector(':scope > h3')?.textContent?.trim() === title) || null;
}
function detailsBlock(summaryText, bodyNodes, className='deep-details') {
  const d = document.createElement('details');
  d.className = className;
  d.append(el('summary', null, summaryText), ...bodyNodes);
  return d;
}
function codeBlock(code) {
  const pre = el('pre', 'lesson-code deep-code');
  pre.append(el('code', null, code));
  return pre;
}
function renderOpening(day) {
  const s = section('先進入情境', 'deep-opening');
  s.append(el('p', 'deep-opening-copy', day.openingScenario));
  return s;
}
function renderWhy(day) {
  const s = section('為什麼這一題型值得練', 'deep-why');
  day.whyItMatters.forEach((p) => s.append(el('p', 'deep-paragraph', p)));
  return s;
}
function renderDeepDive(day) {
  const s = section('概念深挖', 'deep-dive');
  day.deepDive.forEach((part, idx) => {
    const article = el('article', 'deep-dive-card');
    const head = el('div', 'deep-dive-head');
    head.append(el('span', 'deep-index', String(idx + 1).padStart(2, '0')), el('h4', null, part.title));
    article.append(head);
    part.paragraphs.forEach((p) => article.append(el('p', 'deep-paragraph', p)));
    s.append(article);
  });
  return s;
}
function renderSecondExample(day) {
  const x = day.secondWorkedExample;
  const s = section('第二個完整示範', 'deep-example');
  s.append(el('p', 'task-prompt', x.prompt));
  if (x.code) s.append(codeBlock(x.code));
  const ol = el('ol', 'deep-walkthrough');
  x.walkthrough.forEach((step) => ol.append(el('li', null, step)));
  s.append(ol, el('p', 'example-result', x.result));
  return s;
}
function renderDrills(day) {
  const s = section('短練習：四題把概念釘牢', 'deep-drills');
  s.append(el('p', 'deep-section-intro', '每題先自己回答 20–40 秒，再展開。不要把「看懂答案」當作「自己會做」。'));
  day.drillSet.forEach((item, idx) => {
    const answer = el('div', 'deep-answer');
    answer.append(el('strong', null, `答案：${item.a}`), el('p', null, item.why));
    s.append(detailsBlock(`${idx + 1}. ${item.q}`, [answer], 'deep-drill'));
  });
  return s;
}
function renderMisconceptions(day) {
  const s = section('迷思診療室', 'deep-misconceptions');
  day.misconceptionClinic.forEach((item) => {
    const card = el('article', 'myth-card');
    card.append(el('strong', 'myth-label', item.myth), el('p', null, item.correction));
    s.append(card);
  });
  return s;
}
function noteArea(day, suffix, placeholder) {
  const area = document.createElement('textarea');
  area.className = 'deep-note';
  const key = `${day.day}:${suffix}`;
  area.value = state.notes[key] || '';
  area.placeholder = placeholder;
  area.addEventListener('input', () => { state.notes[key] = area.value; saveState(); });
  return area;
}
function renderTransfer(day) {
  const t = day.transferChallenge;
  const s = section('遷移題：換一個表面，方法還會不會用？', 'deep-transfer');
  s.append(el('p', 'task-prompt', t.prompt), noteArea(day, 'transfer', '先寫你的推導或答案。這裡只存在此瀏覽器。'));
  const hints = el('div', 'deep-hints');
  t.hints.forEach((hint, idx) => hints.append(detailsBlock(`提示 ${idx + 1}`, [el('p', null, hint)])));
  s.append(hints, detailsBlock('看完整解法', [el('p', null, t.solution)], 'deep-solution'));
  return s;
}
function renderOptional(day) {
  const t = day.optionalChallenge;
  const s = section('選做挑戰：今天還有餘力再做', 'deep-optional');
  s.append(el('p', 'task-prompt', t.prompt), noteArea(day, 'optional', '選做區：記下你的設計、推導或測資。'));
  s.append(detailsBlock('先看一個提示', [el('p', null, t.hint)]), detailsBlock('參考解法／完成標準', [el('p', null, t.solution)], 'deep-solution'));
  return s;
}
function renderRecap(day) {
  const s = section('今天收進工具箱的 5 件事', 'deep-recap');
  const ul = el('ul', 'deep-recap-list');
  day.recap.forEach((x) => ul.append(el('li', null, x)));
  s.append(ul);
  return s;
}
function renderGlossary(day) {
  const s = section('今天的術語', 'deep-glossary');
  const dl = el('dl', 'deep-glossary-grid');
  day.glossary.forEach((x) => {
    const wrap = el('div', 'deep-glossary-item');
    wrap.append(el('dt', null, x.term), el('dd', null, x.definition));
    dl.append(wrap);
  });
  s.append(dl);
  return s;
}
function updateDuration(day) {
  const kicker = document.querySelector('#lesson-view .lesson-kicker');
  if (kicker) {
    const spans = [...kicker.querySelectorAll('span')];
    const time = spans.at(-1);
    if (time) time.textContent = `${day.estimatedCoreMinutes} 分鐘核心 + ${day.optionalMinutes} 分鐘選做`;
  }
  document.querySelectorAll('#day-nav button').forEach((button, idx) => {
    const d = deepening.days[idx];
    const meta = button.querySelector('.day-nav-copy span');
    if (d && meta) meta.textContent = `${d.estimatedCoreMinutes} 分鐘`;
  });
  const subtitle = document.getElementById('free-subtitle');
  if (subtitle) subtitle.textContent = '每天約 45–60 分鐘核心學習，再加 15 分鐘選做；先聽懂、動手試、自己做，再用 Self-check 確認。';
}
function applyDeepening() {
  if (!deepening) return;
  const host = document.getElementById('lesson-view');
  if (!host?.querySelector('.lesson-head')) return;
  const dayNo = currentDayNumber();
  const day = deepening.days.find((x) => x.day === dayNo);
  if (!day) return;
  if (host.querySelector(`.deepening-layer[data-deep-day="${dayNo}"]`)) return;

  host.querySelectorAll('.deepening-layer').forEach((n) => n.remove());
  const head = host.querySelector('.lesson-head');
  const opening = renderOpening(day);
  opening.dataset.deepDay = String(dayNo);
  head.after(opening, renderWhy(day));

  const teaching = host.querySelector('.teaching-story');
  const concept = findSection('核心概念');
  const anchor = teaching || concept;
  if (anchor) anchor.after(renderDeepDive(day));

  const worked = findSection('Worked example');
  if (worked) worked.after(renderSecondExample(day));

  const playground = host.querySelector('.lesson-playground');
  const task = host.querySelector('.task-box') || findSection('五能力 checkpoint');
  const drillAnchor = playground || task || worked;
  if (drillAnchor) drillAnchor.after(renderDrills(day), renderMisconceptions(day));

  const self = findSection('Self-check');
  if (self) self.before(renderTransfer(day), renderOptional(day));

  const next = findSection('下一步');
  if (next) next.before(renderRecap(day), renderGlossary(day));

  updateDuration(day);
  track('free7_deepening_view', { day: dayNo, version: deepening.version });
}
async function init() {
  const response = await fetch(DATA_URL, { cache: 'no-store' });
  if (!response.ok) throw new Error(`FREE-7DAY deepening: HTTP ${response.status}`);
  deepening = await response.json();
  observer = new MutationObserver(() => applyDeepening());
  const host = document.getElementById('lesson-view');
  if (host) observer.observe(host, { childList: true, subtree: true });
  applyDeepening();
}
init().catch((error) => console.error(error));
