import importlib.util
import json
import contextlib
import io
import os
import pathlib
import tempfile
import unittest
import subprocess
from unittest.mock import patch

from cryptography.fernet import Fernet

spec = importlib.util.spec_from_file_location('candidate', pathlib.Path(__file__).with_name('todo-native-candidate.py'))
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


class PrivacyGuards(unittest.TestCase):
    def config(self):
        return dict(version='1.4.9', diagnostics_key=Fernet.generate_key().decode(),
                    **{name: dict(repository='example/private-' + name, commit='a' * 40, directory='component-' + name)
                       for name in ['base', 'pro', 'core']})

    def test_rejects_moving_refs_traversal_and_version_mismatch(self):
        for key, value in [('commit', 'main'), ('directory', '../source'), ('repository', 'https://untrusted/source')]:
            config = self.config()
            config['base'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                candidate.validate_config(config, '1.4.9')
        with self.assertRaises(ValueError):
            candidate.validate_config(self.config(), '1.4.10')

    def test_beta_uses_its_own_version_rules_and_install_identity(self):
        config = dict(self.config(), version='1.4.10-beta.1', channel='beta')
        candidate.validate_config(config, config['version'])
        with self.assertRaises(ValueError):
            candidate.validate_config(dict(config, channel='stable'), config['version'])
        with tempfile.TemporaryDirectory() as directory, open(os.devnull, 'wb') as log:
            build = candidate.Candidate(config, 'darwin-arm64', config['version'], pathlib.Path(directory), log)
            self.assertEqual((build.branch, build.app_key, build.scheme, build.data_dir),
                             ('beta', 'eos-todo-beta', 'eostodo-beta', 'eos-todolist-beta'))

    def test_beta_baseline_accepts_only_the_exact_official_api_version(self):
        config = dict(self.config(), version='1.4.10-beta.1', channel='beta')
        with tempfile.TemporaryDirectory() as directory, open(os.devnull, 'wb') as log:
            root = pathlib.Path(directory)
            build = candidate.Candidate(config, 'darwin-arm64', config['version'], root, log)
            tested = root / 'fixture'
            tested.write_bytes(b'authentic package fixture')
            reference = {'url': 'https://api.eosaios.com/api/v1/download/versions/273/file/eos-todo-beta_old.dmg',
                         'sha256': candidate.digest(tested), 'version_id': 273}
            with patch.object(build, 'run') as download:
                build.download_baseline(reference, tested)
                download.assert_called_once()
                for update in ({'version_id': 274}, {'url': reference['url'].replace('api.eosaios.com', 'other.example')},
                               {'url': reference['url'] + '?redirect=elsewhere'}):
                    with self.assertRaises(ValueError):
                        build.download_baseline(dict(reference, **update), tested)
                download.assert_called_once()

    def test_child_process_environment_excludes_credentials_and_configuration(self):
        with tempfile.TemporaryDirectory() as directory, open(os.devnull, 'wb') as log, patch.dict(os.environ, {
                'PRIVATE_BUILD_CONFIG': 'private coordinates', 'PRIVATE_SOURCE_TOKEN': 'credential',
                'GH_TOKEN': 'another credential', 'GITHUB_TOKEN': 'runner credential'}):
            build = candidate.Candidate(self.config(), 'linux-amd64', '1.4.9', pathlib.Path(directory), log)
            self.assertEqual({key: build.env.get(key) for key in ['PRIVATE_BUILD_CONFIG', 'PRIVATE_SOURCE_TOKEN', 'GH_TOKEN', 'GITHUB_TOKEN']},
                             dict(PRIVATE_BUILD_CONFIG=None, PRIVATE_SOURCE_TOKEN=None, GH_TOKEN=None, GITHUB_TOKEN=None))

    def fixture(self, root):
        filename = 'eos-todo_1.4.9_linux-amd64.tar.gz'
        (root / filename).write_bytes(b'synthetic package')
        manifest = dict(channel='stable', environment='production', runtime_verified=True, distribution_ready=True,
                        file=filename, file_size=17, sha256=candidate.digest(root / filename),
                        api_origin='https://api.eosaios.com', **{name: dict(commit='a' * 40, dirty=False) for name in ['base', 'pro', 'core_source']})
        path = root / 'release-manifest.json'
        path.write_text(json.dumps(manifest))
        return path, manifest

    def test_export_copies_only_installer_identity_and_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory); output = root / 'out'; output.mkdir()
            path, manifest = self.fixture(root)
            (root / 'source.go').write_text('private source')
            (root / 'build.log').write_text('private diagnostic')
            self.assertEqual(candidate.export_manifest(path, output), manifest)
            self.assertEqual(sorted(p.name for p in output.iterdir()), ['SHA256SUMS.txt', manifest['file'], 'release-manifest.json'])
            self.assertEqual((output / manifest['file']).read_bytes(), b'synthetic package')

    def test_export_rejects_paths_secrets_and_changed_package(self):
        for field, value in [('file', '../private.txt'), ('debug', '/home/runner/private/source.go'),
                             ('repository', 'https://github.com/example/private'), ('token', 'credential')]:
            with tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory); output = root / 'out'; output.mkdir()
                path, manifest = self.fixture(root); manifest[field] = value; path.write_text(json.dumps(manifest))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    candidate.export_manifest(path, output)
                self.assertEqual(list(output.iterdir()), [])
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory); output = root / 'out'; output.mkdir()
            path, manifest = self.fixture(root); (root / manifest['file']).write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                candidate.export_manifest(path, output)

    def test_failed_build_seals_details_without_printing_them(self):
        private = 'private source diagnostic and confidential identifier'
        config = self.config()
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
                'RUNNER_TEMP': directory, 'PRIVATE_BUILD_CONFIG': json.dumps(config), 'PRIVATE_SOURCE_TOKEN': 'credential',
                'CANDIDATE_VERSION': '1.4.9', 'CANDIDATE_PLATFORM': 'linux-amd64'}), \
                patch.object(candidate.Candidate, 'checkout'), patch.object(candidate.Candidate, 'build', side_effect=ValueError(private)):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(candidate.main(), 1)
            self.assertNotIn(private, output.getvalue())
            exported = pathlib.Path(directory) / 'todo-export'
            self.assertEqual([p.name for p in exported.iterdir()], ['diagnostics.fernet'])
            sealed = (exported / 'diagnostics.fernet').read_bytes()
            self.assertNotIn(private.encode(), sealed)
            self.assertIn(private.encode(), Fernet(config['diagnostics_key'].encode()).decrypt(sealed))

    def test_native_macos_app_and_build_manifest_are_exported_only_sealed(self):
        config = dict(self.config(), version='1.4.10-beta.1', channel='beta',
                      baselines={'darwin-arm64': {'version': '1.4.8-beta.1'}})
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            build_results = root / 'fixture'
            build_results.mkdir()
            files = ('build-manifest.json', 'macos-payload.zip')
            for name in files:
                (build_results / name).write_text('private candidate ' + name)
            env = dict(RUNNER_TEMP=directory, PRIVATE_BUILD_CONFIG=json.dumps(config),
                       PRIVATE_SOURCE_TOKEN='credential', CANDIDATE_VERSION=config['version'],
                       CANDIDATE_PLATFORM='darwin-arm64', CANDIDATE_CHANNEL='beta')
            with patch.dict(os.environ, env), patch.object(candidate.Candidate, 'checkout'), \
                    patch.object(candidate.Candidate, 'build', return_value=build_results), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(candidate.main(), 0)
            exported = root / 'todo-export'
            self.assertEqual(sorted(p.name for p in exported.iterdir()),
                             sorted(['diagnostics.fernet', 'verification.json'] + [name + '.fernet' for name in files]))
            sealing = Fernet(config['diagnostics_key'].encode())
            for name in files:
                self.assertEqual(sealing.decrypt((exported / (name + '.fernet')).read_bytes()),
                                 (build_results / name).read_bytes())

    def test_native_acceptance_collects_independent_failures_and_rejects_candidate(self):
        with tempfile.TemporaryDirectory() as directory, open(os.devnull, 'wb') as log:
            root = pathlib.Path(directory)
            build = candidate.Candidate(self.config(), 'linux-amd64', '1.4.9', root, log)
            calls = []
            def run(args, cwd=None, env=None):
                calls.append((args, cwd))
                if 'test' in args and 'go' in args and cwd == build.paths['base']:
                    raise subprocess.CalledProcessError(1, args)
            with patch.object(build, 'run', side_effect=run), \
                    patch.object(build, 'verify_install', side_effect=ValueError('synthetic installer failure')) as install:
                with self.assertRaises(ExceptionGroup) as failed:
                    build.verify_native(root / 'candidate', root / 'stage')
            self.assertEqual([type(error) for error in failed.exception.exceptions],
                             [subprocess.CalledProcessError, ValueError])
            self.assertEqual(len(calls), 6)
            self.assertEqual(calls[-1][0][1], 'test')
            install.assert_called_once_with(root / 'candidate')


if __name__ == '__main__':
    unittest.main()
