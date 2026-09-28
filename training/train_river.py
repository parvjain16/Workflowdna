"""River supervised fine-tuning using the official session/LoRA API.

Sources (checked 2026-09-27): https://docs.river.ai/guides/sft/
and https://docs.river.ai/python-api/ (river-client 0.11.0).
Run: python -m training.train_river --epochs 3 --batch-size 4
Requires RIVER_API_KEY and access to RIVER_MODEL; execution incurs River usage.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import random
import sys

from .common import ROOT, evaluate_predictions, fingerprint, load_env, load_examples, now, render_model_prompt, verify_splits, write_json

DEFAULT_MODEL = "Qwen/Qwen3.6-35B-A3B-FP8"


def make_datum(example: dict, tokenizer) -> dict:
    """Next-token targets; supervise completion and EOS, never prompt/padding.

    The last prompt token predicts the first completion token, so its weight is
    one. The terminal dummy next-token target is masked instead of training a
    redundant EOS-to-EOS transition. Arrays retain the River datum dimensions.
    """
    eos = tokenizer.eos_token_id
    if eos is None:
        raise ValueError("The tokenizer must have an EOS token.")
    prompt = tokenizer(render_model_prompt(example["input"], tokenizer), add_special_tokens=False)["input_ids"]
    completion_text = " " + json.dumps(example["output"], separators=(",", ":"))
    completion = tokenizer(completion_text, add_special_tokens=False)["input_ids"] + [eos]
    if not prompt or len(completion) < 2:
        raise ValueError("Training example must include prompt and completion tokens.")
    ids = prompt + completion
    return {"input_ids": ids, "target_tokens": ids[1:] + [eos],
            "weights": [0.0] * (len(prompt) - 1) + [1.0] * len(completion) + [0.0]}


def sample_outputs(sample_function, examples: list[dict], tokenizer, **kwargs) -> list[str]:
    outputs = sample_function([render_model_prompt(x["input"], tokenizer) for x in examples], max_tokens=384,
                              temperature=0.0, seed=42, **kwargs)
    if len(outputs) != len(examples) or any(len(samples) != 1 for samples in outputs):
        raise ValueError("River sampling returned an unexpected number of results.")
    return [samples[0].text for samples in outputs]


def run(args: argparse.Namespace) -> int:
    load_env()
    output_dir = Path(args.output_dir)
    status_path = output_dir / "river_status.json"
    model_name = os.environ.get("RIVER_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    metadata = {"base_model": model_name, "sdk": "river-client==0.11.0", "train_count": 20, "eval_count": 5,
                "docs": ["https://docs.river.ai/guides/sft/", "https://docs.river.ai/python-api/"], "updated_at": now()}
    training = load_examples(ROOT / "data/train.jsonl")
    evaluation = load_examples(ROOT / "data/eval.jsonl")
    verify_splits(training, evaluation)
    key = os.environ.get("RIVER_API_KEY", "").strip()
    if not key or key.lower() in {"your_api_key", "your_river_api_key", "replace_me", "rv_..."}:
        message = "River training has not run: set RIVER_API_KEY in .env and confirm model access. No River checkpoint or metrics were fabricated."
        write_json(status_path, {**metadata, "status": "not_configured", "message": message})
        print(message, file=sys.stderr)
        return 2
    if args.check_only:
        print("Dataset split is valid and a River key is configured; authentication and model access have not been tested.")
        return 0
    if args.epochs < 1 or not 1 <= args.batch_size <= 20 or not 1 <= args.rank <= 32 or args.learning_rate <= 0:
        raise ValueError("Use positive epochs/lr, batch size 1–20, and LoRA rank 1–32.")
    write_json(status_path, {**metadata, "status": "running", "message": "Loading tokenizer and creating a real River training session."})
    client = None
    try:
        import river_client as river
        # River serving aliases (such as -FP8) can differ from HF tokenizer IDs.
        tokenizer = river.load_tokenizer(base_model=model_name)
        print("Tokenizer loaded; opening authenticated River session.", flush=True)
        batches = [make_datum(example, tokenizer) for example in training]
        client = river.Client(api_key=key, timeout=args.timeout)
        report = {"base_model": model_name, "train_count": 20, "eval_count": 5,
                  "training_sha256": fingerprint(training), "evaluation_sha256": fingerprint(evaluation),
                  "generation": {"temperature": 0.0, "seed": 42, "max_tokens": 384, "prompt_protocol": "chat_no_thinking_v1", "enable_thinking": False},
                  "hyperparameters": {"epochs": args.epochs, "batch_size": args.batch_size, "rank": args.rank,
                                      "learning_rate": args.learning_rate, "shuffle_seed": 42},
                  "loss_history": [], "started_at": now()}
        with client.session(project="workflowdna-sft", timeout=args.timeout) as session:
            model = session.create_model(base_model=model_name, lora=river.LoraConfig(rank=args.rank, seed=42),
                                         tokenizer=tokenizer, timeout=args.timeout)
            report["model_id"] = model.model_id
            print("River model created; evaluating original weights on held-out prompts.", flush=True)
            # Evaluation data is sampled only. It never enters forward_backward.
            report["before"] = evaluate_predictions(evaluation, sample_outputs(model.sample, evaluation, tokenizer, timeout=args.timeout))
            write_json(output_dir / "river_evaluation.json", report)
            print(json.dumps({"stage": "baseline_evaluated", "metrics": report["before"]["metrics"]}), flush=True)
            rng = random.Random(42)
            for epoch in range(args.epochs):
                order = list(range(len(batches)))
                rng.shuffle(order)
                for offset in range(0, len(order), args.batch_size):
                    batch = [batches[index] for index in order[offset:offset + args.batch_size]]
                    forward = model.forward_backward(batch, loss_fn="cross_entropy", timeout=args.timeout)
                    model.optim_step(lr=args.learning_rate, grad_clip_norm=1.0, timeout=args.timeout)
                    entry = {"epoch": epoch + 1, "step": model.step, "loss": float(forward.metrics["loss"])}
                    report["loss_history"].append(entry)
                    write_json(output_dir / "river_evaluation.json", report)
                    write_json(status_path, {**metadata, "updated_at": now(), "status": "running", "completed_steps": model.step,
                                            "total_steps": args.epochs * ((len(batches) + args.batch_size - 1) // args.batch_size),
                                            "message": f"River SFT update {model.step} completed; final checkpoint and evaluation are pending."})
                    print(json.dumps(entry), flush=True)
            name = "workflowdna-" + now().replace(":", "-").replace("+", "-").replace(".", "-")
            checkpoint = model.save_weights(name, mode="inference", timeout=args.timeout)
            if not isinstance(checkpoint.path, str) or not checkpoint.path.startswith("river://"):
                raise ValueError("River did not return a valid checkpoint path.")
            # Persist only the path actually returned by River. Never a placeholder.
            manifest = {"status": "trained", "path": checkpoint.path, "mode": "inference", "base_model": model_name,
                        "saved_at": now(), "train_count": 20, "training_sha256": fingerprint(training),
                        "training_ids": [x["id"] for x in training], "policy_fingerprints": sorted({fingerprint(x["input"]["policy"]) for x in training}),
                        "model_id": model.model_id, "step": model.step, "prompt_protocol": "chat_no_thinking_v1"}
            write_json(output_dir / "river_checkpoint.json", manifest)
            print("Inference checkpoint saved; evaluating trained weights and checkpoint.", flush=True)
            report["after_live"] = evaluate_predictions(evaluation, sample_outputs(model.sample, evaluation, tokenizer, timeout=args.timeout))
            report["after_checkpoint"] = evaluate_predictions(evaluation, sample_outputs(
                session.sample, evaluation, tokenizer, base_model=model_name, checkpoint=checkpoint, timeout=args.timeout))
            report.update(status="evaluated", checkpoint=checkpoint.path, completed_at=now())
            write_json(output_dir / "river_evaluation.json", report)
            write_json(status_path, {**metadata, "updated_at": now(), "status": "trained", "checkpoint": checkpoint.path,
                                    "metrics": report["after_checkpoint"]["metrics"],
                                    "message": "River SFT completed; inference checkpoint saved and sampled on five held-out examples. Inspect the evaluation report for failures."})
            print(json.dumps({"checkpoint": checkpoint.path, "held_out_metrics": report["after_checkpoint"]["metrics"]}, indent=2))
        return 0
    except Exception as exc:
        # API exceptions can include request metadata: do not write raw errors or secrets.
        message = f"River run did not complete ({type(exc).__name__}). Check credentials, model access, network, and dependency compatibility. Partial artifacts, if any, contain only completed operations."
        write_json(status_path, {**metadata, "updated_at": now(), "status": "failed", "error_type": type(exc).__name__, "message": message})
        print(message, file=sys.stderr)
        return 1
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--rank", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts")
    parser.add_argument("--check-only", action="store_true", help="Validate data/config presence; does not call River.")
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
