# WorkflowDNA hackathon submission

WorkflowDNA is a local Next.js and Python demonstration of policy-aware reimbursement routing for fictional Atlas Technologies. River AI supplies the original language model, supervised fine-tuning, saved model weights, and checkpoint inference. No GBrain integration is included.

The source project is stored on this Mac at:

```text
/Users/parvj/.codex/visualizations/2026/09/27/01a0e53f-da08-7320-816d-e79cfd9c8206/WorkflowDNA
```

The browser and Python service run locally. River training and inference run remotely. The local checkpoint manifest records a `river://` reference to weights stored by River; it is not a downloaded model-weight file.

## Submission checklist

- [ ] Include the Next.js source in `frontend/`, Python service in `backend/`, River training and inference code in `training/`, and automated tests in `tests/`.
- [ ] Include `frontend/package.json`, `frontend/package-lock.json`, Python requirements files, `.env.example`, startup instructions in `README.md`, and the documentation under `docs/` and `training/README.md`.
- [ ] Include `data/company_policy.json`, exactly 20 examples in `data/train.jsonl`, and the separate five examples in `data/eval.jsonl`.
- [ ] Include the completed `artifacts/river_checkpoint.json`, `artifacts/river_evaluation.json`, and `artifacts/river_status.json`. If any operation remains incomplete, retain its truthful status and identify the missing evidence.
- [ ] Confirm the evaluation report's `checkpoint` equals the checkpoint manifest's `path`, its status is `evaluated`, and both `before.results` and `after_checkpoint.results` contain all five evaluation IDs and raw responses.
- [ ] Report the actual original-versus-checkpoint metrics from that report. Keep invalid responses and failed cases visible. Do not replace them with policy reference labels or results from a different model.
- [ ] Include the actual test/build results and a short screen recording showing the workflow, policy citations, and model comparison. A passing source test does not replace a live River inference demonstration.
- [ ] Exclude `.env`, API keys, `.venv/`, `node_modules/`, `.next/`, caches, and runtime logs. Legacy `local_checkpoint.json`, `local_evaluation.json`, and the separate local classifier are not River training evidence and are not part of this River-only demo.
- [ ] Check the hackathon's own portal for its required title, description, team details, repository/archive, and video fields. Those event-specific requirements are not supplied with this project.

The judge needs a River account/key with access to the checkpoint for fresh inference, or must train a new checkpoint with their own authorized account. An archive containing a `river://` reference does not grant access to its weights. Never include your API key in the submission.

## Two-minute demo sequence

Start the application using `README.md`, open the local URL printed at startup, and wait for River readiness before recording. The default frontend address is [http://127.0.0.1:3000](http://127.0.0.1:3000). River queue time can extend the sequence below.

1. **0:00–0:20 — Explain the problem.** Atlas Technologies sends every reimbursement through manager, department head, finance, and CFO approval. With submission and payment, the fictional sequential process takes 12 business days.
2. **0:20–0:50 — Show the trained model.** Analyze the default ordinary **$750** expense with a receipt. Identify the River engine and saved checkpoint. A successful, policy-validated response keeps manager and finance approval, removes department head and CFO approval, and displays **four approvals to two**, **12 days to six**, and **six days / 50% potential savings**. These are the policy reference outcome and projected durations; claim them as a model result only after that River request succeeds.
3. **0:50–1:10 — Show why it is allowed.** Open the cited policy clauses. P2 requires manager and finance; P3 adds department head only above $1,000; P4 adds CFO only above $5,000. Show that the policy is a local JSON file containing written clauses and human-authored structured rules.
4. **1:10–1:30 — Show an important boundary.** Mark a policy exception or remove the receipt and analyze again. A policy-valid response retains all four approvals, requires human review, and claims zero savings. If River fails or returns an invalid proposal, show the error; the application must not substitute a rules result as model inference.
5. **1:30–2:00 — Show evidence.** Open **Model lab**. Compare the original model with the **saved trained checkpoint**, point to the actual five-case scores, and expand a raw response. Show the saved checkpoint path. State the result as recorded, including a tie, regression, or failure if that is what occurred.

The dashboard's **Export report** action downloads the current analysis. It supplements the model evaluation artifact; it does not replace the before/after training evidence.

## The five held-out scenarios

These are policy reference outcomes, not claimed model predictions. Their inputs are excluded from the 20 training examples and from supervised gradient updates.

| Evaluation ID | Expense | Scenario | Required reference outcome | Projected days |
| --- | ---: | --- | --- | ---: |
| `atlas-eval-01` | $750 | Ordinary, receipt present | Manager + finance | 6 |
| `atlas-eval-02` | $2,600 | Ordinary, receipt present | Manager + department head + finance | 9 |
| `atlas-eval-03` | $7,600 | Ordinary, receipt present | All four approvals | 12 |
| `atlas-eval-04` | $860 | Policy exception | All four approvals; manual review | 12 |
| `atlas-eval-05` | $120 | Receipt missing | All four approvals; manual review | 12 |

Read the actual predictions from `artifacts/river_evaluation.json`: `before` contains sampling before fine-tuning; `after_checkpoint` contains sampling from the saved inference checkpoint. `after_live`, when present, is additional evidence from the trained in-memory weights. It does not establish checkpoint reload by itself.

Use the report's exact-match count, approval accuracy, valid structured-output rate, and safety/guardrail metrics as recorded. Exact match includes the full structured answer, including citations and ordering. The original model may already solve this narrow task; successful training does not guarantee higher scores. With five cases, one case changes a percentage by 20 points.

The training implementation follows River's [official supervised fine-tuning guide](https://docs.river.ai/guides/sft/) and [Python API reference](https://docs.river.ai/python-api/). Read [LIMITATIONS.md](LIMITATIONS.md) before describing the demo's scope or reliability.
