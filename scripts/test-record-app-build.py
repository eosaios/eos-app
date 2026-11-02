import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('recorder', Path(__file__).with_name('record-app-build.py'))
recorder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recorder)

class LiveCatalogSnapshotTest(unittest.TestCase):
    def test_automatic_update_is_checked_against_its_frozen_network_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'app'
            dist = root / 'dist'; dist.mkdir(parents=True)
            source = root.parent / 'eos-core-rs/catalogs'; source.mkdir(parents=True)
            (source / 'model-capabilities-v1.json').write_text(json.dumps({'revision': 'old', 'models': [1]}))
            expected = {'schema_version': 1, 'revision': 'auto-new', 'models': [1, 2]}
            snapshot = dist / 'expected-capability-catalog-linux-arm64.json'
            snapshot.write_text(json.dumps(expected))
            gate = {'url': 'https://api.eosaios.com/api/v1/model-capabilities/v1.json',
                    'revision': 'auto-new', 'models': 2, 'actual_core_https_fetch_verified': True,
                    'persisted_cache_verified': True}
            result = dist / 'live-capability-catalog-linux-arm64.json'
            result.write_text(json.dumps(gate))
            self.assertEqual(recorder.verified_live_catalog(root, 'linux-arm64'), (gate, recorder.sha(snapshot)))
            for invalid in [{'revision': 'old'}, {'models': 1}, {'actual_core_https_fetch_verified': False}, {'persisted_cache_verified': False}]:
                with self.subTest(invalid=invalid):
                    result.write_text(json.dumps({**gate, **invalid}))
                    with self.assertRaises(AssertionError): recorder.verified_live_catalog(root, 'linux-arm64')

if __name__ == '__main__': unittest.main()
