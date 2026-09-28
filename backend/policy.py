"""Human-authored policy controls; this module is not an NLP policy extractor."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY_FILE = ROOT / "data" / "company_policy.json"


def load_company() -> dict[str, Any]:
    with POLICY_FILE.open() as handle:
        return json.load(handle)


def decide(input_dict: dict[str, Any]) -> dict[str, Any]:
    policy, workflow, scenario = (
        input_dict["policy"], input_dict["workflow"], input_dict["scenario"]
    )
    rules = policy["rules"]
    approval_order = [step["role"] for step in workflow["steps"] if step["type"] == "approval"]
    review_required = scenario["exception"] or not scenario["receipt_present"]
    if review_required:
        return {
            "required_approvals": approval_order,
            "removed_approvals": [],
            "review_required": True,
            "clause_ids": ["P1", rules["manual_review_clause_id"]],
        }
    required = set(rules["base_required_approvals"])
    for threshold in rules["amount_thresholds"]:
        if scenario["amount"] > threshold["above"]:
            required.add(threshold["additional_approval"])
    return {
        "required_approvals": [role for role in approval_order if role in required],
        "removed_approvals": [role for role in approval_order if role not in required],
        "review_required": False,
        "clause_ids": rules["base_clause_ids"] + [t["clause_id"] for t in rules["amount_thresholds"]],
    }


def validate_prediction(prediction: Any, input_dict: dict[str, Any]) -> dict[str, Any]:
    """Reject model output unless roles, controls and citations match current policy.

    Validation does not repair a rejected prediction or silently substitute rule output.
    Ordering is normalized to the current sequential workflow only after validation.
    """
    if not isinstance(prediction, dict):
        raise ValueError("The model must return a structured JSON object.")
    expected = decide(input_dict)
    for field in ("required_approvals", "removed_approvals", "clause_ids"):
        values = prediction.get(field)
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
            raise ValueError(f"The model returned an invalid {field} list.")
        if len(values) != len(set(values)):
            raise ValueError(f"The model returned duplicate values in {field}.")
    if type(prediction.get("review_required")) is not bool:
        raise ValueError("The model must return a boolean review_required field.")
    if prediction["review_required"] != expected["review_required"]:
        raise ValueError("The model did not preserve the policy's manual review requirement.")
    for field in ("required_approvals", "removed_approvals"):
        if set(prediction[field]) != set(expected[field]):
            raise ValueError(f"The model's {field} do not match the current written policy controls.")
    known_clauses = {clause["id"] for clause in input_dict["policy"]["clauses"]}
    cited = set(prediction["clause_ids"])
    if not cited or not cited <= known_clauses:
        raise ValueError("The model cited missing or unknown policy clauses.")
    # Every retained or removed control must be grounded in the relevant clause.
    if not set(expected["clause_ids"]) <= cited:
        raise ValueError("The model omitted policy citations required to justify its recommendation.")
    return {**expected, "clause_ids": prediction["clause_ids"]}
