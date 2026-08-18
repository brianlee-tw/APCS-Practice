import fs from 'node:fs';

const requiredIds = [
  'landing-view','quiz-view','result-view','start-btn','resources-btn','question-count','load-error',
  'progress-label','progress','question-prompt','question-code','choices','back-btn','next-btn',
  'overall-score','band-label','weakest-label','strongest-label','skill-bars','error-tags',
  'review-btn','review-empty','review-list','product-title','recommend-reason','product-price',
  'product-status','product-btn','interest-box','share-btn','restart-btn','share-status','resources'
];

const files = {
  index: fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8'),
  privacy: fs.readFileSync(new URL('../privacy.html', import.meta.url), 'utf8'),
  vector: fs.readFileSync(new URL('../guides/vector-out-of-range.html', import.meta.url), 'utf8'),
  tle: fs.readFileSync(new URL('../guides/tle.html', import.meta.url), 'utf8'),
  prefix: fs.readFileSync(new URL('../guides/prefix-sum.html', import.meta.url), 'utf8'),
  app: fs.readFileSync(new URL('../app.js', import.meta.url), 'utf8'),
  theme: fs.readFileSync(new URL('../js/theme.js', import.meta.url), 'utf8'),
  polish: fs.readFileSync(new URL('../layout-polish.css', import.meta.url), 'utf8'),
};

const errors = [];
for (const id of requiredIds) if (!files.index.includes(`id="${id}"`)) errors.push(`index missing #${id}`);
for (const [name, html] of Object.entries(files).filter(([k]) => ['index','privacy','vector','tle','prefix'].includes(k))) {
  if (!html.includes('data-theme-toggle')) errors.push(`${name} missing theme toggle`);
  if (!html.includes('floating-theme-toggle')) errors.push(`${name} theme toggle must be floating`);
  if (!html.includes('theme.js')) errors.push(`${name} missing theme.js`);
  if (!html.includes('layout-polish.css')) errors.push(`${name} missing Q13 layout stylesheet`);
  if (!html.includes('meta name="theme-color"')) errors.push(`${name} missing theme-color meta`);
  if (html.includes('<header class="site-header"')) errors.push(`${name} must not render the top navigation bar`);
}
if (!files.index.includes('name="apcs-analytics-endpoint" content=""')) errors.push('analytics endpoint must remain empty by default');
if (!files.index.includes('找出<em>弱點</em>，再開始練習。')) errors.push('Q13 compact hero H1 missing');
for (const score of [88,76,54,71,66]) {
  if (!files.index.includes(`--score:${score}%`)) errors.push(`preview bar missing score ${score}`);
  if (!files.index.includes(`preview-bar-score">${score}<`)) errors.push(`preview bar missing visible score ${score}`);
}
if (!files.app.includes('buildReviewItems')) errors.push('free review logic missing from app.js');
if (!files.theme.includes('apcs_theme_preference')) errors.push('theme persistence key missing');
if (!files.polish.includes('.floating-theme-toggle')) errors.push('floating theme CSS missing');
if (!files.polish.includes('.preview-track::before')) errors.push('preview score bar fill CSS missing');

if (errors.length) {
  console.error(errors.join('\n'));
  process.exit(1);
}
console.log('UI contract: PASS');
