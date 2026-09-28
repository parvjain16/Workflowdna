"""Reproduce the fixed 20/5 synthetic split from the fictional local policy.

These are reimbursement workflow instances, not 25 different policy documents.
Labels are generated from human-authored structured rules and checked by tests.
Changing the policy requires review, dataset regeneration, and retraining.
"""
from __future__ import annotations

import copy
import json

from .common import ROOT, ROLES, verify_splits

# (amount USD, exception, receipt present). Held-out inputs are never fit.
TRAIN_SCENARIOS = [
    (25, False, True), (125, False, True), (400, False, True), (999.99, False, True),
    (1000, False, True), (1000.01, False, True), (1500, False, True), (3200, False, True),
    (4999.99, False, True), (5000, False, True), (5000.01, False, True), (6200, False, True),
    (9000, False, True), (8200, False, False), (50, True, True), (2100, True, True),
    (12000, True, True), (80, False, False), (4100, False, False), (10500, True, False),
]
EVAL_SCENARIOS = [(750, False, True), (2600, False, True), (7600, False, True),
                  (860, True, True), (120, False, False)]


def make_examples(company: dict, scenarios: list, split: str) -> list[dict]:
    examples = []
    rules = company["policy"]["rules"]
    for index, (amount, exception, receipt_present) in enumerate(scenarios, 1):
        review = exception or not receipt_present
        required = set(ROLES) if review else set(rules["base_required_approvals"])
        if not review:
            required.update(tier["additional_approval"] for tier in rules["amount_thresholds"] if amount > tier["above"])
        examples.append({"id": f"atlas-{split}-{index:02d}", "input": {
            "policy": copy.deepcopy(company["policy"]), "workflow": copy.deepcopy(company["workflow"]),
            "scenario": {"amount": amount, "exception": exception, "receipt_present": receipt_present}},
            "output": {"required_approvals": [role for role in ROLES if role in required],
                       "removed_approvals": [role for role in ROLES if role not in required],
                       "review_required": review, "clause_ids": ["P1", "P5"] if review else ["P1", "P2", "P3", "P4"]}})
    return examples


def main() -> None:
    company = json.loads((ROOT / "data/company_policy.json").read_text())
    train = make_examples(company, TRAIN_SCENARIOS, "train")
    evaluation = make_examples(company, EVAL_SCENARIOS, "eval")
    verify_splits(train, evaluation)
    for name, examples in (("train", train), ("eval", evaluation)):
        (ROOT / f"data/{name}.jsonl").write_text("".join(json.dumps(example, separators=(",", ":")) + "\n" for example in examples))
    print("Prepared exactly 20 training examples and 5 distinct held-out evaluation examples.")


if __name__ == "__main__":
    main()
