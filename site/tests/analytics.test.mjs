import test from "node:test";
import assert from "node:assert/strict";
import { buildRemoteEvent, getAttribution } from "../js/analytics.js";

test("UTM attribution has deterministic defaults", () => {
  assert.deepEqual(getAttribution(""), {
    source: "direct",
    medium: "none",
    campaign: "none",
    content: "none",
  });
  assert.deepEqual(getAttribution("?utm_source=threads&utm_medium=social&utm_campaign=launch&utm_content=debug01"), {
    source: "threads",
    medium: "social",
    campaign: "launch",
    content: "debug01",
  });
});

test("individual quiz answers are never eligible for remote upload", () => {
  assert.equal(buildRemoteEvent({ name: "quiz_answer", questionId: "Q01", answerIndex: 2 }), null);
});

test("remote event uses an allowlist and excludes exact scores and arbitrary fields", () => {
  const remote = buildRemoteEvent({
    name: "quiz_complete",
    sessionId: "session-test",
    at: "2026-08-18T00:00:00.000Z",
    page: "/APCS-Practice/",
    source: "threads",
    medium: "social",
    campaign: "launch_v1",
    content: "debug01",
    overall: 47,
    weakest: "debug",
    elapsedSec: 321,
    email: "must-not-pass@example.com",
    answerIndex: 1,
  });

  assert.equal(remote.name, "quiz_complete");
  assert.equal(remote.weakest, "debug");
  assert.equal(remote.elapsedSec, 321);
  assert.equal("overall" in remote, false);
  assert.equal("email" in remote, false);
  assert.equal("answerIndex" in remote, false);
});
