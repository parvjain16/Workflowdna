"""Behavioral coverage for policy boundaries, controls, and honest engine errors."""
import pytest
from fastapi.testclient import TestClient

import backend.app as api
from backend.policy import decide, load_company, validate_prediction

client = TestClient(api.app)


def test_health_and_company():
    assert client.get("/api/health").json() == {"status": "ok"}
    company = client.get("/api/company").json()
    assert company["name"] == "Atlas Technologies"
    assert sum(s["days"] for s in company["workflow"]["steps"]) == 12
    assert "manually authored" in company["policy"]["source"]


@pytest.mark.parametrize("amount,days,approvals", [
    (0.01, 6, 2), (750, 6, 2), (1000, 6, 2), (1000.01, 9, 3),
    (5000, 9, 3), (5000.01, 12, 4), (1_000_000, 12, 4),
])
def test_amount_boundaries(amount, days, approvals):
    response = client.post("/api/analyze", json={"amount": amount, "engine": "rules"})
    assert response.status_code == 200
    result = response.json()
    assert result["metrics"]["proposed_days"] == days
    assert result["metrics"]["proposed_approvals"] == approvals
    assert result["metrics"]["saved_days"] == 12 - days
    assert result["compliance"]["status"] == "compliant"
    assert {s["role"] for s in result["proposed_steps"]} >= {"employee", "manager", "finance", "payroll"}
    assert result["model"]["status"] == "not_used"


def test_default_savings_and_policy_citations():
    result = client.post("/api/analyze", json={"engine": "rules"}).json()
    assert result["metrics"]["savings_percent"] == 50.0
    assert [s["role"] for s in result["proposed_steps"]] == ["employee", "manager", "finance", "payroll"]
    assert [s["clause_ids"] for s in result["removed_steps"]] == [["P3"], ["P4"]]


@pytest.mark.parametrize("scenario", [
    {"exception": True}, {"receipt_present": False}, {"exception": True, "receipt_present": False},
])
def test_exceptions_never_remove_controls_or_claim_savings(scenario):
    result = client.post("/api/analyze", json={"amount": 10, "engine": "rules", **scenario}).json()
    assert result["compliance"]["status"] == "review_required"
    assert result["current_steps"] == result["proposed_steps"]
    assert result["removed_steps"] == []
    assert result["metrics"]["saved_days"] == 0
    assert result["metrics"]["savings_percent"] == 0
    assert "P5" in result["compliance"]["clause_ids"]


@pytest.mark.parametrize("bad_request", [
    {"amount": 0}, {"amount": -1}, {"amount": True}, {"amount": "750"},
    {"amount": 1_000_000_001}, {"exception": "false"}, {"receipt_present": 1},
    {"engine": "mystery"}, {"currency": "EUR"},
])
def test_invalid_input_rejected(bad_request):
    assert client.post("/api/analyze", json=bad_request).status_code == 422


def fixture_input(amount=750, **scenario):
    company = load_company()
    return {"policy": company["policy"], "workflow": company["workflow"],
            "scenario": {"amount": amount, "exception": False, "receipt_present": True, **scenario}}


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(required_approvals=["manager"]),
    lambda p: p.update(required_approvals=["manager", "finance", "unknown"]),
    lambda p: p.update(removed_approvals=["cfo"]),
    lambda p: p.update(review_required="false"),
    lambda p: p.update(clause_ids=["P999"]),
    lambda p: p.update(clause_ids=["P1", "P2"]),
    lambda p: p.update(clause_ids=["P1", "P2", "P3", "P4", "P4"]),
])
def test_guardrails_reject_bad_model_proposals(monkeypatch, mutation):
    prediction = decide(fixture_input())
    mutation(prediction)
    monkeypatch.setattr(api, "run_model", lambda *_: prediction)
    response = client.post("/api/analyze", json={"engine": "river"})
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "unsafe_model_proposal"
    assert response.json()["detail"]["fallback_used"] is False
    assert "metrics" not in response.json()


