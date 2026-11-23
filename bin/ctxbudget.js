#!/usr/bin/env node
/**
 * ctxbudget — Check if your prompt fits in a local LLM's context window.
 * Zero dependencies. Works offline.
 */
const fs = require("fs");
const path = require("path");

const models = JSON.parse(
  fs.readFileSync(path.join(__dirname, "..", "models.json"), "utf8")
).models;

function fmtTokens(n) {
  if (n >= 1024) return n % 1024 === 0 ? `${n / 1024}K` : `${(n / 1024).toFixed(1)}K`;
  return String(n);
}

function findModel(query) {
  const q = query.toLowerCase().trim();
  let m = models.find((x) => x.id === q);
  if (m) return m;
  const partial = models.filter((x) => x.id.includes(q));
  if (partial.length === 1) return partial[0];
  if (partial.length > 1) {
    console.error(`Multiple matches: ${partial.slice(0, 5).map((x) => x.id).join(", ")}`);
    process.exit(1);
  }
  m = models.find((x) => x.name.toLowerCase().includes(q));
  return m || null;
}

function listModels() {
  console.log(`\n  Known Local LLMs (${models.length} models)\n`);
  const groups = {};
  for (const m of [...models].sort((a, b) => b.context - a.context || a.params_b - b.params_b)) {
    (groups[m.context] ||= []).push(m);
  }
  for (const ctx of Object.keys(groups).map(Number).sort((a, b) => b - a)) {
    console.log(`  ${fmtTokens(ctx)} context:`);
    for (const m of groups[ctx]) console.log(`    ${m.id.padEnd(35)} ${String(m.params_b).padStart(5)}B`);
    console.log();
  }
}

function budget(model, { system = 0, user = 0, context = 0, reserve = 0 }) {
  const ctx = model.context;
  const totalInput = system + user + context;
  const usable = ctx - reserve;
  const margin = usable - totalInput;

  console.log(`\n  ${"=".repeat(50)}`);
  console.log(`  ${model.name} — Context Budget`);
  console.log(`  ${"=".repeat(50)}\n`);
  console.log(`  Total window:     ${fmtTokens(ctx).padStart(10)} tokens`);
  console.log(`  ${"─".repeat(40)}`);
  if (system) console.log(`  System prompt:    ${fmtTokens(system).padStart(10)} tokens  (${((system / ctx) * 100).toFixed(1)}%)`);
  if (user) console.log(`  User message:     ${fmtTokens(user).padStart(10)} tokens  (${((user / ctx) * 100).toFixed(1)}%)`);
  if (context) console.log(`  Retrieved ctx:    ${fmtTokens(context).padStart(10)} tokens  (${((context / ctx) * 100).toFixed(1)}%)`);
  console.log(`  ${"─".repeat(40)}`);
  console.log(`  Total input:      ${fmtTokens(totalInput).padStart(10)} tokens  (${((totalInput / ctx) * 100).toFixed(1)}%)`);
  if (reserve) console.log(`  Output reserve:   ${fmtTokens(reserve).padStart(10)} tokens`);
  console.log(`  Usable budget:    ${fmtTokens(usable).padStart(10)} tokens`);
  console.log(`\n  [${margin >= 0 ? "PASS" : "FAIL"}] Margin: ${margin >= 0 ? "+" : ""}${fmtTokens(Math.abs(margin))} tokens\n`);
  process.exitCode = margin >= 0 ? 0 : 1;
}

function fitCheck(model, totalInput, reserve = 0) {
  const ctx = model.context;
  const usable = ctx - reserve;
  const fits = totalInput <= usable;
  const pct = (totalInput / ctx) * 100;
  const margin = usable - totalInput;

  console.log(`\n  Model:      ${model.name} (${fmtTokens(ctx)} context)`);
  console.log(`  Input:      ${fmtTokens(totalInput)} tokens`);
  if (reserve) console.log(`  Reserve:    ${fmtTokens(reserve)} tokens (for output)`);
  console.log(`  Usable:     ${fmtTokens(usable)} tokens`);
  console.log(`  Usage:      ${pct.toFixed(1)}% of context window`);
  console.log(`\n  Result:     [${fits ? "PASS" : "FAIL"}] ${fits ? "FITS" : "DOES NOT FIT"}\n`);
  process.exitCode = fits ? 0 : 1;
}

function showModel(model) {
  console.log(`\n  ${model.name}`);
  console.log(`  ID:         ${model.id}`);
  console.log(`  Parameters: ${model.params_b}B`);
  console.log(`  Context:    ${fmtTokens(model.context)} tokens (${model.context.toLocaleString()})\n`);
}

// --- arg parsing ---
const argv = process.argv.slice(2);
let model = null, tokens = null;
let system = 0, user = 0, context = 0, reserve = 0, list = false, json = false;

for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === "--list" || a === "-l") list = true;
  else if (a === "--json" || a === "-j") json = true;
  else if (a === "--system" || a === "-s") system = parseInt(argv[++i], 10);
  else if (a === "--user" || a === "-u") user = parseInt(argv[++i], 10);
  else if (a === "--context" || a === "-c") context = parseInt(argv[++i], 10);
  else if (a === "--reserve" || a === "-r") reserve = parseInt(argv[++i], 10);
  else if (!model) model = a;
  else if (tokens === null && !isNaN(parseInt(a, 10))) tokens = parseInt(a, 10);
}

if (list || !model) { listModels(); process.exit(0); }

const m = findModel(model);
if (!m) { console.error(`Unknown model '${model}'. Use --list to see available models.`); process.exit(1); }

if (system || user || context) budget(m, { system, user, context, reserve });
else if (tokens !== null) fitCheck(m, tokens, reserve);
else showModel(m);
