import { scoreQuiz, levelBand, recommend, topErrorTags, buildReviewItems, buildShareText, selectQuestionSet } from "./js/engine.js";
import { track } from "./js/analytics.js";

const state = {
  fullQuestions: [], questions: [], skills: null, products: [], answers: {}, index: 0,
  started: false, startedAt: null, reviewItems: [], selectedCount: 15,
};
const $ = (id) => document.getElementById(id);
const labelFor = (id) => state.skills.dimensions.find((d) => d.id === id)?.label ?? id;

async function loadJson(path) {
  const r = await fetch(path, { cache: "no-store" });
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json();
}

async function init() {
  const [bank, skills, catalog] = await Promise.all([
    loadJson("./data/questions.v1.json"),
    loadJson("./data/skill-model.v1.json"),
    loadJson("./data/products.v1.json"),
  ]);
  state.fullQuestions = bank.questions;
  state.skills = skills;
  state.products = catalog.products;
  $("question-count").textContent = `5 / 10 / ${state.fullQuestions.length} 題可選`;
  $("start-btn").disabled = false;
  track("landing_view", { quizVersion: bank.version });
}

function show(viewId) {
  for (const el of document.querySelectorAll("[data-view]")) el.hidden = el.id !== viewId;
  document.body.classList.toggle("quiz-active", viewId === "quiz-view");
  if (viewId !== "quiz-view") window.scrollTo({ top: 0, behavior: "smooth" });
}

function openLengthDialog() {
  const dialog = $("quiz-length-dialog");
  if (!dialog.open) dialog.showModal();
}

function startQuiz(count) {
  state.selectedCount = count;
  state.questions = selectQuestionSet(state.fullQuestions, count);
  state.started = true;
  state.startedAt = Date.now();
  state.index = 0;
  state.answers = {};
  state.reviewItems = [];
  $("quiz-length-dialog").close();
  $("result-mode-label").textContent = `${count} 題${count === 5 ? "快速" : count === 10 ? "標準" : "完整"}版`;
  track("quiz_start", { totalQuestions: state.questions.length, mode: count });
  renderQuestion();
  show("quiz-view");
}

function renderQuestion() {
  const q = state.questions[state.index];
  $("progress-label").textContent = `第 ${state.index + 1} / ${state.questions.length} 題`;
  $("progress").value = state.index + 1;
  $("progress").max = state.questions.length;
  $("question-prompt").textContent = q.prompt;
  const code = $("question-code");
  code.hidden = !q.code;
  code.textContent = q.code || "";
  const choices = $("choices");
  choices.replaceChildren();
  q.choices.forEach((text, idx) => {
    const label = document.createElement("label");
    label.className = "choice";
    const input = document.createElement("input");
    input.type = "radio";
    input.name = "answer";
    input.value = String(idx);
    input.checked = state.answers[q.id] === idx;
    input.addEventListener("change", () => {
      state.answers[q.id] = idx;
      $("next-btn").disabled = false;
      track("quiz_answer", { questionId: q.id, dimension: q.dimension, answerIndex: idx });
    });
    const span = document.createElement("span");
    span.textContent = text;
    label.append(input, span);
    choices.append(label);
  });
  $("back-btn").disabled = state.index === 0;
  $("next-btn").disabled = !Number.isInteger(state.answers[q.id]);
  $("next-btn").textContent = state.index === state.questions.length - 1 ? "查看診斷結果" : "下一題";
}

function next() {
  if (!Number.isInteger(state.answers[state.questions[state.index].id])) return;
  if (state.index < state.questions.length - 1) {
    state.index += 1;
    renderQuestion();
    $("quiz-scroll").scrollTo({ top: 0, behavior: "smooth" });
  } else finishQuiz();
}

function back() {
  if (state.index > 0) {
    state.index -= 1;
    renderQuestion();
    $("quiz-scroll").scrollTo({ top: 0, behavior: "smooth" });
  }
}

function requestExit() {
  const dialog = $("exit-quiz-dialog");
  if (!dialog.open) dialog.showModal();
}

function confirmExit() {
  track("quiz_abandon", {
    answered: Object.keys(state.answers).length,
    totalQuestions: state.questions.length,
    mode: state.selectedCount,
  });
  $("exit-quiz-dialog").close();
  state.started = false;
  state.answers = {};
  state.index = 0;
  show("landing-view");
}

function finishQuiz() {
  const result = scoreQuiz(state.questions, state.answers);
  const recommendation = recommend(result, state.products);
  const band = levelBand(result.overall);
  const elapsedSec = state.startedAt ? Math.round((Date.now() - state.startedAt) / 1000) : null;
  sessionStorage.setItem("apcs_diag_result_v1", JSON.stringify(result));
  track("quiz_complete", { overall: result.overall, weakest: result.weakest, elapsedSec, mode: state.selectedCount });
  renderResult(result, band, recommendation);
  state.started = false;
  show("result-view");
  track("result_view", { overall: result.overall, weakest: result.weakest, productId: recommendation.productId, mode: state.selectedCount });
}

