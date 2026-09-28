import argparse
import contextlib
import copy
import io
import json
from pathlib import Path
import types
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

from training.common import ROOT, evaluate_predictions, load_examples, parse_prediction, render_model_prompt, verify_splits
from training.train_river import make_datum, run as run_river


class CharacterTokenizer:
    """Transparent tokenizer for inspecting every supervised target in unit tests."""
    eos_token_id = 0

    def __call__(self, text, add_special_tokens=False):
        return {"input_ids": [ord(char) for char in text]}

    def apply_chat_template(self, messages, tokenize, add_generation_prompt, enable_thinking):
        assert tokenize is False and add_generation_prompt is True and enable_thinking is False
        return '<user>' + messages[0]['content'] + '</user><assistant>'


class TrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.training = load_examples(ROOT / 'data/train.jsonl')
        cls.evaluation = load_examples(ROOT / 'data/eval.jsonl')

    def test_exact_split_and_input_isolation(self):
        verify_splits(self.training, self.evaluation)
        contaminated = copy.deepcopy(self.evaluation)
        contaminated[0]['input'] = copy.deepcopy(self.training[0]['input'])
        with self.assertRaisesRegex(ValueError, 'overlap'):
            verify_splits(self.training, contaminated)

    def test_prompt_mask_includes_first_completion_and_eos(self):
        example = self.training[0]
        tokenizer = CharacterTokenizer()
        datum = make_datum(example, tokenizer)
        prompt_length = len(render_model_prompt(example['input'], tokenizer))
        expected = [ord(char) for char in ' ' + json.dumps(example['output'], separators=(',', ':'))] + [0]
        self.assertEqual(len(datum['input_ids']), len(datum['target_tokens']))
        self.assertEqual(len(datum['input_ids']), len(datum['weights']))
        self.assertTrue(all(weight == 0 for weight in datum['weights'][:prompt_length - 1]))
        self.assertEqual([token for token, weight in zip(datum['target_tokens'], datum['weights']) if weight], expected)
        self.assertEqual(datum['weights'][-1], 0)

    def test_parser_rejects_malformed_and_unsafe_shapes(self):
        valid = self.training[0]['output']
        malformed = ['```json\n{}\n```', '{', json.dumps({**valid, 'review_required': 'false'}),
                     json.dumps({**valid, 'required_approvals': ['manager', 'finance', 'unknown']}),
                     json.dumps({**valid, 'review_required': True}), json.dumps({**valid, 'extra': 'invented'})]
        for response in malformed:
            with self.subTest(response=response):
                with self.assertRaises(ValueError):
                    parse_prediction(response)

    def test_evaluation_counts_unsafe_removal_and_invalid_json_as_failures(self):
        ordinary = copy.deepcopy(self.evaluation[0]['output'])
        report = evaluate_predictions([self.evaluation[2], self.evaluation[4]], [ordinary, 'not JSON'])
        self.assertEqual(report['metrics']['safe_recommendation_rate'], 0)
        self.assertEqual(report['metrics']['unsafe_or_invalid_count'], 2)
        self.assertEqual(report['metrics']['valid_json_rate'], 0.5)
        self.assertEqual(report['metrics']['policy_guardrail_pass_rate'], 0)

    def test_guardrail_metric_rejects_missing_citations_and_excess_review(self):
        missing = copy.deepcopy(self.evaluation[0]['output'])
        missing['clause_ids'] = ['P1']
        conservative = copy.deepcopy(self.evaluation[4]['output'])
        report = evaluate_predictions([self.evaluation[0], self.evaluation[0]], [missing, conservative])
        self.assertEqual(report['metrics']['safe_recommendation_rate'], 1)
        self.assertEqual(report['metrics']['policy_guardrail_pass_rate'], 0)

    def test_unknown_citation_fails_safety(self):
        prediction = copy.deepcopy(self.evaluation[0]['output'])
        prediction['clause_ids'] = ['invented-clause']
        report = evaluate_predictions([self.evaluation[0]], [prediction])
        self.assertEqual(report['metrics']['safe_recommendation_rate'], 0)

    def test_missing_river_key_never_creates_checkpoint_or_metrics(self):
        with TemporaryDirectory() as directory, patch('training.train_river.load_env'), patch.dict('os.environ', {'RIVER_API_KEY': ''}), contextlib.redirect_stderr(io.StringIO()):
            code = run_river(argparse.Namespace(output_dir=directory, check_only=False))
            self.assertEqual(code, 2)
            output_dir = Path(directory)
            self.assertEqual(json.loads((output_dir / 'river_status.json').read_text())['status'], 'not_configured')
            self.assertFalse((output_dir / 'river_checkpoint.json').exists())
            self.assertFalse((output_dir / 'river_evaluation.json').exists())

    def test_river_orchestration_keeps_eval_out_of_updates_and_samples_saved_checkpoint(self):
        # Offline API contract test; mock artifacts exist only in a deleted temp dir.
        # These test values are never application checkpoints or reported model metrics.
        events, seen_datums, sampled_prompts = [], [], []
        tokenizer = CharacterTokenizer()
        expected_outputs = [json.dumps(example['output']) for example in self.evaluation]

        def samples(prompts):
            sampled_prompts.append(prompts)
            return [[types.SimpleNamespace(text=text)] for text in expected_outputs]

        class FakeModel:
            model_id = 'unit-test-model'
            step = 0

            def sample(self, prompts, **kwargs):
                events.append('model_sample')
                return samples(prompts)

            def forward_backward(self, datums, **kwargs):
                seen_datums.extend(datums)
                return types.SimpleNamespace(metrics={'loss': 0.1})

            def optim_step(self, **kwargs):
                self.step += 1

            def save_weights(self, name, mode, **kwargs):
                self.assert_mode = mode
                events.append('save_inference')
                if mode != 'inference':
                    raise AssertionError('Wrong checkpoint mode')
                return types.SimpleNamespace(path='river://unit-test-only/checkpoint')

        class FakeSession:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def create_model(self, **kwargs):
                return FakeModel()

            def sample(self, prompts, checkpoint, **kwargs):
                if checkpoint.path != 'river://unit-test-only/checkpoint':
                    raise AssertionError('Saved checkpoint was not reused')
                events.append('checkpoint_sample')
                return samples(prompts)

        class FakeClient:
            def __init__(self, **kwargs):
                pass

            def session(self, **kwargs):
                return FakeSession()

            def close(self):
                pass

        fake_river = types.SimpleNamespace(Client=FakeClient, load_tokenizer=lambda **kwargs: tokenizer,
                                          LoraConfig=lambda **kwargs: kwargs)
        with TemporaryDirectory() as directory, patch('training.train_river.load_env'), patch.dict('os.environ', {'RIVER_API_KEY': 'unit-test-value'}), patch.dict('sys.modules', {'river_client': fake_river}), contextlib.redirect_stdout(io.StringIO()):
            args = argparse.Namespace(output_dir=directory, check_only=False, epochs=1, batch_size=4, rank=16, learning_rate=2e-4, timeout=60)
            self.assertEqual(run_river(args), 0)
            self.assertEqual(len(seen_datums), 20)
            self.assertCountEqual(seen_datums, [make_datum(x, tokenizer) for x in self.training])
            expected_prompts = [render_model_prompt(x['input'], tokenizer) for x in self.evaluation]
            self.assertEqual(sampled_prompts, [expected_prompts, expected_prompts, expected_prompts])
            self.assertEqual(events, ['model_sample', 'save_inference', 'model_sample', 'checkpoint_sample'])
            manifest = json.loads((Path(directory) / 'river_checkpoint.json').read_text())
            self.assertTrue(set(manifest['training_ids']).isdisjoint(x['id'] for x in self.evaluation))
            self.assertEqual(manifest['prompt_protocol'], 'chat_no_thinking_v1')


if __name__ == '__main__':
    unittest.main()