def test_model_cannot_bypass_manual_review(monkeypatch):
    monkeypatch.setattr(api, "run_model", lambda *_: decide(fixture_input()))
    response = client.post("/api/analyze", json={"engine": "river", "receipt_present": False})
    assert response.status_code == 502


def test_model_cannot_bypass_high_amount_threshold():
    with pytest.raises(ValueError, match="required_approvals"):
        validate_prediction(decide(fixture_input()), fixture_input(10_000))


def test_valid_model_proposal_preserves_order_and_engine_label(monkeypatch):
    prediction = decide(fixture_input())
    prediction["required_approvals"].reverse()
    monkeypatch.setattr(api, "run_model", lambda *_: prediction)
    result = client.post("/api/analyze", json={"engine": "river"}).json()
    assert result["required_approvals"] == ["manager", "finance"]
    assert result["engine_label"] == "River fine-tuned model"
    assert result["model"]["status"] == "policy_validated"


@pytest.mark.parametrize("engine", ["river"])
def test_missing_model_is_explicit_without_fallback(monkeypatch, engine):
    def unavailable(_name):
        raise ImportError("Model checkpoint is not configured")
    monkeypatch.setattr(api.importlib, "import_module", unavailable)
    response = client.post("/api/analyze", json={"engine": engine})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "model_unavailable"
    assert response.json()["detail"]["fallback_used"] is False




@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_amount_returns_validation_error(literal):
    result = client.post("/api/analyze", content='{"amount":' + literal + '}',
                         headers={"Content-Type": "application/json"})
    assert result.status_code == 422
    assert result.json()["detail"]


def test_local_engine_is_removed():
    assert client.post("/api/analyze", json={"engine": "local"}).status_code == 422


def test_default_is_river_and_never_silently_returns_rules(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "ARTIFACTS", tmp_path)
    response = client.post("/api/analyze", json={})
    assert response.status_code == 503
    assert response.json()["detail"]["engine"] == "river"
    assert response.json()["detail"]["fallback_used"] is False


