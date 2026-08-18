import fs from 'node:fs';
import { spawnSync } from 'node:child_process';

const data = JSON.parse(fs.readFileSync(new URL('../data/free-7day-deepening.v1.json', import.meta.url), 'utf8'));
const html = fs.readFileSync(new URL('../free-7day.html', import.meta.url), 'utf8');
const jsPath = new URL('../js/free-7day-deepening.js', import.meta.url);
const js = fs.readFileSync(jsPath, 'utf8');
const css = fs.readFileSync(new URL('../free-product-deepening.css', import.meta.url), 'utf8');
const errors = [];

if (data.productId !== 'FREE-7DAY') errors.push('deepening productId must be FREE-7DAY');
if (data.version !== '1.2.0') errors.push('FREE-7DAY deepening version must be 1.2.0');
if (data.layer !== 'deepening') errors.push('deepening layer marker missing');
if (data.coreMinutesRange !== '45–60') errors.push('core minute range must be 45–60');
if (data.optionalMinutesPerDay !== 15) errors.push('optional minutes must be 15');
if (!Array.isArray(data.days) || data.days.length !== 7) errors.push('deepening must contain exactly seven days');

const titles = new Set();
for (const [idx, day] of (data.days || []).entries()) {
  const label = `Day ${idx + 1}`;
  if (day.day !== idx + 1) errors.push(`${label} sequence mismatch`);
  if (!day.title || titles.has(day.title)) errors.push(`${label} title missing/duplicate`);
  titles.add(day.title);
  if (!Number.isInteger(day.estimatedCoreMinutes) || day.estimatedCoreMinutes < 45 || day.estimatedCoreMinutes > 60) errors.push(`${label} core minutes outside 45–60`);
  if (day.optionalMinutes !== 15) errors.push(`${label} optionalMinutes must be 15`);
  if (typeof day.openingScenario !== 'string' || day.openingScenario.length < 90) errors.push(`${label} opening scenario too thin`);
  if (!Array.isArray(day.whyItMatters) || day.whyItMatters.length < 2 || day.whyItMatters.some((p) => p.length < 45)) errors.push(`${label} whyItMatters too thin`);
  if (!Array.isArray(day.deepDive) || day.deepDive.length < 3) errors.push(`${label} needs >=3 deep-dive sections`);
  for (const part of day.deepDive || []) {
    if (!part.title || !Array.isArray(part.paragraphs) || part.paragraphs.length < 2 || part.paragraphs.some((p) => p.length < 45)) errors.push(`${label} deep-dive subsection incomplete`);
  }
  const ex = day.secondWorkedExample;
  if (!ex?.prompt || !ex?.code || !Array.isArray(ex.walkthrough) || ex.walkthrough.length < 3 || !ex.result) errors.push(`${label} second worked example incomplete`);
  if (!Array.isArray(day.drillSet) || day.drillSet.length < 4 || day.drillSet.some((x) => !x.q || !x.a || !x.why)) errors.push(`${label} needs >=4 complete drills`);
  if (!Array.isArray(day.misconceptionClinic) || day.misconceptionClinic.length < 3 || day.misconceptionClinic.some((x) => !x.myth || !x.correction)) errors.push(`${label} misconception clinic incomplete`);
  if (!day.transferChallenge?.prompt || !Array.isArray(day.transferChallenge?.hints) || day.transferChallenge.hints.length < 2 || !day.transferChallenge?.solution) errors.push(`${label} transfer challenge incomplete`);
  if (!day.optionalChallenge?.prompt || !day.optionalChallenge?.hint || !day.optionalChallenge?.solution) errors.push(`${label} optional challenge incomplete`);
  if (!Array.isArray(day.recap) || day.recap.length < 5) errors.push(`${label} recap needs >=5 items`);
  if (!Array.isArray(day.glossary) || day.glossary.length < 4 || day.glossary.some((x) => !x.term || !x.definition)) errors.push(`${label} glossary needs >=4 terms`);
}

const serialized = JSON.stringify(data);
for (const forbidden of ['TODO','TBD','placeholder','lorem ipsum']) {
  if (serialized.toLowerCase().includes(forbidden.toLowerCase())) errors.push(`deepening content contains ${forbidden}`);
}
for (const requiredText of ['先進入情境','概念深挖','第二個完整示範','短練習：四題把概念釘牢','迷思診療室','遷移題','選做挑戰','今天收進工具箱的 5 件事','今天的術語']) {
  if (!js.includes(requiredText)) errors.push(`deepening renderer missing section: ${requiredText}`);
}
if (!js.includes("const STATE_KEY = 'apcs_free7_deepening_state_v1'")) errors.push('deepening local note state missing');
if (!js.includes('free7_deepening_view')) errors.push('deepening view event missing');
if (!html.includes('./free-product-deepening.css') || !html.includes('./js/free-7day-deepening.js')) errors.push('deepening assets not wired into page');
if (!html.includes('45–60 分鐘核心')) errors.push('hero does not communicate deep course duration');
for (const cls of ['.deep-opening','.deep-dive-card','.deep-drill','.deep-note','.deep-recap-list','.deep-glossary-grid']) if (!css.includes(cls)) errors.push(`deepening CSS missing ${cls}`);

const syntax = spawnSync(process.execPath, ['--check', jsPath.pathname], { encoding:'utf8' });
if (syntax.status !== 0) errors.push(`deepening JS syntax invalid: ${syntax.stderr || syntax.stdout}`);

if (errors.length) {
  console.error(errors.join('\n'));
  process.exit(1);
}
console.log('FREE-7DAY v1.2 deepening content: VALID');
console.log('FREE-7DAY v1.2 density gate: PASS');
console.log('FREE-7DAY v1.2 rendering contract: PASS');
