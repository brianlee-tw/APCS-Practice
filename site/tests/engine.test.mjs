import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { scoreQuiz, levelBand, recommend, topErrorTags, buildReviewItems, validateQuestionBank, selectBalancedQuestions } from "../js/engine.js";

const bank = JSON.parse(fs.readFileSync(new URL("../data/questions.v1.json", import.meta.url), "utf8"));
const catalog = JSON.parse(fs.readFileSync(new URL("../data/products.v1.json", import.meta.url), "utf8"));
const skillModel = JSON.parse(fs.readFileSync(new URL("../data/skill-model.v1.json", import.meta.url), "utf8"));

test("question bank is structurally valid", () => {
  assert.deepEqual(validateQuestionBank(bank), []);
  assert.equal(bank.questions.length, 15);
});

test("5 10 and 15 question modes stay balanced across five dimensions", () => {
  for (const count of [5, 10, 15]) {
    const selected = selectBalancedQuestions(bank.questions, count);
    assert.equal(selected.length, count);
    const perDimension = count / 5;
    const counts = new Map();
    for (const q of selected) counts.set(q.dimension, (counts.get(q.dimension) ?? 0) + 1);
    assert.deepEqual([...counts.values()].sort(), Array(5).fill(perDimension));
  }
});

test("diagnostic variants stay deterministic, balanced, and rotate repeats", () => {
  for (const count of [5, 10]) {
    const first = selectBalancedQuestions(bank.questions, count, 0);
    const same = selectBalancedQuestions(bank.questions, count, 0);
    const next = selectBalancedQuestions(bank.questions, count, 1);

    assert.deepEqual(first.map((q) => q.id), same.map((q) => q.id));
    assert.notDeepEqual(first.map((q) => q.id), next.map((q) => q.id));
    assert.equal(new Set(first.map((q) => q.id)).size, count);
    assert.equal(new Set(next.map((q) => q.id)).size, count);
  }

  const all = selectBalancedQuestions(bank.questions, 15, 2);
  assert.equal(all.length, 15);
  assert.equal(new Set(all.map((q) => q.id)).size, 15);
});

test("diagnostic selection interleaves dimensions instead of blocking by dimension", () => {
  const selected = selectBalancedQuestions(bank.questions, 10, 0);
  assert.deepEqual(
    selected.slice(0, 5).map((q) => q.dimension),
    ["syntax", "reading", "debug", "algorithm", "implementation"],
  );
  assert.deepEqual(
    selected.slice(5, 10).map((q) => q.dimension),
    ["syntax", "reading", "debug", "algorithm", "implementation"],
  );
});

test("unsupported question counts and invalid variants are rejected", () => {
  assert.throws(() => selectBalancedQuestions(bank.questions, 7), /Unsupported quiz count/);
  assert.throws(() => selectBalancedQuestions(bank.questions, 5, -1), /Invalid diagnostic variant/);
  assert.throws(() => selectBalancedQuestions(bank.questions, 5, 1.5), /Invalid diagnostic variant/);
});


test("diagnostic model is explicitly non-readiness authority", () => {
  assert.equal(skillModel.scope, "diagnostic-only");
  assert.equal(skillModel.runtimeAuthority, false);
  assert.equal(skillModel.readinessAuthority, false);
  assert.equal(skillModel.canonicalLearningSkillMap, "Skill Map v3");
  assert.ok(skillModel.bands.every((band) => band.label.startsWith("本次題組：")));
  assert.ok(!levelBand(73).label.includes("準備"));
  assert.ok(!levelBand(100).label.includes("實戰"));
});

test("all-correct answers produce 100 across dimensions", () => {
  const answers = Object.fromEntries(bank.questions.map((q) => [q.id, q.correctIndex]));
  const r = scoreQuiz(bank.questions, answers);
  assert.equal(r.overall, 100);
  assert.equal(r.confidence, 1);
  for (const score of Object.values(r.scores)) assert.equal(score, 100);
  assert.equal(levelBand(r.overall).id, "strong");
  assert.equal(recommend(r, catalog.products).productId, "P4-MOCK");
});

test("five-question all-correct mode still scores all dimensions at 100", () => {
  const questions = selectBalancedQuestions(bank.questions, 5);
  const answers = Object.fromEntries(questions.map((q) => [q.id, q.correctIndex]));
  const r = scoreQuiz(questions, answers);
  assert.equal(r.total, 5);
  assert.equal(r.overall, 100);
  for (const score of Object.values(r.scores)) assert.equal(score, 100);
});

test("all-wrong answers produce foundation recommendation", () => {
  const answers = Object.fromEntries(bank.questions.map((q) => [q.id, (q.correctIndex + 1) % q.choices.length]));
  const r = scoreQuiz(bank.questions, answers);
  assert.equal(r.overall, 0);
  assert.equal(r.misses.length, 15);
  assert.equal(recommend(r, catalog.products).productId, "P1-30DAY");
});

test("debug weakness routes to debug product when overall is not low", () => {
  const answers = Object.fromEntries(bank.questions.map((q) => [q.id, q.correctIndex]));
  for (const q of bank.questions.filter((x) => x.dimension === "debug")) answers[q.id] = (q.correctIndex + 1) % q.choices.length;
  const r = scoreQuiz(bank.questions, answers);
  assert.equal(r.weakest, "debug");
  assert.equal(r.overall, 80);
  assert.equal(recommend(r, catalog.products).productId, "P2-DEBUG");
});

test("topErrorTags aggregates repeated tags", () => {
  const tags = topErrorTags([{ errorTags: ["a", "b"] }, { errorTags: ["a"] }]);
  assert.deepEqual(tags[0], { tag: "a", count: 2 });
});

test("wrong-answer review prioritizes the weakest dimension and never exceeds limit", () => {
  const answers = Object.fromEntries(bank.questions.map((q) => [q.id, q.correctIndex]));
  const debugQuestions = bank.questions.filter((q) => q.dimension === "debug");
  const syntaxQuestion = bank.questions.find((q) => q.dimension === "syntax");
  for (const q of [...debugQuestions, syntaxQuestion]) answers[q.id] = (q.correctIndex + 1) % q.choices.length;
  const r = scoreQuiz(bank.questions, answers);
  const review = buildReviewItems(bank.questions, r.misses, "debug", 3);
  assert.equal(review.length, 3);
  assert.ok(review.every((item) => item.dimension === "debug"));
  assert.ok(review.every((item) => item.correct && item.explanation));
});
