import fs from 'node:fs';

const requiredIds = [
  'landing-view','quiz-view','result-view','start-btn','resources-btn','question-count','load-error',
  'count-picker','launch-badge','selected-count','selected-time','quiz-mode-title','exit-quiz-btn','exit-dialog',
  'continue-quiz-btn','confirm-exit-btn','progress-label','progress','question-prompt','question-code','choices','back-btn','next-btn',
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
  productsHtml: fs.readFileSync(new URL('../products.html', import.meta.url), 'utf8'),
  app: fs.readFileSync(new URL('../app.js', import.meta.url), 'utf8'),
  engine: fs.readFileSync(new URL('../js/engine.js', import.meta.url), 'utf8'),
  theme: fs.readFileSync(new URL('../js/theme.js', import.meta.url), 'utf8'),
  polish: fs.readFileSync(new URL('../layout-polish.css', import.meta.url), 'utf8'),
  experience: fs.readFileSync(new URL('../experience.css', import.meta.url), 'utf8'),
  productPlan: fs.readFileSync(new URL('../product-plan.css', import.meta.url), 'utf8'),
};
const products = JSON.parse(fs.readFileSync(new URL('../data/products.v1.json', import.meta.url), 'utf8'));

const errors = [];
for (const id of requiredIds) if (!files.index.includes(`id="${id}"`)) errors.push(`index missing #${id}`);
for (const [name, html] of Object.entries(files).filter(([k]) => ['index','privacy','vector','tle','prefix','productsHtml'].includes(k))) {
  if (!html.includes('data-theme-toggle')) errors.push(`${name} missing theme toggle`);
  if (!html.includes('floating-theme-toggle')) errors.push(`${name} theme toggle must be floating`);
  if (!html.includes('theme.js')) errors.push(`${name} missing theme.js`);
  if (!html.includes('meta name="theme-color"')) errors.push(`${name} missing theme-color meta`);
  if (html.includes('<header class="site-header"')) errors.push(`${name} must not render the top navigation bar`);
}
if (!files.index.includes('name="apcs-analytics-endpoint" content=""')) errors.push('analytics endpoint must remain empty by default');
if (!files.index.includes('找出<em>弱點</em>，再開始練習。')) errors.push('compact hero H1 missing');
for (const score of [88,76,54,71,66]) {
  if (!files.index.includes(`--score:${score}%`)) errors.push(`preview bar missing score ${score}`);
  if (!files.index.includes(`preview-bar-score">${score}<`)) errors.push(`preview bar missing visible score ${score}`);
}
for (const count of [5,10,15]) {
  if (!files.index.includes(`name="quiz-count" value="${count}"`)) errors.push(`question-count option ${count} missing`);
}
if (!files.index.includes('marketing-only')) errors.push('marketing-only sections missing');
if (!files.app.includes('classList.toggle("quiz-active"')) errors.push('quiz focus state toggle missing');
if (!files.experience.includes('body.quiz-active .marketing-only')) errors.push('focus-mode marketing hide CSS missing');
if (!files.experience.includes('@media (max-width: 620px)')) errors.push('mobile breakpoint missing');
if (!files.engine.includes('selectBalancedQuestions')) errors.push('balanced short-quiz selector missing');
if (!files.app.includes('quiz_abandon')) errors.push('quiz exit/abandon event missing');
if (!files.app.includes('buildReviewItems')) errors.push('free review logic missing from app.js');
if (!files.theme.includes('apcs_theme_preference')) errors.push('theme persistence key missing');
if (!files.polish.includes('.floating-theme-toggle')) errors.push('floating theme CSS missing');
if (!files.polish.includes('width:42px') || !files.polish.includes('position:fixed')) errors.push('theme toggle must be compact and removed from document flow');
if (!files.polish.includes('padding:28px 0 56px')) errors.push('desktop hero top spacing was not tightened');
if (!files.experience.includes('.guide-shell')) errors.push('redesigned guide system missing');
for (const key of ['vector','tle','prefix']) {
  if (!files[key].includes('guide-hero') || !files[key].includes('guide-content') || !files[key].includes('experience.css')) errors.push(`${key} guide did not migrate to Q14 design`);
}
if (!files.productsHtml.includes('Product Library') || !files.productsHtml.includes('產品規格完成 · 內容準備中')) errors.push('formal product library status missing');
if (!files.productsHtml.includes('product-plan.css')) errors.push('formal product-plan stylesheet missing');
for (const requiredProduct of ['P1-30DAY','P2-DEBUG','P3-CONCEPT','P3-INTERMEDIATE','P3-ADVANCED','P4-SPRINT','P4-MOCK','P5-POSTEXAM','P6-GITHUB','P7-PORTFOLIO','P8-AI-CODING','B1-APCS-CORE','B2-PORTFOLIO','B3-APCS-PREP']) {
  if (!files.productsHtml.includes(requiredProduct)) errors.push(`product library missing ${requiredProduct}`);
}
const futureProducts = products.products.filter((p) => p.id !== 'FREE-3Q');
if (futureProducts.length < 15) errors.push(`expected at least 15 future product slots, got ${futureProducts.length}`);
for (const p of futureProducts) if (p.status !== 'preparing') errors.push(`${p.id} must be preparing`);
if (futureProducts.some((p) => p.status === 'validation')) errors.push('formal product catalog must not use validation status');
if (!files.productPlan.includes('.product-deliverables') || !files.productPlan.includes('.bundle-grid')) errors.push('formal product-card detail system missing');

if (errors.length) {
  console.error(errors.join('\n'));
  process.exit(1);
}
console.log('UI contract: PASS');