def valid_manifest():
    import hashlib
    import json
    fingerprint = hashlib.sha256(json.dumps(load_company()["policy"], sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return {"status": "trained", "mode": "inference", "path": "river://test/checkpoint",
            "base_model": "test-model", "policy_fingerprints": [fingerprint]}


def write_artifact(tmp_path, name, value):
    import json
    (tmp_path / name).write_text(json.dumps(value))


def test_metadata_loads_without_any_model(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "ARTIFACTS", tmp_path)
    assert client.get("/api/company").status_code == 200
    for endpoint in ["/api/status", "/api/training"]:
        result = client.get(endpoint).json()
        assert "local" not in result
        assert result["river"]["ready"] is False
        assert result["river"]["metrics"] is None
        assert result["river"]["checkpoint"] is None
        assert result["gbrain"]["status"] == "not_connected"
    evaluation = client.get("/api/evaluation").json()
    assert evaluation["status"] == "not_evaluated"
    assert evaluation["before"] is None
    assert evaluation["after_checkpoint"] is None


@pytest.mark.parametrize("change", [
    {"path": "fake-checkpoint"}, {"mode": "training"}, {"base_model": ""},
    {"policy_fingerprints": ["old-policy"]}, {"policy_fingerprints": None},
])
def test_invalid_or_stale_checkpoint_cannot_be_ready(tmp_path, monkeypatch, change):
    monkeypatch.setattr(api, "ARTIFACTS", tmp_path)
    write_artifact(tmp_path, "river_checkpoint.json", {**valid_manifest(), **change})
    write_artifact(tmp_path, "river_status.json", {"status": "trained"})
    result = client.get("/api/training").json()
    assert result["river"]["status"] == "invalid_checkpoint"
    assert result["river"]["ready"] is False
    assert client.post("/api/analyze", json={}).status_code == 503


def test_checkpoint_without_evaluation_is_not_ready(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "ARTIFACTS", tmp_path)
    write_artifact(tmp_path, "river_checkpoint.json", valid_manifest())
    write_artifact(tmp_path, "river_status.json", {"status": "trained"})
    result = client.get("/api/training").json()
    assert result["river"]["status"] == "evaluation_pending"
    assert result["river"]["ready"] is False
    assert result["river"]["metrics"] is None


def test_evaluation_exposes_actual_rows_and_does_not_use_live_outputs(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(api, "ARTIFACTS", tmp_path)
    example = json.loads((api.ROOT / "data" / "eval.jsonl").read_text().splitlines()[0])
    section = {"metrics": {"exact_match_accuracy": 0.2}, "results": [{"id": example["id"], "expected": example["output"], "raw_prediction": "actual raw baseline", "valid": False}]}
    write_artifact(tmp_path, "river_evaluation.json", {"before": section, "after_live": section})
    result = client.get("/api/evaluation").json()
    assert result["status"] == "partial"
    assert result["before"]["results"][0]["raw_prediction"] == "actual raw baseline"
    assert result["before"]["results"][0]["scenario"] == example["input"]["scenario"]
    assert result["after_checkpoint"] is None
    assert result["checkpoint_verified"] is False


def test_evaluation_metrics_only_attached_to_matching_checkpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "ARTIFACTS", tmp_path)
    manifest = valid_manifest()
    import json
    examples = [json.loads(line) for line in (api.ROOT / "data" / "eval.jsonl").read_text().splitlines() if line.strip()]
    section = {"metrics": {"exact_match_accuracy": 0.4},
               "results": [{"id": example["id"], "raw_prediction": "actual sampled output"} for example in examples]}
    write_artifact(tmp_path, "river_checkpoint.json", manifest)
    write_artifact(tmp_path, "river_status.json", {"status": "trained"})
    report = {"status": "evaluated", "before": section, "after_checkpoint": section, "checkpoint": "river://different/checkpoint"}
    write_artifact(tmp_path, "river_evaluation.json", report)
    assert client.get("/api/training").json()["river"]["ready"] is False
    report["checkpoint"] = manifest["path"]
    write_artifact(tmp_path, "river_evaluation.json", report)
    assert client.get("/api/training").json()["river"]["metrics"] == section["metrics"]
    write_artifact(tmp_path, "river_status.json", {"status": "failed"})
    assert client.get("/api/training").json()["river"]["ready"] is False


@pytest.mark.parametrize("exception_class,expected_status", [(RuntimeError, 503), (ValueError, 502), (Exception, 502)])
def test_raw_inference_exception_never_exposes_credentials(monkeypatch, exception_class, expected_status):
    monkeypatch.setattr(api, "checkpoint_state", lambda: (valid_manifest(), None))
    def unavailable(_name):
        raise exception_class("credential-secret-example must not be echoed")
    monkeypatch.setattr(api.importlib, "import_module", unavailable)
    result = client.post("/api/analyze", json={"engine": "river"})
    assert result.status_code == expected_status
    assert "credential-secret-example" not in result.text
    assert result.json()["detail"]["fallback_used"] is False


def test_empty_evaluation_rows_never_claim_completed_model(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "ARTIFACTS", tmp_path)
    manifest = valid_manifest()
    write_artifact(tmp_path, "river_checkpoint.json", manifest)
    write_artifact(tmp_path, "river_status.json", {"status": "trained"})
    section = {"metrics": {"exact_match_accuracy": 1}, "results": []}
    write_artifact(tmp_path, "river_evaluation.json", {"status": "evaluated", "before": section, "after_checkpoint": section, "checkpoint": manifest["path"]})
    assert client.get("/api/training").json()["river"]["ready"] is False
    assert client.get("/api/evaluation").json()["checkpoint_verified"] is False
