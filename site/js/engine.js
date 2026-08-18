const DIMENSIONS = ["syntax", "reading", "debug", "algorithm", "implementation"];

export function scoreQuiz(questions, answers) {
  const byDimension = Object.fromEntries(DIMENSIONS.map((id) => [id, { correct: 0, total: 0 }]));
  const misses = [];
  let answered = 0;

  for (const q of questions) {
    if (!byDimension[q.dimension]) throw new Error(`Unknown dimension: ${q.dimension}`);
    byDimension[q.dimension].total += 1;
    const answer = answers[q.id];
    if (Number.isInteger(answer)) answered += 1;
    if (answer === q.correctIndex) {
      byDimension[q.dimension].correct += 1;
    } else {
      misses.push({
        questionId: q.id,
        dimension: q.dimension,
        tags: q.tags ?? [],
        errorTags: q.errorTags ?? [],
        selectedIndex: Number.isInteger(answer) ? answer : null,
        correctIndex: q.correctIndex,
      });
    }
  }

  const scores = {};
  for (const id of DIMENSIONS) {
    const d = byDimension[id];
    scores[id] = d.total ? Math.round((d.correct / d.total) * 100) : 0;
  }

  const overall = Math.round(DIMENSIONS.reduce((sum, id) => sum + scores[id], 0) / DIMENSIONS.length);
  const weakest = [...DIMENSIONS].sort((a, b) => scores[a] - scores[b] || DIMENSIONS.indexOf(a) - DIMENSIONS.indexOf(b))[0];
  const strongest = [...DIMENSIONS].sort((a, b) => scores[b] - scores[a] || DIMENSIONS.indexOf(a) - DIMENSIONS.indexOf(b))[0];
  const confidence = questions.length ? Number((answered / questions.length).toFixed(2)) : 0;

  return { overall, scores, weakest, strongest, confidence, answered, total: questions.length, misses };
}

export function levelBand(overall) {
  if (overall < 40) return { id: "foundation", label: "基礎需補強" };
  if (overall < 60) return { id: "developing", label: "正在建立解題能力" };
  if (overall < 80) return { id: "ready", label: "具備穩定基礎" };
  return { id: "strong", label: "可往進階與模擬實戰" };
}

export function recommend(result, products = []) {
  const productMap = Object.fromEntries(products.map((p) => [p.id, p]));
  let productId = "P1-30DAY";
  let reason = "以結構化訓練補齊最低能力維度。";
  let ruleId = "R-DEFAULT";

  if (result.overall < 45) {
    ruleId = "R-LOW";
    productId = "P1-30DAY";
    reason = "先建立完整的題意→步驟→程式流程，比單點補洞更有效。";
  } else if (result.weakest === "debug" && result.scores.debug < 70) {
    ruleId = "R-DEBUG";
    productId = "P2-DEBUG";
    reason = "你的主要失分來源偏向邊界、錯誤定位與程式可靠性。";
  } else if (["implementation", "algorithm"].includes(result.weakest) && result.overall < 75) {
    ruleId = "R-IMPL";
    productId = "P1-30DAY";
    reason = "你較需要把題意轉成可執行步驟，而不是重讀語法。";
  } else if (result.overall >= 75) {
    ruleId = "R-HIGH";
    productId = "P4-MOCK";
    reason = "基本能力已足夠，下一步應提高限時整合與穩定度。";
  }

  return {
    ruleId,
    productId,
    product: productMap[productId] ?? null,
    reason,
    freeNext: productMap["FREE-3Q"] ?? null,
  };
}

export function topErrorTags(misses, limit = 3) {
  const counts = new Map();
  for (const miss of misses) {
    for (const tag of miss.errorTags ?? []) counts.set(tag, (counts.get(tag) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, limit)
    .map(([tag, count]) => ({ tag, count }));
}

export function buildShareText(result, skillModel) {
  const labels = Object.fromEntries(skillModel.dimensions.map((d) => [d.id, d.label]));
  return [
    `我的 APCS 15 題診斷：${result.overall}/100`,
    `最需補強：${labels[result.weakest] ?? result.weakest}`,
    `最穩定：${labels[result.strongest] ?? result.strongest}`,
    "這不是正式 APCS 成績，只是練習方向診斷。",
  ].join("\n");
}

export function validateQuestionBank(bank) {
  const errors = [];
  if (!bank || !Array.isArray(bank.questions)) return ["questions must be an array"];
  const ids = new Set();
  const dimCount = Object.fromEntries(DIMENSIONS.map((d) => [d, 0]));

  for (const [i, q] of bank.questions.entries()) {
    const where = `questions[${i}]`;
    if (!q.id) errors.push(`${where}: missing id`);
    else if (ids.has(q.id)) errors.push(`${where}: duplicate id ${q.id}`);
    else ids.add(q.id);
    if (!DIMENSIONS.includes(q.dimension)) errors.push(`${where}: invalid dimension ${q.dimension}`);
    else dimCount[q.dimension] += 1;
    if (!Array.isArray(q.choices) || q.choices.length < 2) errors.push(`${where}: choices must have >=2 items`);
    if (!Number.isInteger(q.correctIndex) || q.correctIndex < 0 || q.correctIndex >= (q.choices?.length ?? 0)) {
      errors.push(`${where}: invalid correctIndex`);
    }
    if (!q.explanation) errors.push(`${where}: missing explanation`);
    if (!q.domain) errors.push(`${where}: missing domain`);
  }

  for (const d of DIMENSIONS) {
    if (dimCount[d] !== 3) errors.push(`dimension ${d}: expected 3 questions, got ${dimCount[d]}`);
  }
  return errors;
}

export { DIMENSIONS };
