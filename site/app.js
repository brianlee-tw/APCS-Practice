import { scoreQuiz, levelBand, recommend, topErrorTags, buildShareText } from "./js/engine.js";
import { track } from "./js/analytics.js";

const state = { questions: [], skills: null, products: [], answers: {}, index: 0, started: false, startedAt: null };
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
  state.questions = bank.questions;
  state.skills = skills;
  state.products = catalog.products;
  $("question-count").textContent = `${state.questions.length} 題`;
  $("start-btn").disabled = false;
  track("landing_view", { quizVersion: bank.version });
}

function show(viewId) {
  for (const el of document.querySelectorAll("[data-view]")) el.hidden = el.id !== viewId;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function startQuiz() {
  state.started = true;
  state.startedAt = Date.now();
  state.index = 0;
  state.answers = {};
  track("quiz_start", { totalQuestions: state.questions.length });
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
  } else finishQuiz();
}

function back() {
  if (state.index > 0) {
    state.index -= 1;
    renderQuestion();
  }
}

function finishQuiz() {
  const result = scoreQuiz(state.questions, state.answers);
  const recommendation = recommend(result, state.products);
  const band = levelBand(result.overall);
  const elapsedSec = state.startedAt ? Math.round((Date.now() - state.startedAt) / 1000) : null;
  sessionStorage.setItem("apcs_diag_result_v1", JSON.stringify(result));
  track("quiz_complete", { overall: result.overall, weakest: result.weakest, elapsedSec });
  renderResult(result, band, recommendation);
  show("result-view");
  track("result_view", { overall: result.overall, weakest: result.weakest, productId: recommendation.productId });
}

function renderResult(result, band, recommendation) {
  $("overall-score").textContent = String(result.overall);
  $("band-label").textContent = band.label;
  $("weakest-label").textContent = labelFor(result.weakest);
  $("strongest-label").textContent = labelFor(result.strongest);

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
  $("recommend-reason").textContent = recommendation.reason;
  const product = recommendation.product;
  $("product-title").textContent = product?.title ?? "下一階段訓練";
  $("product-price").textContent = product?.priceTwd ? `預計首發 NT$${product.priceTwd}` : "免費";
  $("product-status").textContent = product?.status === "validation" ? "目前為市場驗證階段，尚未開放付款。" : "此產品仍在規劃中。";
  $("product-btn").dataset.productId = recommendation.productId;
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

function restart() {
  track("quiz_restart");
  startQuiz();
}

$("start-btn").addEventListener("click", startQuiz);
$("next-btn").addEventListener("click", next);
$("back-btn").addEventListener("click", back);
$("share-btn").addEventListener("click", shareResult);
$("product-btn").addEventListener("click", productInterest);
$("restart-btn").addEventListener("click", restart);

init().catch((err) => {
  console.error(err);
  $("load-error").hidden = false;
  $("start-btn").disabled = true;
});
