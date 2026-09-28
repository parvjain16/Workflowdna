"""FastAPI service with explicit engines and fail-closed policy validation."""
from __future__ import annotations

import hashlib
import importlib
import time
import json
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt

from backend.policy import ROOT, decide, load_company, validate_prediction

ARTIFACTS = ROOT / "artifacts"

app = FastAPI(title="WorkflowDNA", version="0.1.0", description="A fictional policy-aware reimbursement demonstration")


@app.exception_handler(RequestValidationError)
async def invalid_request(_request, exc: RequestValidationError) -> JSONResponse:
    # Do not echo non-finite JSON numbers (NaN/Infinity) into JSON error responses.
    # Including those raw inputs would make error serialization itself fail.
    details = [{"loc": error["loc"], "msg": error["msg"], "type": error["type"]} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": details})


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: Annotated[StrictInt | StrictFloat, Field(gt=0, le=1_000_000_000, allow_inf_nan=False)] = 750
    exception: StrictBool = False
    receipt_present: StrictBool = True
    engine: Literal["rules", "river"] = "river"


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/company")
def company() -> dict[str, Any]:
    return load_company()


def read_artifact(name: str) -> dict[str, Any] | None:
    path = ARTIFACTS / name
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text())
        if not isinstance(value, dict):
            raise ValueError("Expected an object")
        return value
    except (ValueError, OSError):
        return {"status": "invalid_artifact", "message": f"Cannot read {name}; retrain before using this checkpoint."}


