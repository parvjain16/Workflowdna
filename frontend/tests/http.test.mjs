import assert from "node:assert/strict";
import { test } from "node:test";

const base = process.env.WORKFLOWDNA_URL || "http://127.0.0.1:3000";

test("Next.js serves the application with its identity and accessible navigation", async () => {
  const response = await fetch(base);
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /WorkflowDNA/);
  assert.match(html, /Main navigation/);
  assert.match(html, /Skip to main content/);
});

test("Next.js proxies to the live Python service", async () => {
  const response = await fetch(`${base}/api/health`);
  assert.equal(response.status, 200);
  assert.equal((await response.json()).status, "ok");
});

test("company endpoint exposes source policy and exactly 12 days / four approvals", async () => {
  const response = await fetch(`${base}/api/company`);
  assert.equal(response.status, 200);
  const company = await response.json();
  assert.equal(company.name, "Atlas Technologies");
  assert.equal(company.workflow.steps.reduce((sum, step) => sum + step.days, 0), 12);
  assert.equal(company.workflow.steps.filter(step => step.type === "approval").length, 4);
  assert.equal(company.policy.clauses.length, 5);
});

test("metadata is available without paid inference and does not expose a local engine", async () => {
  const response = await fetch(`${base}/api/training`);
  assert.equal(response.status, 200);
  const status = await response.json();
  assert.equal(status.train_count, 20);
  assert.equal(status.eval_count, 5);
  assert.equal(status.local, undefined);
  assert.ok(status.river);
});

test("invalid input is rejected through the frontend proxy without River usage", async () => {
  const response = await fetch(`${base}/api/analyze`, { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({amount: -1, engine:"river"}) });
  assert.equal(response.status, 422);
});

test("the retired local engine cannot be selected through the API", async () => {
  const response = await fetch(`${base}/api/analyze`, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({amount:750,engine:"local"})});
  assert.equal(response.status, 422);
});
