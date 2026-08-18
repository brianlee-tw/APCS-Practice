import { track } from './analytics.js';

const STORAGE_KEY = 'apcs_free7_progress_v1';
const $ = (id) => document.getElementById(id);
let course = null;
let state = loadState();
let currentDay = 1;

function loadState() {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    return {
      completedDays: Array.isArray(raw.completedDays) ? raw.completedDays.filter((n) => Number.isInteger(n) && n >= 1 && n <= 7) : [],
      notes: raw.notes && typeof raw.notes === 'object' ? raw.notes : {},
      solutionViewed: raw.solutionViewed && typeof raw.solutionViewed === 'object' ? raw.solutionViewed : {},
      checkpointAnswers: raw.checkpointAnswers && typeof raw.checkpointAnswers === 'object' ? raw.checkpointAnswers : {},
      checkpointScore: Number.isInteger(raw.checkpointScore) ? raw.checkpointScore : null,
      lastDay: Number.isInteger(raw.lastDay) ? Math.min(7, Math.max(1, raw.lastDay)) : 1,
    };
  } catch (_) {
    return { completedDays: [], notes: {}, solutionViewed: {}, checkpointAnswers: {}, checkpointScore: null, lastDay: 1 };
  }
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  updateProgress();
}

function node(tag, className, text) {
  const n = document.createElement(tag);
  if (className) n.className = className;
  if (text !== undefined) n.textContent = text;
  return n;
}

function codeBlock(code) {
  const pre = node('pre', 'lesson-code');
  const c = node('code');
  c.textContent = code;
  pre.append(c);
  return pre;
}

function renderList(items, className) {
  const ul = node('ul', className);
  for (const item of items) {
    const li = node('li');
    const span = node('span', null, item);
    li.append(span);
    ul.append(li);
  }
  return ul;
}

function skillLabel(skill) {
  const map = { syntax: '語法', reading: '讀碼', debug: '除錯', algorithm: '演算法', implementation: '實作' };
  return map[skill] || skill;
}

function updateProgress() {
  const count = new Set(state.completedDays).size;
  $('completed-count').textContent = String(count);
  $('course-progress').value = count;
  $('progress-copy').textContent = count === 7 ? '七天已完成。建議重新做 15 題完整診斷。' : count ? `已完成 ${count} 天；進度只存在這個瀏覽器。` : '從 Day 1 開始。進度只存在這個瀏覽器。';
  const next = Array.from({ length: 7 }, (_, i) => i + 1).find((d) => !state.completedDays.includes(d)) || 7;
  $('continue-btn').textContent = count === 7 ? '回到 Day 7' : `繼續 Day ${next}`;
  $('continue-btn').onclick = () => selectDay(count === 7 ? 7 : next);
  renderNav();
}

function renderNav() {
  if (!course) return;
  const nav = $('day-nav');
  nav.replaceChildren();
  for (const day of course.days) {
    const btn = node('button');
    btn.type = 'button';
    btn.setAttribute('aria-current', day.day === currentDay ? 'true' : 'false');
    const num = node('span', 'day-num', String(day.day).padStart(2, '0'));
    const copy = node('span', 'day-nav-copy');
    copy.append(node('strong', null, day.title), node('span', null, `${day.estimatedMinutes} 分鐘`));
    const stateDot = node('span', `day-state${state.completedDays.includes(day.day) ? ' is-done' : ''}`);
    btn.append(num, copy, stateDot);
    btn.addEventListener('click', () => selectDay(day.day));
    nav.append(btn);
  }
}

