#!/usr/bin/env node
/**
 * Record only the real, completed River demo; never substitute API/DOM results.
 * Requires the app on DEMO_URL (default localhost:3000), completed River artifacts,
 * project .venv imageio-ffmpeg, system Chrome, and Playwright's ffmpeg helper.
 *
 * Preparation (one-time):
 *   uv pip install --python .venv/bin/python imageio-ffmpeg
 *   PLAYWRIGHT_BROWSERS_PATH=/tmp/workflowdna-playwright node frontend/node_modules/playwright-core/cli.js install ffmpeg
 * Run only after final UI/training verification:
 *   node scripts/record_demo.mjs
 */
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { mkdir, writeFile, stat, unlink } from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const exec = promisify(execFile);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(ROOT, 'frontend/package.json'));
process.env.PLAYWRIGHT_BROWSERS_PATH ||= '/tmp/workflowdna-playwright';
const { chromium } = require('@playwright/test');
const URL = process.env.DEMO_URL || 'http://127.0.0.1:3000';
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const OUTPUT = path.join(ROOT, 'WorkflowDNA_Demo.mp4');
const DEMO_DIR = path.join(ROOT, 'artifacts/demo');
const WIDTH = 1440;
const HEIGHT = 900;
const TARGET_SECONDS = 78;
const sleep = ms => new Promise(resolve => setTimeout(resolve, Math.max(0, ms)));

function requireTrue(condition, message) {
  if (!condition) throw new Error(message);
}
async function getJSON(endpoint) {
  const response = await fetch(`${URL}${endpoint}`, { signal: AbortSignal.timeout(20000) });
  requireTrue(response.ok, `${endpoint} returned HTTP ${response.status}.`);
  return response.json();
}
function narration(report, analysis) {
  const before = report.before.metrics;
  const after = report.after_checkpoint.metrics;
  const score = before.correct === after.correct
    ? `Both models matched ${after.correct} of ${after.total} cases exactly. Fine-tuning did not improve this small test's exact-match score.`
    : `Exact matches changed from ${before.correct} of ${before.total} before training to ${after.correct} of ${after.total} from the saved checkpoint.`;
  const sections = [
    ['00:00–00:08', 'WorkflowDNA helps teams find avoidable waiting. At fictional Atlas Technologies, every reimbursement currently needs four approvals and takes twelve business days.'],
    ['00:08–00:26', `For this seven-hundred-fifty-dollar expense, our River-trained model keeps manager and finance approvals. Removing two unnecessary approvals cuts projected turnaround from twelve to ${analysis.metrics.proposed_days} business days: ${analysis.metrics.savings_percent} percent less waiting. The comparison makes every change visible.`],
    ['00:26–00:40', 'Each recommendation traces to written policy. Department-head approval starts above one thousand dollars, and CFO approval above five thousand. Missing receipts and exceptions retain all controls for review.'],
    ['00:40–00:55', 'We trained with twenty synthetic examples using River supervised fine-tuning, then saved an inference checkpoint. Five separate scenarios were evaluated before and after training.'],
    ['00:55–01:03', score],
    ['01:03–01:12', 'The raw responses are inspectable, including failures. Five synthetic cases demonstrate the workflow; they do not establish production reliability.'],
    ['01:12–01:18', 'WorkflowDNA pairs policy-grounded improvements with real model evidence, clear controls, and transparent projected savings.'],
  ];
  return `# WorkflowDNA demo narration\n\nA matching voiceover script for the ${TARGET_SECONDS}-second silent screen recording. All scores below come from the completed River evaluation shown on screen.\n\n${sections.map(([time, text]) => `**${time}**\n\n${text}`).join('\n\n')}\n\nRecording: \`WorkflowDNA_Demo.mp4\`\n\nInference checkpoint: \`${report.checkpoint}\`\n\nEvaluation completed: ${report.completed_at}\n\nThe company and durations are fictional; savings are projected. Policy rules are manually authored in local JSON. No GBrain integration is included.\n`;
}

