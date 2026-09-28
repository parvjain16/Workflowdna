"""Use only an actual River inference checkpoint saved by train_river."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .common import ROOT, fingerprint, load_env, parse_prediction, render_model_prompt


def predict(input_dict: dict, checkpoint_path: Path | str = ROOT / "artifacts/river_checkpoint.json") -> dict:
    load_env()
    key = os.environ.get("RIVER_API_KEY", "").strip()
    if not key or not Path(checkpoint_path).is_file():
        raise RuntimeError("River inference requires RIVER_API_KEY and a saved inference checkpoint.")
    checkpoint = json.loads(Path(checkpoint_path).read_text())
    path = checkpoint.get("path", "")
    if not isinstance(path, str) or not path.startswith("river://") or checkpoint.get("mode") != "inference":
        raise ValueError("Invalid River inference checkpoint manifest.")
    if fingerprint(input_dict["policy"]) not in checkpoint.get("policy_fingerprints", []):
        raise ValueError("Policy changed: train and evaluate a new River checkpoint.")
    try:
        import river_client as river
    except ImportError as exc:
        raise RuntimeError("Install training/requirements.txt to enable River inference.") from exc
    client = river.Client(api_key=key, timeout=120)
    try:
        tokenizer = river.load_tokenizer(base_model=checkpoint["base_model"])
        with client.session(project="workflowdna-inference", timeout=120) as session:
            outputs = session.sample(render_model_prompt(input_dict, tokenizer), base_model=checkpoint["base_model"], checkpoint=path,
                                     tokenizer=tokenizer,
                                     temperature=0.0, seed=42, max_tokens=384, timeout=120)
            if len(outputs) != 1 or len(outputs[0]) != 1:
                raise ValueError("River returned an unexpected response count.")
            return parse_prediction(outputs[0][0].text)
    finally:
        client.close()