function selectDay(dayNumber) {
  currentDay = Math.min(7, Math.max(1, dayNumber));
  state.lastDay = currentDay;
  saveState();
  history.replaceState(null, '', `${location.pathname}?day=${currentDay}`);
  renderDay(course.days[currentDay - 1]);
  track('free7_day_view', { day: currentDay, productId: course.productId, version: course.version });
  document.querySelector('.free-course-layout')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function section(title) {
  const s = node('section', 'lesson-section');
  s.append(node('h3', null, title));
  return s;
}

function renderWorkedExample(day) {
  if (!day.workedExample) return null;
  const w = day.workedExample;
  const s = section('Worked example');
  s.append(node('p', 'task-prompt', w.prompt));
  if (w.code) s.append(codeBlock(w.code));
  s.append(renderList(w.trace || [], 'trace-list'));
  s.append(node('p', 'example-result', w.result));
  return s;
}

function renderHints(hints) {
  const wrap = node('div', 'hint-stack');
  hints.forEach((hint, idx) => {
    const details = document.createElement('details');
    const summary = node('summary', null, `Hint ${idx + 1}`);
    const p = node('p', null, hint);
    details.append(summary, p);
    wrap.append(details);
  });
  return wrap;
}

function renderSolution(day, container) {
  const existing = container.querySelector('.solution-panel');
  if (existing) {
    existing.scrollIntoView({ behavior: 'smooth', block: 'center' });
    return;
  }
  state.solutionViewed[day.unitId] = true;
  saveState();
  const t = day.task;
  const panel = node('div', 'solution-panel');
  panel.append(node('h4', null, '答案'));
  if (t.solution.includes('\n') || t.solution.includes('`')) {
    const c = node('pre', 'solution-code');
    c.textContent = t.solution.replaceAll('`', '');
    panel.append(c);
  } else panel.append(node('p', null, t.solution));
  panel.append(node('h4', null, '完整解析'), node('p', null, t.explanation));
  panel.append(node('h4', null, '常見錯法'), renderList(t.commonMistakes, 'mistake-list'));
  container.append(panel);
  renderCompletion(day);
  track('free7_solution_view', { day: day.day, unitId: day.unitId });
}

function renderTask(day) {
  const t = day.task;
  const box = node('section', 'task-box');
  box.append(node('h3', null, '主任務'), node('p', 'task-prompt', t.prompt));
  if (t.code) box.append(codeBlock(t.code));

  if (t.type === 'choice') {
    const choices = node('div', 'training-choices');
    t.choices.forEach((choice, idx) => {
      const label = node('label', 'training-choice');
      const input = document.createElement('input');
      input.type = 'radio'; input.name = `task-${day.unitId}`; input.value = String(idx);
      const span = node('span', null, choice);
      label.append(input, span); choices.append(label);
    });
    const feedback = node('p', 'task-feedback'); feedback.hidden = true;
    const check = node('button', 'secondary', '檢查答案'); check.type = 'button';
    check.addEventListener('click', () => {
      const selected = box.querySelector(`input[name="task-${day.unitId}"]:checked`);
      if (!selected) { feedback.hidden = false; feedback.textContent = '先選一個答案。'; return; }
      const ok = Number(selected.value) === t.correctIndex;
      feedback.hidden = false; feedback.className = `task-feedback${ok ? ' is-correct' : ''}`;
      feedback.textContent = ok ? '正確。現在再看解析，確認你不是猜中的。' : '這次不對。先開 Hint，再回到狀態或條件重新推一次。';
      track('free7_task_check', { day: day.day, correct: ok });
    });
    box.append(choices, feedback);
    const actions = node('div', 'task-actions'); actions.append(check);
    box.append(actions);
  } else {
    const textarea = node('textarea', 'task-note');
    textarea.placeholder = '先在這裡寫下你的修正、條件或推導。只會存在此瀏覽器。';
    textarea.value = state.notes[day.unitId] || '';
    textarea.addEventListener('input', () => { state.notes[day.unitId] = textarea.value; saveState(); });
    box.append(textarea);
  }

  box.append(renderHints(t.hints));
  const reveal = node('button', 'secondary', '看答案與完整解析'); reveal.type = 'button';
  reveal.addEventListener('click', () => renderSolution(day, box));
  const actions = box.querySelector('.task-actions') || node('div', 'task-actions');
  if (!actions.parentNode) box.append(actions);
  actions.append(reveal);
  if (state.solutionViewed[day.unitId]) renderSolution(day, box);
  return box;
}

function checkpointBand(day, score) {
  return day.checkpoint.bands.find((b) => score >= b.min && score <= b.max) || day.checkpoint.bands[0];
}

function renderCheckpoint(day) {
  const s = section('五能力 checkpoint');
  s.append(node('p', 'task-prompt', '五題全部作答後一次送出。先獨立完成，再看解析。'));
  const list = node('div', 'checkpoint-list');
  day.checkpoint.items.forEach((item, qIdx) => {
    const card = node('article', 'checkpoint-item');
    card.append(node('span', 'checkpoint-dimension', skillLabel(item.dimension)), node('h4', null, `${qIdx + 1}. ${item.prompt}`));
    if (item.code) card.append(codeBlock(item.code));
    const choices = node('div', 'training-choices');
    item.choices.forEach((choice, idx) => {
      const label = node('label', 'training-choice');
      const input = document.createElement('input');
      input.type = 'radio'; input.name = item.id; input.value = String(idx);
      input.checked = Number(state.checkpointAnswers[item.id]) === idx;
      input.addEventListener('change', () => { state.checkpointAnswers[item.id] = idx; saveState(); });
      label.append(input, node('span', null, choice)); choices.append(label);
    });
    card.append(choices); list.append(card);
  });
  s.append(list);
  const submit = node('button', 'primary', '送出 checkpoint'); submit.type = 'button';
  const result = node('div', 'checkpoint-result'); result.hidden = true;
  submit.addEventListener('click', () => {
    const items = day.checkpoint.items;
    if (items.some((item) => !Number.isInteger(Number(state.checkpointAnswers[item.id])))) {
      result.hidden = false; result.replaceChildren(node('p', null, '還有題目沒有作答。')); return;
    }
    const score = items.reduce((sum, item) => sum + (Number(state.checkpointAnswers[item.id]) === item.correctIndex ? 1 : 0), 0);
    state.checkpointScore = score;
    if (!state.completedDays.includes(7)) state.completedDays.push(7);
    saveState();
    renderCheckpointResult(day, result, score);
    track('free7_checkpoint_complete', { score, total: items.length });
    if (state.completedDays.length === 7) track('free7_complete', { productId: course.productId, version: course.version, score });
    renderCompletion(day);
  });
  s.append(submit, result);
  if (state.checkpointScore !== null) renderCheckpointResult(day, result, state.checkpointScore);
  return s;
}

function renderCheckpointResult(day, result, score) {
  result.hidden = false; result.replaceChildren();
  const band = checkpointBand(day, score);
  result.append(node('div', 'checkpoint-score', `${score}/5`), node('h3', null, band.label), node('p', null, band.action));
  const ex = node('div', 'checkpoint-explanations');
  day.checkpoint.items.forEach((item, idx) => {
    const article = node('article');
    const selected = Number(state.checkpointAnswers[item.id]);
    const ok = selected === item.correctIndex;
    article.append(node('strong', null, `${idx + 1}. ${ok ? '正確' : '需要修正'}｜${skillLabel(item.dimension)}`), node('p', null, item.explanation));
    ex.append(article);
  });
  result.append(ex);
}

function renderCompletion(day) {
  const old = $('lesson-completion'); if (old) old.remove();
  const wrap = node('div', 'lesson-completion'); wrap.id = 'lesson-completion';
  const done = state.completedDays.includes(day.day);
  const copy = node('p', null, day.completionRule);
  const btn = node('button', done ? 'secondary' : 'primary', done ? '已完成這一天 ✓' : '標記 Day 完成'); btn.type = 'button';
  if (day.day === 7) btn.disabled = state.checkpointScore === null;
  else btn.disabled = !state.solutionViewed[day.unitId];
  btn.addEventListener('click', () => {
    if (!state.completedDays.includes(day.day)) state.completedDays.push(day.day);
    saveState();
    track('free7_day_complete', { day: day.day, unitId: day.unitId });
    renderCompletion(day);
  });
  wrap.append(copy, btn);
  const host = $('lesson-view'); host.append(wrap);
}

function renderDay(day) {
  const host = $('lesson-view'); host.replaceChildren();
  const head = node('header', 'lesson-head');
  const kicker = node('div', 'lesson-kicker');
  kicker.append(node('span', null, `DAY ${String(day.day).padStart(2, '0')}`), node('span', null, day.skill.map(skillLabel).join(' / ')), node('span', null, `${day.estimatedMinutes} 分鐘`));
  head.append(kicker, node('h2', null, day.title), node('p', 'lesson-objective', day.objective));
  host.append(head);

  const concept = section('核心概念'); concept.append(renderList(day.concept, 'concept-list')); host.append(concept);
  const example = renderWorkedExample(day); if (example) host.append(example);
  if (day.checkpoint) host.append(renderCheckpoint(day)); else host.append(renderTask(day));
  const self = section('Self-check'); self.append(renderList(day.selfCheck, 'self-check-list')); host.append(self);
  const next = section('下一步'); next.append(node('p', 'task-prompt', day.nextStep));
  const nav = node('div', 'lesson-next');
  const prev = node('button', 'secondary', '← 上一天'); prev.type = 'button'; prev.disabled = day.day === 1; prev.onclick = () => selectDay(day.day - 1);
  const nextBtn = node('button', 'secondary', day.day === 7 ? '回到診斷 →' : '下一天 →'); nextBtn.type = 'button'; nextBtn.onclick = () => day.day === 7 ? (location.href = './?count=15') : selectDay(day.day + 1);
  nav.append(prev, nextBtn); next.append(nav); host.append(next);
  renderCompletion(day);
}

async function init() {
  const response = await fetch('./data/free-7day.v1.json', { cache: 'no-store' });
  if (!response.ok) throw new Error(`free-7day content: HTTP ${response.status}`);
  course = await response.json();
  $('free-subtitle').textContent = course.subtitle;
  const requested = Number(new URLSearchParams(location.search).get('day'));
  currentDay = Number.isInteger(requested) && requested >= 1 && requested <= 7 ? requested : state.lastDay;
  updateProgress(); renderDay(course.days[currentDay - 1]);
  track('free7_view', { productId: course.productId, version: course.version });
}

init().catch((error) => {
  console.error(error);
  $('lesson-view').replaceChildren(node('p', 'error', '7 日訓練內容載入失敗，請重新整理頁面。'));
});
