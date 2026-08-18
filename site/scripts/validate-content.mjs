import fs from "node:fs";
import { validateQuestionBank } from "../js/engine.js";
const bank = JSON.parse(fs.readFileSync(new URL("../data/questions.v1.json", import.meta.url), "utf8"));
const errors = validateQuestionBank(bank);
if (bank.questions.length !== 15) errors.push(`expected 15 questions, got ${bank.questions.length}`);
if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
console.log(`Question bank ${bank.version}: ${bank.questions.length} questions — VALID`);
