# WorkflowDNA scope and limitations

This is a hackathon demonstration of one fictional reimbursement policy. It is not a production workflow-management system, an autonomous policy interpreter, or evidence of measured operational savings.

## What the model and policy checks do

River AI is the only language-model provider used by the demo. The trained checkpoint proposes required approvals, removable approvals, review status, and policy citations. The Python service independently validates that proposal against the current human-authored policy controls before showing a recommendation and calculating savings.

The policy is stored in `data/company_policy.json`. Its written clauses and structured rules were authored together by humans. Automatic extraction of rules from arbitrary natural-language documents is not implemented. Agreement with these structured rules supports the fictional Atlas demo; it does not establish compliance with a real company's policies or law.

The application supports the supplied Atlas workflow and approval roles. Policy changes require review, refreshed examples, retraining, and evaluation. Missing receipts and explicitly marked exceptions require manual review with every existing approval retained. An absent or invalid model response is an error, not permission to remove a control.

The backend's explicit `rules` diagnostic mode is deterministic policy logic, not another AI provider or model output. The interface uses River checkpoint inference. There is no silent fallback to the diagnostic mode, a local classifier, or another AI service. No GBrain integration is implemented or needed for this submission.

## What the training demonstration establishes

The dataset contains 20 synthetic training examples and five separate synthetic evaluation examples. All 25 are instances of the same policy and reimbursement workflow; they are not examples from 25 organizations or 25 independent policies. The evaluation inputs and IDs are disjoint from the training split, and the five examples do not enter supervised gradient updates.

The five cases exercise three amount tiers, an exception, and a missing receipt. They do not cover arbitrary policies, contradictory documents, adversarial inputs, ambiguous evidence, other currencies, or a broad range of real employee situations. Five examples are too few to estimate production reliability. Development may inspect or rerun these same cases while debugging the training pipeline; exclusion from gradient updates does not make them a pristine external benchmark.

Targets are generated from the human-authored rules. This gives the demo a checkable reference answer, but it also makes the task narrow. A model can succeed here without learning general workflow analysis. A larger, independently authored and untouched evaluation set would be required for a broader quality claim.

The original and trained models may perform equally, or fine-tuning may reduce quality. Report the measured result without forcing an improvement claim. Training loss, valid JSON, correct approvals, complete policy citations, guardrail acceptance, and exact match measure different things. In particular, a conservative response that retains all controls can preserve required approvals while still failing to produce the precise policy-required routing or citations.

`artifacts/river_evaluation.json` preserves actual raw responses, including invalid outputs. `before` is the original comparison and `after_checkpoint` is the saved-checkpoint comparison. A checkpoint save alone proves neither successful reload nor accurate recommendations. Partial artifacts or incomplete status must remain labeled incomplete.

## Where execution and data live

The Next.js interface, Python service, policies, dataset files, and reports are local to the Mac. River performs remote training and inference using the configured account and credits. The prompts send the synthetic policy, workflow, and scenario to River. The inference adapter weights remain on River; `artifacts/river_checkpoint.json` stores the returned `river://` reference and provenance, not the model weights themselves.

Live inference needs network connectivity, valid server-side credentials, authorized model/checkpoint access, sufficient credits, and available River capacity. Queueing, timeouts, or revoked access can interrupt a demo even after a successful training run. A working key does not guarantee all future requests will succeed. The local site is not a public hosted deployment and cannot be assumed accessible to judges on another machine.

Keep credentials in the ignored root `.env` file. Do not submit that file or place the API key in browser code, screenshots, recordings, reports, or archives. A recipient needs their own authorized River access; a shared checkpoint path does not itself grant permission.

## Savings and operational scope

Atlas Technologies, its expenses, policy, and processing times are fictional. Durations are sequential elapsed business days assigned to the supplied workflow steps. The default ordinary $750 case removes two three-day approval steps, so the reference projection changes 12 days to six days. This is six days, or 50%, of potential time savings in that synthetic scenario.

Those figures are not observed cycle-time reductions, causal estimates, labor-cost savings, or a service-level promise. The model does not estimate the duration values. The backend calculates totals from the retained steps. There is no measurement of parallel processing, staffing, queues, rework, holidays, or downstream bottlenecks.

Recommendations do not execute changes in an external workflow, remove real approval controls, issue payments, or contact employees. There is no GBrain connection, enterprise identity/permissions integration, production audit system, or automated ingestion of company records. Any real deployment would need a separately designed and validated operational process.
