import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { scoreQuiz, levelBand, recommend, topErrorTags, validateQuestionBank } from "../js/engine.js";

const bank = JSON.parse(fs.readFileSync(new URL("../data/questions.v1.json", import.meta.url), "utf8"));
const catalog = JSON.parse(fs.readFileSync(new URL("../data/products.v1.json", import.meta.url), "utf8"));

test("question bank is structurally valid", () => {
  assert.deepEqual(validateQuestionBank(bank), []);
  assert.equal(bank.questions.length, 15);
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
