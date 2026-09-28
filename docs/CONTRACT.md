# WorkflowDNA implementation contract

Python backend: FastAPI on 127.0.0.1:8000. Next.js on localhost:3000 proxies /api/* to backend /api/*.

GET /api/health -> {status: "ok"}
GET /api/company -> {name, policy: {id, version, title, source, clauses: [{id,text}]}, workflow: {id,name,description,steps:[{id,label,role,days,type}]}, default_scenario:{amount,exception,receipt_present}}
GET /api/training -> {train_count,eval_count,river:{status,checkpoint,message,...},gbrain:{status:"not_connected",message}}
POST /api/analyze <- {amount:750,exception:false,receipt_present:true,engine:"river" (UI) or "rules" (explicit diagnostic only)}
-> {company,workflow_name,engine,engine_label,scenario,policy_version,current_steps,proposed_steps,removed_steps:[{id,label,role,days,type,reason,clause_ids}],required_approvals:[string],findings:[{title,description,clause_ids}],metrics:{current_days,proposed_days,saved_days,savings_percent,current_approvals,proposed_approvals},compliance:{status:"compliant"|"review_required",message,clause_ids},assumptions:[string],model:{status,message,checkpoint?}}

Steps use types submission, approval, payment. Baseline: submit expense (1d), manager (2d), department head (3d), finance (2d), CFO (3d), payment (1d): 12 days and 4 approvals. Standard amount <=1000 with receipt requires manager + finance (6d, 50% improvement). >1000 <=5000 additionally department head (9d); >5000 additionally CFO (12d). Exceptions retain all four and require manual review. Missing receipt returns manual review with no removals or claimed savings. Exact equality belongs to lower tier. Required roles are manager, department_head, finance, cfo. Always preserve baseline order.

Policy authored as local JSON with written clauses and machine-readable rules; explicitly maintained together by humans, not automatically extracted from prose. Unsupported/ambiguous cases fail closed. Synthetic durations are elapsed business days, sequential, projected savings only.

Training integration owned by training agent:
- data/train.jsonl exactly 20 examples, data/eval.jsonl exactly 5 distinct held-out examples, each {id,input,output}. input includes policy clauses/rules, workflow steps, scenario; output has required_approvals, removed_approvals, review_required, clause_ids.
- training/common.py: render_prompt(input_dict), parse_prediction(text), load_examples(path), evaluate_predictions(...).
- training/train_river.py CLI using documented river_client SFT, actual prompt mask, train-only 20, before/after eval-only 5, save_weights(mode="inference"), save actual river path in artifacts/river_checkpoint.json, raw eval and loss logs. Without credentials exit clearly and write truthful status; no placeholder checkpoint.
- artifacts/river_status.json is status evidence, artifacts/river_checkpoint.json only exists after success.
- GET training status reads those files, never hardcodes success.

The UI uses River exclusively. Policy rules are deterministic validation and an explicitly labeled backend diagnostic. No GBrain integration.

GET /api/evaluation returns actual before and after_checkpoint evaluations with metrics, raw results, scenarios, and loss history. Readiness requires the evaluated checkpoint to match the saved manifest and current policy.