def count_examples(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return sum(1 for line in path.read_text().splitlines() if line.strip() and isinstance(json.loads(line), dict))
    except (ValueError, OSError):
        return 0


def checkpoint_state() -> tuple[dict[str, Any] | None, str | None]:
    checkpoint = read_artifact("river_checkpoint.json")
    if checkpoint is None:
        return None, "No saved River inference checkpoint is available."
    if checkpoint.get("status") != "trained" or checkpoint.get("mode") != "inference":
        return None, "The saved River manifest is not a valid inference checkpoint."
    path = checkpoint.get("path")
    if not isinstance(path, str) or not path.startswith("river://") or len(path) <= 8 or any(c.isspace() for c in path):
        return None, "The saved River checkpoint path is invalid."
    if not isinstance(checkpoint.get("base_model"), str) or not checkpoint["base_model"].strip():
        return None, "The saved River checkpoint has no base model."
    policy_fingerprint = hashlib.sha256(json.dumps(load_company()["policy"], sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    if not isinstance(checkpoint.get("policy_fingerprints"), list) or policy_fingerprint not in checkpoint["policy_fingerprints"]:
        return None, "The policy changed after training. Retrain and evaluate before inference."
    return checkpoint, None


def evaluation_rows(section: Any, scenarios: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(section, dict) or not isinstance(section.get("metrics"), dict) or not isinstance(section.get("results"), list):
        return None
    # Only expose evidence fields, never arbitrary server or credential metadata.
    allowed = {"id", "expected", "raw_prediction", "prediction", "valid", "exact_match", "approval_match", "safe", "error"}
    results = []
    for record in section["results"]:
        if not isinstance(record, dict):
            continue
        row = {key: value for key, value in record.items() if key in allowed}
        row["scenario"] = scenarios.get(record.get("id"))
        results.append(row)
    return {"metrics": section["metrics"], "results": results}


@app.get("/api/evaluation")
def evaluation_status() -> dict[str, Any]:
    report = read_artifact("river_evaluation.json")
    if not report or report.get("status") == "invalid_artifact":
        return {
            "status": "invalid_artifact" if report else "not_evaluated",
            "message": "No readable River evaluation report is available yet. Metrics and outputs appear only after real River sampling.",
            "before": None, "after_checkpoint": None,
        }
    scenarios: dict[str, Any] = {}
    try:
        for line in (ROOT / "data" / "eval.jsonl").read_text().splitlines():
            if line.strip():
                example = json.loads(line)
                scenarios[example["id"]] = example["input"]["scenario"]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    before = evaluation_rows(report.get("before"), scenarios)
    after = evaluation_rows(report.get("after_checkpoint"), scenarios)
    checkpoint, checkpoint_error = checkpoint_state()
    expected_ids = set(scenarios)
    complete_sections = all(
        section and len(section["results"]) == 5
        and {row.get("id") for row in section["results"]} == expected_ids
        and all("raw_prediction" in row for row in section["results"])
        for section in (before, after)
    )
    verified = bool(len(expected_ids) == 5 and complete_sections and checkpoint
                    and report.get("checkpoint") == checkpoint["path"] and report.get("status") == "evaluated")
    metadata = {key: report[key] for key in (
        "base_model", "train_count", "eval_count", "checkpoint", "started_at", "completed_at", "generation", "hyperparameters", "loss_history"
    ) if key in report}
    return {
        **metadata,
        "status": "evaluated" if verified else "partial",
        "message": "Real River baseline and saved-checkpoint outputs on five held-out synthetic examples." if verified else (checkpoint_error or "River evaluation is in progress or incomplete; only completed sampling results are shown."),
        "before": before, "after_checkpoint": after,
        "checkpoint_verified": verified,
        "limitations": ["Five synthetic evaluation cases are a small demonstration, not evidence of production reliability.",
                        "Safety metrics and policy guardrails are distinct from exact-match accuracy."],
    }


@app.get("/api/training")
@app.get("/api/status")
def training_status() -> dict[str, Any]:
    status = read_artifact("river_status.json") or {
        "status": "not_started", "message": "River training has not started. No trained-model results are available yet.",
    }
    # The trainer writes sanitized messages; expose only the known status fields.
    river = {key: status[key] for key in ("status", "message", "base_model", "updated_at", "error_type", "docs") if key in status}
    checkpoint, checkpoint_error = checkpoint_state()
    evaluation = evaluation_status()
    ready = bool(status.get("status") == "trained" and checkpoint and evaluation.get("checkpoint_verified"))
    river.update(ready=ready, checkpoint=checkpoint["path"] if checkpoint else None,
                 metrics=evaluation["after_checkpoint"]["metrics"] if ready else None)
    if checkpoint:
        river.update(checkpoint_artifact="artifacts/river_checkpoint.json", base_model=checkpoint["base_model"])
    if river.get("status") == "trained" and not ready:
        river.update(status="evaluation_pending" if checkpoint else "invalid_checkpoint",
                     message=checkpoint_error or "Saved River checkpoint exists; completed checkpoint evaluation is not yet available.")
    return {
        "train_count": count_examples(ROOT / "data" / "train.jsonl"),
        "eval_count": count_examples(ROOT / "data" / "eval.jsonl"),
        "river": river,
        "gbrain": {"status": "not_connected", "message": "No GBrain integration. This MVP uses the local JSON policy."},
    }


def run_model(engine: str, input_dict: dict[str, Any]) -> dict[str, Any]:
    checkpoint, checkpoint_error = checkpoint_state()
    if not checkpoint:
        raise HTTPException(status_code=503, detail={
            "code": "model_unavailable", "engine": "river", "message": checkpoint_error,
            "fallback_used": False,
        })
    try:
        # The shared loader only reads explicit River keys and never logs values.
        common = importlib.import_module("training.common")
        common.load_env()
        module = importlib.import_module("training.river_inference")
        return module.predict(input_dict)
    except (ImportError, FileNotFoundError, RuntimeError, OSError):
        raise HTTPException(status_code=503, detail={
            "code": "model_unavailable", "engine": "river",
            "message": "River inference is unavailable. Check server-side credentials, dependencies, and saved-checkpoint access. No recommendation was substituted.",
            "fallback_used": False,
        }) from None
    except ValueError:
        raise HTTPException(status_code=502, detail={
            "code": "invalid_model_output", "engine": "river",
            "message": "River returned an invalid structured response or checkpoint configuration. No recommendation was substituted.",
            "fallback_used": False,
        }) from None
    except Exception:
        raise HTTPException(status_code=502, detail={
            "code": "model_inference_failed", "engine": "river",
            "message": "The River inference request failed. Check server-side model access and network connectivity. No recommendation was substituted.",
            "fallback_used": False,
        }) from None


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    company_data = load_company()
    policy = company_data["policy"]
    scenario = request.model_dump(exclude={"engine"})
    input_dict = {"policy": policy, "workflow": company_data["workflow"], "scenario": scenario}
    model_metadata: dict[str, Any]
    if request.engine == "rules":
        prediction = decide(input_dict)
        model_metadata = {
            "status": "not_used",
            "message": "Deterministic policy rules; no model inference. Written clauses and structured rules were authored together by humans, not extracted by NLP.",
        }
    else:
        inference_started = time.perf_counter()
        raw_prediction = run_model(request.engine, input_dict)
        inference_ms = round((time.perf_counter() - inference_started) * 1000)
        try:
            prediction = validate_prediction(raw_prediction, input_dict)
        except ValueError as exc:
            raise HTTPException(status_code=502, detail={
                "code": "unsafe_model_proposal", "engine": request.engine,
                "message": f"Policy guardrails rejected the model proposal: {exc} Current workflow remains unchanged.",
                "fallback_used": False,
            }) from exc
        checkpoint = (read_artifact("river_checkpoint.json") or {}).get("path")
        model_metadata = {
            "status": "policy_validated",
            "message": "Actual saved-checkpoint inference. The proposal passed deterministic policy checks for required controls, manual review, and cited clauses.",
            "checkpoint": checkpoint,
            "inference_ms": inference_ms,
            "cache_hit": False,
        }
    current_steps = company_data["workflow"]["steps"]
    required = set(prediction["required_approvals"])
    proposed_steps = [step for step in current_steps if step["type"] != "approval" or step["role"] in required]
    removed_steps = []
    for step in current_steps:
        if step["type"] != "approval" or step["role"] in required:
            continue
        threshold = next(t for t in policy["rules"]["amount_thresholds"] if t["additional_approval"] == step["role"])
        removed_steps.append({
            **step,
            "reason": f"{step['label']} is required only above ${threshold['above']:,.0f}. This ordinary ${scenario['amount']:,.2f} reimbursement does not meet that threshold.",
            "clause_ids": [threshold["clause_id"]],
        })
    current_days = sum(step["days"] for step in current_steps)
    proposed_days = sum(step["days"] for step in proposed_steps)
    saved_days = current_days - proposed_days
    review_required = prediction["review_required"]
    findings = []
    if review_required:
        reasons = []
        if scenario["exception"]:
            reasons.append("the expense is marked as an exception")
        if not scenario["receipt_present"]:
            reasons.append("the receipt is missing")
        findings.append({
            "title": "Manual review required",
            "description": f"Because {' and '.join(reasons)}, retain every current approval until an authorized reviewer resolves the issue. No time savings are claimed.",
            "clause_ids": ["P1", "P5"],
        })
    else:
        findings.extend({
            "title": f"Remove {step['label'].lower()}",
            "description": step["reason"], "clause_ids": step["clause_ids"],
        } for step in removed_steps)
        findings.append({
            "title": "Required controls preserved",
            "description": "The proposal keeps every approval required for this amount and retains expense submission and payment processing.",
            "clause_ids": prediction["clause_ids"],
        })
    return {
        "company": company_data["name"],
        "workflow_name": company_data["workflow"]["name"],
        "engine": request.engine,
        "engine_label": {"rules": "Policy-rule diagnostic (no model)", "river": "River fine-tuned model"}[request.engine],
        "scenario": scenario,
        "policy_version": policy["version"],
        "current_steps": current_steps,
        "proposed_steps": proposed_steps,
        "removed_steps": removed_steps,
        "required_approvals": prediction["required_approvals"],
        "findings": findings,
        "metrics": {
            "current_days": current_days, "proposed_days": proposed_days,
            "saved_days": saved_days, "savings_percent": round(100 * saved_days / current_days, 1),
            "current_approvals": sum(s["type"] == "approval" for s in current_steps),
            "proposed_approvals": len(required),
        },
        "compliance": {
            "status": "review_required" if review_required else "compliant",
            "message": "Manual review required; all existing controls retained." if review_required else "Compliant with the human-authored structured rules for Atlas policy v1.0.",
            "clause_ids": prediction["clause_ids"],
        },
        "assumptions": [
            "Atlas Technologies, its policy, expenses, and step durations are fictional synthetic demo data.",
            "Durations are sequential elapsed business days. Savings are projections, not measured operational results.",
            "Written clauses and structured rules are maintained together by humans; automatic policy extraction is not implemented.",
            "Recommendations cover the supplied local policy only and do not execute changes in an external workflow system.",
        ],
        "model": model_metadata,
    }