await mkdir(DEMO_DIR, { recursive: true });
const [training, evaluation] = await Promise.all([getJSON('/api/training'), getJSON('/api/evaluation')]);
requireTrue(training.river?.ready === true && training.river.status === 'trained', 'Recording blocked: the real River checkpoint is not ready.');
requireTrue(evaluation.status === 'evaluated' && evaluation.checkpoint_verified === true, 'Recording blocked: completed saved-checkpoint evaluation is unavailable.');
requireTrue(evaluation.checkpoint === training.river.checkpoint, 'Recording blocked: evaluation and inference checkpoints differ.');
for (const stage of [evaluation.before, evaluation.after_checkpoint]) {
  requireTrue(stage?.results?.length === 5 && stage.results.every(row => 'raw_prediction' in row), 'Recording blocked: five actual raw outputs are required for both models.');
  requireTrue(Number.isInteger(stage.metrics.correct) && stage.metrics.total === 5, 'Recording blocked: real exact-match counts are missing.');
}
const { stdout: ffmpegText } = await exec(path.join(ROOT, '.venv/bin/python'), ['-c', 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())']);
const ffmpeg = ffmpegText.trim();
await stat(ffmpeg);
await stat(CHROME);

let browser;
let context;
let rawPath;
const consoleErrors = [];
const scenes = [];
try {
  browser = await chromium.launch({ executablePath: CHROME, headless: true });
  context = await browser.newContext({
    viewport: { width: WIDTH, height: HEIGHT }, deviceScaleFactor: 1,
    colorScheme: 'light', reducedMotion: 'no-preference',
    recordVideo: { dir: path.join(DEMO_DIR, 'raw'), size: { width: WIDTH, height: HEIGHT } },
  });
  const page = await context.newPage();
  page.setDefaultTimeout(20000);
  page.on('pageerror', error => consoleErrors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  const analyzed = page.waitForResponse(response => response.url().endsWith('/api/analyze') && response.request().method() === 'POST', { timeout: 180000 });
  await page.goto(URL, { waitUntil: 'domcontentloaded' });
  const response = await analyzed;
  requireTrue(response.ok(), `Recording blocked: actual River analysis returned HTTP ${response.status()}.`);
  const analysis = await response.json();
  requireTrue(analysis.engine === 'river' && analysis.model?.status === 'policy_validated', 'Recording blocked: actual validated River inference is required.');
  requireTrue(analysis.model.checkpoint === evaluation.checkpoint, 'Recording blocked: live analysis used a different checkpoint.');
  requireTrue(analysis.scenario.amount === 750 && analysis.metrics.current_days === 12 && analysis.metrics.proposed_days === 6, 'Recording blocked: expected Atlas default scenario did not validate.');
  await page.getByTestId('current-days').waitFor({ state: 'visible' });
  await page.locator('.workflow-card').waitFor({ state: 'visible' });
  requireTrue(await page.getByRole('alert').count() === 0, 'Recording blocked: visible app errors.');
  await sleep(1000);
  await page.mouse.move(WIDTH - 30, HEIGHT - 20);

  const started = performance.now();
  async function beat(seconds) { await sleep(started + seconds * 1000 - performance.now()); }
  function mark(name) { scenes.push({ name, at_seconds: Number(((performance.now() - started) / 1000).toFixed(2)) }); console.log(`Scene: ${name}`); }
  async function smoothTo(locator, top = 135) {
    const box = await locator.boundingBox();
    requireTrue(box, 'A required demo section is missing.');
    const distance = box.y - top;
    const steps = 24;
    await page.mouse.move(WIDTH - 35, HEIGHT / 2);
    for (let i = 0; i < steps; i++) { await page.mouse.wheel(0, distance / steps); await sleep(28); }
    await sleep(200);
  }
  async function nav(name) { await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('button', { name: new RegExp(`^${name}(?:\\s+SFT)?$`) }).click(); await sleep(250); }
  const diagram = page.getByRole('group', { name: 'Diagram view' });

  mark('Overview: real saved-checkpoint result');
  await beat(8);
  await smoothTo(page.locator('.workflow-card'), 110);
  await diagram.getByRole('button', { name: 'Before', exact: true }).click();
  mark('Current workflow: four approvals');
  await beat(15);
  await diagram.getByRole('button', { name: 'After', exact: true }).click();
  mark('Recommended workflow: required controls retained');
  await beat(21);
  await diagram.getByRole('button', { name: 'Compare', exact: true }).click();
  mark('Before and after comparison');
  await beat(26);
  await nav('Company policy');
  await page.locator('.policy-document').waitFor({ state: 'visible' });
  mark('Written policy and local JSON provenance');
  await beat(33);
  await smoothTo(page.locator('#P3'), 245);
  mark('Threshold clauses and manual review controls');
  await beat(40);
  await nav('Model lab');
  await page.locator('.river-run-card').waitFor({ state: 'visible' });
  mark('Saved River checkpoint and dataset split');
  await beat(47);
  await smoothTo(page.locator('.score-grid'), 160);
  mark('Measured baseline and trained model scores');
  await beat(55);
  await smoothTo(page.locator('.evaluation-card'), 130);
  mark('Five held-out scenarios side by side');
  await beat(63);
  await smoothTo(page.locator('.raw-results'), 155);
  await page.locator('.raw-results summary').first().click();
  mark('Actual raw model outputs');
  await beat(72);
  await nav('Workflow overview');
  await page.getByTestId('saved-days').waitFor({ state: 'visible' });
  mark('Conclusion: projected savings');
  await beat(TARGET_SECONDS);
  const presentationSeconds = (performance.now() - started) / 1000;
  requireTrue(presentationSeconds <= 85, 'Recording exceeded its pacing budget; rerun after checking UI responsiveness.');
  await page.screenshot({ path: path.join(DEMO_DIR, 'WorkflowDNA_Demo_Preview.png') });
  await sleep(1000);
  rawPath = await page.video().path();
  await context.close(); context = null;
  await browser.close(); browser = null;
  requireTrue(consoleErrors.length === 0, `Recording blocked by ${consoleErrors.length} browser errors. Review the app before recording again.`);

  // Strip the real River loading/warmup from the front. Scene footage is neither
  // substituted nor sped up: only the pre-roll and final extra second are trimmed.
  let inspection;
  try { await exec(ffmpeg, ['-hide_banner', '-i', rawPath]); }
  catch (error) { inspection = error.stderr || ''; }
  const duration = inspection.match(/Duration: (\d+):(\d+):(\d+(?:\.\d+)?)/);
  requireTrue(duration, 'Could not determine raw video duration.');
  const rawSeconds = Number(duration[1]) * 3600 + Number(duration[2]) * 60 + Number(duration[3]);
  const trimStart = Math.max(0, rawSeconds - presentationSeconds - 1);
  await exec(ffmpeg, [
    '-y', '-hide_banner', '-loglevel', 'error', '-ss', trimStart.toFixed(3), '-i', rawPath,
    '-t', TARGET_SECONDS.toString(), '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19',
    '-pix_fmt', 'yuv420p', '-r', '30', '-movflags', '+faststart', OUTPUT,
  ], { maxBuffer: 4 * 1024 * 1024 });
  const output = await stat(OUTPUT);
  requireTrue(output.size > 100000, 'The generated MP4 is unexpectedly small.');
  await writeFile(path.join(ROOT, 'docs/NARRATION.md'), narration(evaluation, analysis));
  await writeFile(path.join(DEMO_DIR, 'recording_manifest.json'), JSON.stringify({
    recorded_at: new Date().toISOString(), url: URL, output: 'WorkflowDNA_Demo.mp4',
    width: WIDTH, height: HEIGHT, duration_seconds: TARGET_SECONDS, has_audio: false,
    narration: 'docs/NARRATION.md', checkpoint: evaluation.checkpoint, evaluation_completed_at: evaluation.completed_at,
    analysis_engine: analysis.engine, baseline_metrics: evaluation.before.metrics,
    trained_metrics: evaluation.after_checkpoint.metrics, projected_workflow_metrics: analysis.metrics,
    browser_errors: consoleErrors, scenes, bytes: output.size,
    capture: 'Playwright recordVideo; real UI and HTTP responses only; loading pre-roll trimmed',
  }, null, 2) + '\n');
  await unlink(rawPath);
  console.log(`Saved ${OUTPUT} (${(output.size / 1024 / 1024).toFixed(1)} MB, ${TARGET_SECONDS}s).`);
  console.log('Saved matching narration and recording manifest.');
} finally {
  if (context) await context.close();
  if (browser) await browser.close();
}
