# River AI training and evaluation

WorkflowDNA uses River AI for model training and inference. The 20 training
examples and five separate held-out evaluation examples are fictional Atlas
reimbursement workflow instances governed by one policy. They cover approval
thresholds, exceptions, missing receipts, and exact boundary values. IDs and
complete inputs are checked for overlap. Held-out examples never enter the
supervised training batches.

The policy includes written clauses and human-maintained structured rules.
Synthetic training labels were generated from those rules. The application
independently checks generated recommendations against policy before showing any
savings. This tiny same-policy evaluation is a demonstration, not evidence of
reliability across companies or policy documents.

## Setup and reproduction

This implementation follows River's official [SFT guide](https://docs.river.ai/guides/sft/)
and [Python API reference](https://docs.river.ai/python-api/), checked September 27,
2026 for `river-client==0.11.0`. The SDK's `load_tokenizer(base_model=...)` resolves
River serving aliases to their canonical tokenizer. Set `RIVER_API_KEY` in the
ignored project `.env`; no key is written to output artifacts. `RIVER_MODEL`
defaults to `Qwen/Qwen3.6-35B-A3B-FP8` and can be changed to an authorized model.

From the project root with the Python environment active:

```sh
python -m pip install -r training/requirements.txt
python -m training.prepare_data
python -m training.train_river --check-only
python -m training.train_river --epochs 3 --batch-size 4 --rank 16 --timeout 600
python -m unittest discover -s tests -p test_training.py
```

The real River run creates a LoRA model, evaluates its starting weights, performs
15 updates over the 20 training rows, saves an actual inference checkpoint,
evaluates the trained live weights, and evaluates by loading the saved checkpoint.
It saves before evaluation so a later sampling failure does not lose trained
weights. All evaluations use the same five unseen prompts and generation settings:
greedy generation, seed 42, maximum 384 output tokens.

Training and inference both use Qwen's tokenizer chat template with
`enable_thinking=False`. This avoids spending the output budget on reasoning and
makes the original-versus-trained comparison use exactly the same protocol.
Next-token targets supervise only completion tokens and EOS: the last prompt token
predicts the first completion token; all earlier prompt positions and the final
dummy target have zero weight. The mask and saved-checkpoint reuse are tested.

## Artifacts and interpretation

`artifacts/river_evaluation.json` contains actual baseline outputs (`before`),
training losses, trained live outputs (`after_live`), and saved-checkpoint outputs
(`after_checkpoint`). Only `after_checkpoint` is the final saved-model comparison.
Every row includes its expected target, raw response, parsed output when valid,
and validation outcomes. Dataset fingerprints and run settings are recorded.

`artifacts/river_checkpoint.json` is created only after
`save_weights(..., mode="inference")` returns a `river://` path. The LoRA adapter
is stored on River; the local manifest references that actual artifact. Application
inference loads this exact path through `session.sample`. No dedicated production
deployment or GBrain integration is created.

Metrics distinguish several questions:

- Exact match requires the full structured target, including citation order.
- Approval accuracy measures the required approval list when the response is valid.
- `valid_json_rate` means a valid structured response under the complete output
  schema; it is stricter than merely syntactically valid JSON.
- Control preservation (`safe_recommendation_rate`) checks that no required
  control was removed, manual review was respected, and citations exist.
- Policy guardrail acceptance additionally requires the correct approval lists,
  review decision, and all required citations. This is the functional application
  gate, exposed as `policy_guardrail_pass_rate`.

`artifacts/river_status.json` tracks actual execution. Without a key, training exits
2 with `not_configured` and creates no River checkpoint or metrics. Dependencies,
network, authentication, quota, or model-access failures exit 1 with a sanitized
error type. `--check-only` validates dataset/config presence, not remote access.
The script never substitutes a local classifier or fabricated model result.

Two initial raw-completion attempts were superseded by the identical no-thinking
chat protocol. Their original outputs and any completed updates are preserved in
`river_initial_attempt.json` and `river_raw_completion_attempt.json` for audit,
and are excluded from the final before/after comparison. The switch addressed
response serialization and output-budget consumption; evaluation labels were
never used for training or model selection.

Offline tests mock the River transport only inside temporary directories. Those
fixtures are not application artifacts and are never reported as model results.
The saved real run reports provide the evidence of actual API training/inference.
