# WorkflowDNA

[GitHub repository](https://github.com/parvjain16/Workflowdna)

WorkflowDNA maps fictional Atlas Technologies' reimbursement process against a local JSON policy. A custom River AI model recommends changes, while FastAPI verifies required controls. The Next.js dashboard visualizes current and proposed workflows and exports a report. A model lab compares original and trained outputs on five held-out examples.

## Run locally

Requirements: Node.js 20.9+ and Python 3.12 recommended. `uv` is optional.

```sh
bash scripts/setup.sh
# Add your River API key to .env. Never commit .env.
bash scripts/start.sh
```

Open **http://127.0.0.1:3000**. Backend health: http://127.0.0.1:8000/api/health.
The servers bind to your computer only. Source files and reports are local; River authentication, training, and inference use River Cloud and account credits. Saved adapter weights live on River; `artifacts/river_checkpoint.json` stores their returned checkpoint path.

If dependencies are already installed, only the start command is needed. Use Ctrl+C to stop both servers. The backend reads the root `.env`; the key is never sent to the browser. Another account needs access to the saved checkpoint or must run its own training job.

## What the demo does

- Shows Atlas Technologies' current four-approval, 12-business-day process.
- Sends the written policy, structured rules, workflow, and expense scenario to the saved River inference checkpoint.
- Independently validates model proposals against the policy; invalid or unsafe answers produce an explicit error with no fallback model result.
- Shows a before/after workflow, clause citations, projected savings, and an exportable JSON report.
- Provides a model lab with original-versus-trained metrics and all five raw held-out responses.

For a normal **$750** expense with a receipt, the reference policy requires manager and finance approval. Removing department-head and CFO waits changes **12 days → 6 days**, **4 approvals → 2**, a **50% projected reduction**. Amounts above $1,000 require the department head; above $5,000 also require the CFO. Exceptions and missing receipts retain all controls for manual review. These are synthetic sequential business-day estimates, not measured company outcomes.

## Train and compare on River

The scripts follow the official [River supervised fine-tuning guide](https://docs.river.ai/guides/sft/) and [Python API reference](https://docs.river.ai/python-api/) for `river-client==0.11.0`.

```sh
source .venv/bin/activate
python -m training.train_river --epochs 3 --batch-size 4
```

`data/train.jsonl` contains exactly **20** labeled synthetic scenarios. `data/eval.jsonl` contains **five** distinct scenarios held out from gradient updates. The same model-specific chat protocol and generation settings are used before training and when sampling the saved trained checkpoint. Prompt tokens are masked from the loss. Training performs LoRA updates and saves with `mode="inference"`.

Evidence is written only after actual operations:

- `artifacts/river_status.json`: current run status; never interpreted as proof of completed training by itself.
- `artifacts/river_checkpoint.json`: the actual returned River checkpoint path and training metadata.
- `artifacts/river_evaluation.json`: original responses, per-step losses, saved-checkpoint responses, exact-match, approval, formatting, safety, and policy-guardrail metrics.
- Earlier interrupted attempts, when present, are retained separately and excluded from the final comparison.

The app displays "trained" only when a valid checkpoint and matching completed evaluation exist. It does not simulate training, manufacture checkpoints, silently substitute deterministic outputs, or promise that fine-tuning improves every metric. These five examples were inspected during development, so this is a small development holdout, not an untouched external benchmark.

## Verified River result

The completed 15-update run saved an inference checkpoint and sampled it on all five held-out scenarios using the same no-thinking Qwen chat protocol as the original model.

| Metric | Original model | Saved trained checkpoint |
| --- | --- | --- |
| Exact structured matches | 0/5 | 5/5 |
| Correct approval routing | 2/5 | 5/5 |
| Valid structured responses | 2/5 | 5/5 |
| Passes all policy checks | 0/5 | 5/5 |

Checkpoint: `river://11b25b7a-4614-4830-88fb-de82e34bfa29/sampler_weights/workflowdna-2026-09-28T00-00-26-490564-00-00`. These are actual observed development-holdout results, not a claim about real-world accuracy. The full evidence is in `artifacts/river_evaluation.json`.

## Tests and build

```sh
.venv/bin/python -m pytest -q
npm --prefix frontend run typecheck
npm --prefix frontend run build
# With both local servers running:
npm --prefix frontend test
# Uses system Chrome and real River inference (incurs credits):
npm --prefix frontend run test:e2e
```

Python tests cover thresholds, manual-review controls, malformed inputs, rejected model proposals, unavailable checkpoints, truthful metadata, split isolation, prompt masks, and inference protocol consistency. HTTP smoke tests verify the live frontend/backend proxy without paid inference. The application is also checked in a browser; real River behavior is recorded separately in the evaluation report.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/company` | Written policy, rules, and workflow |
| `GET /api/training` | Dataset counts and evidence-backed River status |
| `GET /api/evaluation` | Actual before/after outputs with scenarios |
| `POST /api/analyze` | `{ "amount": 750, "exception": false, "receipt_present": true, "engine": "river" }` |

The `rules` engine is retained only as an explicitly labeled backend diagnostic for tests. The user interface uses River exclusively. Rule calculations validate model proposals and compute durations; they are not represented as trained model output.

## Scope and submission

Written clauses and human-maintained structured policy rules are stored together; automatic extraction from arbitrary policy prose is incomplete. This demonstration covers one fictional process and does not execute changes in real reimbursement systems. It has no production authentication or deployment.

See [the submission checklist](docs/SUBMISSION.md), [limitations](docs/LIMITATIONS.md), and [training details](training/README.md). To create a source-and-evidence ZIP with credentials excluded:

```sh
python3 scripts/package_submission.py
```

No screen recording is included. `.env`, installed dependencies, caches, and private credentials must never be submitted.
