import fs from 'node:fs';
import { spawnSync } from 'node:child_process';

const data = JSON.parse(fs.readFileSync(new URL('../data/free-7day-enrichment.v1.json', import.meta.url), 'utf8'));
const js = fs.readFileSync(new URL('../js/free-7day-enrichment.js', import.meta.url), 'utf8');
const css = fs.readFileSync(new URL('../free-product-enrichment.css', import.meta.url), 'utf8');
const html = fs.readFileSync(new URL('../free-7day.html', import.meta.url), 'utf8');
const errors = [];
const expectedPlaygrounds = ['loopScore','vectorBoundary','conditionFilter','complexityCompare','prefixSum','binarySearch','integerOps'];

if (data.productId !== 'FREE-7DAY') errors.push('enrichment productId must be FREE-7DAY');
if (data.enrichmentVersion !== '1.1.0') errors.push('enrichmentVersion must be 1.1.0');
if (!Array.isArray(data.days) || data.days.length !== 7) errors.push('enrichment must contain exactly 7 days');

for (const [index, day] of (data.days || []).entries()) {
  if (day.day !== index + 1) errors.push(`enrichment day sequence mismatch at ${index + 1}`);
  if (!Number.isInteger(day.estimatedMinutes) || day.estimatedMinutes < 30 || day.estimatedMinutes > 45) errors.push(`Day ${day.day} enriched duration must be 30-45 minutes`);
  if (!Array.isArray(day.teaching) || day.teaching.length < 4) errors.push(`Day ${day.day} needs >=4 conversational teaching paragraphs`);
  for (const [pIndex, paragraph] of (day.teaching || []).entries()) if (paragraph.length < 70) errors.push(`Day ${day.day} teaching paragraph ${pIndex + 1} is too thin`);
  if (!Array.isArray(day.microChecks) || day.microChecks.length < 2) errors.push(`Day ${day.day} needs >=2 micro checks`);
  for (const item of day.microChecks || []) if (!item.question || !item.answer || item.answer.length < 20) errors.push(`Day ${day.day} has incomplete micro check`);
  if (!day.playground?.type || day.playground.type !== expectedPlaygrounds[index]) errors.push(`Day ${day.day} playground must be ${expectedPlaygrounds[index]}`);
  if (!day.playground?.title || !day.playground?.description || !day.playground?.defaults) errors.push(`Day ${day.day} playground metadata incomplete`);
}

const serialized = JSON.stringify(data).toLowerCase();
for (const forbidden of ['todo','tbd','placeholder','lorem ipsum']) if (serialized.includes(forbidden)) errors.push(`enrichment contains forbidden token: ${forbidden}`);

for (const marker of [
  "const STATE_KEY = 'apcs_free7_enrichment_state_v1'",
  'input.type = \'checkbox\'',
  'input.checked = Boolean(checks[index])',
  'state.checks[day.unitId][index] = input.checked',
  'function runLoopScore',
  'function runVectorBoundary',
  'function runConditionFilter',
  'function runComplexity',
  'function runPrefix',
  'function runBinary',
  'function runIntegerOps',
  "track('free7_playground_run'",
  '不會把程式或輸入送到外部編譯服務'
]) if (!js.includes(marker)) errors.push(`enrichment JS missing contract marker: ${marker}`);

for (const marker of ['.teaching-story','.lesson-playground','.self-check-option','.playground-output','@media(max-width:620px)']) if (!css.includes(marker)) errors.push(`enrichment CSS missing ${marker}`);
if (!html.includes('./free-product-enrichment.css') || !html.includes('./js/free-7day-enrichment.js')) errors.push('FREE-7DAY enrichment assets not wired into page');
if (!html.includes('每天約 30–45 分鐘') && !html.includes('45–60 分鐘核心')) errors.push('FREE-7DAY enriched-or-deepened time promise missing from page');

const syntax = spawnSync(process.execPath, ['--check', new URL('../js/free-7day-enrichment.js', import.meta.url).pathname], { encoding: 'utf8' });
if (syntax.status !== 0) errors.push(`enrichment JS syntax check failed: ${syntax.stderr || syntax.stdout}`);

if (errors.length) { console.error(errors.join('\n')); process.exit(1); }
console.log('FREE-7DAY enrichment: VALID');
console.log('FREE-7DAY selectable self-check: PASS');
console.log('FREE-7DAY local playground contract: PASS');
