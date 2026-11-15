import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('recorder', Path(__file__).with_name('record-app-build.py'))
recorder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recorder)


class ComposerInputGateTest(unittest.TestCase):
    def test_actual_budget_and_no_persistence_are_required_for_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'dist').mkdir()
            path = root / 'dist/composer-input-linux-amd64.json'
            gate = {'passed': True, 'unknown_limit_explicit': True,
                    'oversized_turn_rejected_before_persistence': True, 'no_cloud_requests': True,
                    'inference_requests': 0,
                    'exact_boundary': {'estimated_tokens': 8, 'max_input_tokens': 8},
                    'selected_larger_model': {'estimated_tokens': 8, 'max_input_tokens': 256}}
            path.write_text(json.dumps(gate))
            self.assertEqual(recorder.verified_composer_input(root, 'linux-amd64'), gate)
            for bad in [{'oversized_turn_rejected_before_persistence': False}, {'inference_requests': 1},
                        {'exact_boundary': {'estimated_tokens': 8, 'max_input_tokens': 80}},
                        {'unknown_limit_explicit': False}]:
                with self.subTest(bad=bad):
                    path.write_text(json.dumps({**gate, **bad}))
                    with self.assertRaises(AssertionError):
                        recorder.verified_composer_input(root, 'linux-amd64')


if __name__ == '__main__':
    unittest.main()