function renderResult(result, band, recommendation) {
  $("overall-score").textContent = String(result.overall);
  $("band-label").textContent = band.label;
  $("weakest-label").textContent = labelFor(result.weakest);
  $("strongest-label").textContent = labelFor(result.strongest);
  $("result-confidence-note").textContent = state.selectedCount === 5
    ? "快速版每項能力只有 1 題，適合快速找方向；若要更穩定的能力分布，建議再做 15 題完整版。"
    : state.selectedCount === 10
      ? "標準版每項能力 2 題；若要更細緻地確認弱點，可再做 15 題完整版。"
      : "完整版每項能力 3 題，適合作為目前版本最完整的能力診斷。";

  const bars = $("skill-bars");
  bars.replaceChildren();
  for (const d of state.skills.dimensions) {
    const row = document.createElement("div");
    row.className = "skill-row";
    row.innerHTML = `<div class="skill-head"><span>${d.label}</span><strong>${result.scores[d.id]}</strong></div><div class="bar"><span style="width:${result.scores[d.id]}%"></span></div>`;
    bars.append(row);
  }

  const errors = topErrorTags(result.misses, 3);
  $("error-tags").textContent = errors.length ? errors.map((e) => e.tag).join("、") : "目前沒有明顯集中錯誤";

  state.reviewItems = buildReviewItems(state.questions, result.misses, result.weakest, 3);
  $("review-list").replaceChildren();
  $("review-list").hidden = true;
  $("review-btn").hidden = state.reviewItems.length === 0;
  $("review-empty").hidden = state.reviewItems.length !== 0;
  $("review-btn").textContent = `免費看 ${state.reviewItems.length} 個錯題解析`;

  $("recommend-reason").textContent = recommendation.reason;
  const product = recommendation.product;
  $("product-title").textContent = product?.title ?? "下一階段訓練";
  $("product-price").textContent = product?.priceTwd ? `預計首發 NT$${product.priceTwd}` : "免費";
  $("product-status").textContent = product?.status === "validation" ? "目前為市場驗證階段，尚未開放付款。" : "此產品仍在規劃中。";
  $("product-btn").dataset.productId = recommendation.productId;
}

function showReview() {
  const list = $("review-list");
  list.replaceChildren();
  for (const [idx, item] of state.reviewItems.entries()) {
    const article = document.createElement("article");
    article.className = "review-card";
    const h3 = document.createElement("h3");
    h3.textContent = `${idx + 1}. ${labelFor(item.dimension)}｜${item.questionId}`;
    const prompt = document.createElement("p");
    prompt.textContent = item.prompt;
    article.append(h3, prompt);
    if (item.code) {
      const pre = document.createElement("pre");
      pre.className = "code review-code";
      pre.textContent = item.code;
      article.append(pre);
    }
    const selected = document.createElement("p");
    selected.innerHTML = "<strong>你的答案：</strong>";
    selected.append(document.createTextNode(item.selected));
    const correct = document.createElement("p");
    correct.innerHTML = "<strong>正確答案：</strong>";
    correct.append(document.createTextNode(item.correct));
    const explanation = document.createElement("p");
    explanation.className = "review-explanation";
    explanation.textContent = item.explanation;
    article.append(selected, correct, explanation);
    list.append(article);
  }
  list.hidden = false;
  $("review-btn").hidden = true;
  track("free_review_open", { count: state.reviewItems.length });
  list.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function shareResult() {
  const raw = sessionStorage.getItem("apcs_diag_result_v1");
  if (!raw) return;
  const result = JSON.parse(raw);
  const text = buildShareText(result, state.skills);
  track("share_click", { weakest: result.weakest, overall: result.overall });
  try {
    if (navigator.share) await navigator.share({ title: "APCS 能力診斷", text });
    else {
      await navigator.clipboard.writeText(text);
      $("share-status").textContent = "結果文字已複製。";
    }
  } catch (e) {
    if (e?.name !== "AbortError") $("share-status").textContent = "分享失敗，可稍後再試。";
  }
}

function productInterest(e) {
  const productId = e.currentTarget.dataset.productId;
  track("product_interest", { productId });
  $("interest-box").hidden = false;
  $("interest-box").scrollIntoView({ behavior: "smooth", block: "center" });
}

$("start-btn").addEventListener("click", openLengthDialog);
$("next-btn").addEventListener("click", next);
$("back-btn").addEventListener("click", back);
$("exit-quiz-btn").addEventListener("click", requestExit);
$("exit-cancel-btn").addEventListener("click", () => $("exit-quiz-dialog").close());
$("exit-confirm-btn").addEventListener("click", confirmExit);
$("length-cancel-btn").addEventListener("click", () => $("quiz-length-dialog").close());
for (const button of document.querySelectorAll("[data-quiz-count]")) {
  button.addEventListener("click", () => startQuiz(Number(button.dataset.quizCount)));
}
$("review-btn").addEventListener("click", showReview);
$("share-btn").addEventListener("click", shareResult);
$("product-btn").addEventListener("click", productInterest);
$("restart-btn").addEventListener("click", openLengthDialog);
$("resources-btn").addEventListener("click", () => $("resources").scrollIntoView({ behavior: "smooth", block: "start" }));

init().catch((err) => {
  console.error(err);
  $("load-error").hidden = false;
  $("start-btn").disabled = true;
});
