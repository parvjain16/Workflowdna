# WorkflowDNA — 85-second hackathon demo

Before recording, open http://127.0.0.1:3000. Set the expense to **$750**, keep **Receipt attached** checked and **Policy exception** unchecked. Click **Analyze workflow** and wait for **Analysis ready**. The screen should show the River fine-tuned model, 12 current days, 6 proposed days, and 6 projected days saved. Start recording after the real model result has loaded.

| Time | What to click or show | What to say |
| --- | --- | --- |
| 0:00–0:10 | Start on **Workflow overview** with the three metrics visible. | “This is WorkflowDNA. We help teams spot unnecessary waiting in company workflows—without removing the controls their policies require.” |
| 0:10–0:20 | Scroll to **Workflow comparison** and click **Before**. Point across the four approval steps. | “Here’s fictional Atlas Technologies. Every reimbursement passes through four approvals and takes twelve business days—even for this seven-hundred-fifty-dollar expense.” |
| 0:20–0:33 | Click **Company policy**. Show **P2**, then scroll to **P3** and **P4**. | “The policy only requires manager and finance approval at this amount. Department-head approval starts above one thousand dollars; CFO approval starts above five thousand.” |
| 0:33–0:47 | Click **Workflow overview**, scroll to the diagram, then click **After** and **Compare**. Show the two removed approvals and recommendation panel. | “Our custom River model recommends removing those two unnecessary approvals. Required controls stay, and projected turnaround drops from twelve to six business days—fifty percent less waiting.” |
| 0:47–1:00 | Click **Model lab**. Show the **saved inference checkpoint**, **20 training examples**, **5 held-out examples**, and **15 training updates**. | “Here’s the actual saved River checkpoint. We fine-tuned a custom model on twenty synthetic examples, with five separate scenarios held out of training.” |
| 1:00–1:15 | Scroll to the **Before fine-tuning / After fine-tuning** scorecards, then the **Unseen examples, side by side** table. | “On those same five cases, the original model produced zero exact matches. The trained checkpoint produced five, and every recommendation passed our policy checks.” |
| 1:15–1:25 | Scroll to **Inspect the evidence** and expand **atlas-eval-01**. End with the original and trained raw responses visible. | “You can inspect the raw responses here. This is a small synthetic demo, not a production accuracy claim. WorkflowDNA makes improvements you can trace back to policy.” |

## Presenter notes

- Speak naturally and pause briefly after “six business days” and “five.” The narration is approximately 175 words; allow 80–90 seconds including navigation.
- The workflow before/after comparison shows **projected process changes**. The Model lab before/after comparison shows **actual original-model versus saved-checkpoint outputs**. They are different comparisons.
- “Exact match” includes the approval list, removed approvals, review flag, and citations. The original model had two correct approval lists but incomplete citations; do not claim it had zero reasoning ability.
- The five cases were held out from gradient updates but inspected during development. Do not call them an untouched external benchmark.
- The policy is fictional and maintained in a local JSON file with written clauses plus human-authored structured rules. Do not claim automatic ingestion of arbitrary policy documents, measured real-world savings, or a GBrain integration.
- If a judge asks about exceptions: the working interface supports missing receipts and exceptions; these retain all controls for review. This optional extension requires another real inference request and is outside the 85-second script.

Verified source: `artifacts/river_evaluation.json` and `artifacts/river_inference_smoke.json`. The matching checkpoint is stored in `artifacts/river_checkpoint.json`.
