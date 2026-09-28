# WorkflowDNA — 85-second demo script

Before recording: open http://127.0.0.1:3000 and click **Workflow overview**. Keep **Expense amount** at **$750**, **Receipt attached** checked, and **Policy exception** unchecked. Wait for **Analysis ready** before starting. The dashboard loads a verified River result automatically; click **Analyze workflow** on camera to show a fresh, real inference request.

| Time | Click or show | Say |
| --- | --- | --- |
| 0:00–0:11 | Show the **Current turnaround** card and the four approvals in the diagram. | “This is WorkflowDNA. At fictional Atlas Technologies, every reimbursement goes through four approvals and takes twelve business days. We find where policy allows a faster path.” |
| 0:11–0:24 | Point to the **$750** input and checked **Receipt attached** box. Click **Analyze workflow**. Wait for **Analysis ready** before continuing. | “Let’s run this expense through our custom River model. It reads the workflow and Atlas’s policy, then proposes a route that keeps required controls.” |
| 0:24–0:40 | In **Workflow comparison**, click **Before**, then **After**, then **Compare**. Point to the crossed-out department-head and CFO approvals and the 12 → 6 day cards. | “Before, there are four approvals. After, manager and finance stay; department head and CFO are removed. That projects six business days saved per request.” |
| 0:40–0:53 | Click **Company policy**. Show **P2**, **P3**, and **P4**. | “Here’s why: for seven hundred fifty dollars, policy requires manager and finance. Department-head approval begins above one thousand dollars; CFO approval above five thousand.” |
| 0:53–1:03 | Click **Export report** in the upper right. Point to the downloaded `workflowdna-atlas-analysis.json` file. | “I can export this exact result as a JSON report, including the recommendation, policy source, and model evidence.” |
| 1:03–1:14 | Click **Model lab**. Show the saved River checkpoint, **20 training examples**, and **5 held-out examples**. | “We fine-tuned on twenty synthetic examples with River and saved an inference checkpoint. Five separate scenarios were held out of training.” |
| 1:14–1:27 | Scroll to the **Before fine-tuning / After fine-tuning** cards and the five-row comparison table. | “The original model had zero exact structured matches on those five cases. The trained checkpoint had five, and all five passed our policy checks. You can inspect every response below.” |

Pause while River responds after **Analyze workflow**. The analysis may take a few seconds because it calls the saved checkpoint. Aim for 80–90 seconds rather than rushing the final comparison.

These are real results from `artifacts/river_evaluation.json`, and the exported report was verified in a live browser test. The company and durations are fictional, savings are projected, and five same-policy cases are a small development evaluation rather than a production accuracy measure. There is no GBrain integration.
