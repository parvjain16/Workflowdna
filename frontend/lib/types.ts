export type Engine = "river";
export type Scenario = { amount: number; exception: boolean; receipt_present: boolean; engine: Engine };
export type Step = { id: string; label: string; role: string; days: number; type: string; reason?: string; clause_ids?: string[] };
export type Company = {
  name: string;
  policy: { id: string; version: string; title: string; source: string; clauses: { id: string; text: string }[] };
  workflow: { id: string; name: string; description: string; steps: Step[] };
};
export type Analysis = {
  company: string; workflow_name: string; engine: Engine; engine_label: string; scenario: Scenario; policy_version: string;
  current_steps: Step[]; proposed_steps: Step[]; removed_steps: Step[]; required_approvals: string[];
  findings: { title: string; description: string; clause_ids: string[] }[];
  metrics: { current_days: number; proposed_days: number; saved_days: number; savings_percent: number; current_approvals: number; proposed_approvals: number };
  compliance: { status: string; message: string; clause_ids: string[] };
  assumptions: string[]; model: { status: string; message: string; checkpoint?: string };
};
export type Training = {
  train_count: number; eval_count: number;
  river: { status: string; checkpoint?: string | null; message?: string };
  gbrain: { status: string; message: string };
};
export type Prediction = { required_approvals: string[]; removed_approvals: string[]; review_required: boolean; clause_ids: string[] };
export type EvaluationResult = { id: string; scenario?: Omit<Scenario, "engine">; expected: Prediction; prediction?: Prediction; raw_prediction: string; valid: boolean; exact_match: boolean; approval_match: boolean; safe: boolean; error?: string };
export type EvaluationStage = { metrics: Record<string, number>; results: EvaluationResult[] };
export type Evaluation = { status: string; message?: string; base_model?: string; checkpoint?: string; completed_at?: string; generation?: { max_tokens: number; temperature: number; seed: number }; before?: EvaluationStage; after_checkpoint?: EvaluationStage; loss_history?: { step: number; loss: number }[] };
