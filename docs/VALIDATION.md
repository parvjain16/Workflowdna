# Verified MVP status

Validated September 27, 2026 (America/Los_Angeles).

## Working

- Next.js dashboard at `http://127.0.0.1:3000`, with Python FastAPI at `127.0.0.1:8000`.
- Real River authentication, model access, 15 supervised optimizer updates on 20 synthetic examples, inference checkpoint save, and independent saved-checkpoint inference.
- Original-versus-trained evaluation on five examples held out from gradient updates, with raw outputs retained. The same no-thinking Qwen chat protocol and generation settings were used for both.
- Policy-grounded model proposals with independent required-control, manual-review, citation, and output-shape checks.
- Before/after workflow, current/proposed durations, written policy, model lab, raw evaluation inspection, and downloaded JSON reports.
- Responsive desktop and mobile layouts.

## Actual River results

| Metric | Original | Saved trained checkpoint |
| --- | --- | --- |
| Exact structured output | 0/5 | 5/5 |
| Correct approval list | 2/5 | 5/5 |
| Valid structured response | 2/5 | 5/5 |
| Passes every policy guardrail | 0/5 | 5/5 |

The two valid original responses had correct approval lists but incomplete citations. Other responses failed approval-list validation. The 0/5 score must not be described as zero general reasoning ability.

Checkpoint: `river://11b25b7a-4614-4830-88fb-de82e34bfa29/sampler_weights/workflowdna-2026-09-28T00-00-26-490564-00-00`.

`artifacts/river_evaluation.json` records the actual run. An independent audit recomputed metrics from every raw response, matched the current dataset hashes, and verified all five trained outputs against backend guardrails. `artifacts/river_inference_smoke.json` records a separate real saved-checkpoint API call for the $750 scenario.

## Checks completed

| Check | Result |
| --- | --- |
| Python backend and training tests | 58 passed; 6 additional subtests passed |
| Live HTTP frontend/backend smoke tests | 6 passed |
| Playwright tests using actual River inference | 2 passed in 29.3 seconds |
| TypeScript check | Passed |
| Next.js production build | Passed |
| Browser runtime exceptions during desktop flow | None observed |
| Mobile page overflow at 390px | None observed; workflow diagram has its own horizontal scroll |

Playwright verified the real $750 result (12→6 days), a real $2,600 result (12→9 days), and missing-receipt review (12→12 days). It checked the Before/After/Compare controls, policy navigation, all five evaluation rows, expandable raw responses, report download, and mobile navigation. Screenshots: `docs/dashboard.png`, `docs/model-comparison.png`, and `docs/mobile.png`.

One dependency deprecation warning remains: the installed Starlette test client warns about its httpx adapter. It did not fail tests or application requests. An initial mobile test used the desktop-only accessible name including the hidden SFT badge; the selector was corrected, and both tests were rerun successfully. No app behavior was mocked in these browser tests.

## Deliberate limits

- One fictional company, one reimbursement process, synthetic durations, and a tiny same-policy development holdout; not production reliability evidence.
- Written policy and structured rules are manually maintained together. Arbitrary-document ingestion and automatic extraction are incomplete.
- Time savings are projected elapsed business days; no real operational savings were measured.
- Recommendations do not execute changes in an external reimbursement system.
- No GBrain integration, production authentication, or public application deployment.
- River weights and inference require account access/network connectivity; the local checkpoint manifest is not a downloadable copy of the model weights.
- The user replaced the recording request with a written demo script. No MP4 recording was created.

See `docs/DEMO_SCRIPT.md` for the verified 85-second judge walkthrough and `docs/HACKATHON.md` for the submission checklist.
