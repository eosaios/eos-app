#!/usr/bin/env python3
"""Native candidate builds with sealed diagnostics and an explicit export allowlist.

Source coordinates and immutable refs arrive only through repository secrets.
No subprocess output, source tree, credential or plaintext diagnostic is exported.
"""
import base64
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile
import time
import traceback
import urllib.request
import urllib.parse

from cryptography.fernet import Fernet


def digest(path):
    value = hashlib.sha256()
    with pathlib.Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def validate_config(config, version):
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version) or config['version'] != version:
        raise ValueError('candidate version must match its frozen configuration')
    Fernet(config['diagnostics_key'].encode())
    for name in ['base', 'pro', 'core']:
        item = config[name]
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', item['repository']):
            raise ValueError('invalid source repository')
        if not re.fullmatch(r'[0-9a-f]{40}', item['commit']):
            raise ValueError('source must be an immutable commit')
        if not re.fullmatch(r'[A-Za-z0-9_-]+', item['directory']):
            raise ValueError('invalid source directory')
    if len({config[name]['directory'] for name in ['base', 'pro', 'core']}) != 3:
        raise ValueError('source directories must be independent')


def export_manifest(source, output):
    manifest = json.loads(source.read_text())
    if manifest['channel'] != 'stable' or manifest['environment'] != 'production':
        raise ValueError('wrong candidate channel')
    if not manifest['runtime_verified'] or not manifest['distribution_ready']:
        raise ValueError('candidate was not natively verified')
    if any(manifest[name]['dirty'] for name in ['base', 'pro', 'core_source']):
        raise ValueError('candidate source is dirty')
    filename = manifest['file']
    if pathlib.Path(filename).name != filename or not re.fullmatch(r'eos-todo_[0-9.]+_(windows-amd64\.exe|linux-amd64\.tar\.gz)', filename):
        raise ValueError('unexpected export filename')
    package = source.parent / filename
    if package.stat().st_size != manifest['file_size'] or digest(package) != manifest['sha256']:
        raise ValueError('candidate digest differs')
    # These manifests carry only opaque source fingerprints and package identity.
    # Reject future additions that could expose local paths or source coordinates.
    encoded = json.dumps(manifest)
    if re.search(r'https?://(?!api\.eosaios\.com)|/Users/|/home/|[A-Za-z]:\\|github\.com|token|password|secret', encoded, re.I):
        raise ValueError('manifest contains non-public metadata')
    shutil.copy2(package, output / filename)
    (output / 'release-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (output / 'SHA256SUMS.txt').write_text(manifest['sha256'] + '  ' + filename + '\n')
    return manifest


class Candidate:
    def __init__(self, config, platform, version, root, log):
        self.config, self.platform, self.version = config, platform, version
        self.root, self.log = root, log
        self.stage = 'configuration'
        self.env = {key: value for key, value in os.environ.items()
                    if key not in ['PRIVATE_SOURCE_TOKEN', 'PRIVATE_BUILD_CONFIG', 'GITHUB_TOKEN', 'GH_TOKEN']}
        self.env.update(GIT_TERMINAL_PROMPT='0', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
        self.paths = {name: root / config[name]['directory'] for name in ['base', 'pro', 'core']}

    def run(self, args, cwd=None, env=None):
        subprocess.run([str(arg) for arg in args], cwd=cwd or self.root, env=env or self.env,
                       stdout=self.log, stderr=subprocess.STDOUT, check=True)

    def capture(self, args, cwd=None, env=None):
        result = subprocess.run([str(arg) for arg in args], cwd=cwd or self.root, env=env or self.env,
                                stdout=subprocess.PIPE, stderr=self.log, check=True)
        return result.stdout.decode('utf-8')

    def checkout(self, token):
        self.stage = 'source checkout'
        auth = base64.b64encode(('x-access-token:' + token).encode()).decode()
        env = dict(self.env, GIT_CONFIG_COUNT='2', GIT_CONFIG_KEY_0='http.https://github.com/.extraheader',
                   GIT_CONFIG_VALUE_0='AUTHORIZATION: basic ' + auth,
                   GIT_CONFIG_KEY_1='core.autocrlf', GIT_CONFIG_VALUE_1='false')
        for name, destination in self.paths.items():
            item = self.config[name]
            remote = 'https://github.com/' + item['repository'] + '.git'
            if name in ['base', 'pro']:
                head = self.capture(['git', 'ls-remote', '--exit-code', remote, 'refs/heads/main'], env=env).split()[0]
                if head != item['commit']:
                    raise ValueError('stable source is no longer the frozen main head')
            self.run(['git', 'init', destination], env=env)
            self.run(['git', '-C', destination, 'config', 'core.autocrlf', 'false'], env=env)
            self.run(['git', '-C', destination, 'remote', 'add', 'origin', remote], env=env)
            self.run(['git', '-C', destination, 'fetch', '--depth', '1', 'origin', item['commit']], env=env)
            self.run(['git', '-C', destination, 'checkout', '--detach', 'FETCH_HEAD'], env=env)
        pin = json.loads((self.paths['pro'] / 'pro/corehost/core-manifest.json').read_text())
        if pin['core_commit'] != self.config['core']['commit']:
            raise ValueError('core source differs from the product pairing')

    def build(self):
        self.stage = 'native prerequisites'
        base, pro, core = [self.paths[name] for name in ['base', 'pro', 'core']]
        target = 'x86_64-pc-windows-gnu' if self.platform == 'windows-amd64' else 'x86_64-unknown-linux-gnu'
        self.run(['rustup', 'target', 'add', target])
        self.run(['go', 'install', 'github.com/wailsapp/wails/v3/cmd/wails3@v3.1.0'])
        self.run([sys.executable, '-m', 'pip', 'install', '-r', base / 'build/requirements-icons.txt'])
        self.run(['npm' + ('.cmd' if os.name == 'nt' else ''), 'ci'], base / 'frontend')
        self.stage = 'native product engine'
        self.run(['cargo', 'build', '--locked', '--release', '--target', target, '-p', 'eos-core-bin',
                  '--bin', 'eos-core-todo', '--features', 'product-todo'], core)
        executable = 'eos-core-todo' + ('.exe' if os.name == 'nt' else '')
        engine = core / 'target' / target / 'release' / executable
        # Compose validates the development pair even before platform packaging.
        # Seed its ignored working copy with the native binary; the builder's
        # overlay still owns the final immutable pair and verification.
        (pro / 'pro/bin').mkdir(parents=True, exist_ok=True)
        shutil.copy2(engine, pro / 'pro/bin' / executable)
        self.stage = 'native application package'
        candidate = self.root / 'candidate'
        self.run([sys.executable, pro / 'scripts/build-platform.py', '--platform', self.platform,
                  '--channel', 'stable', '--version', self.version, '--base', base,
                  '--core', engine, '--core-source', core, '--output', candidate], pro)
        stage = pro / '.release' / ('stable-production-' + self.version + '-' + self.platform + '.noindex')
        pair = stage / 'core'
        shutil.copytree(pair, pro / 'pro/bin', dirs_exist_ok=True)
        self.stage = 'native regression tests'
        test_env = dict(self.env, GOFLAGS='-overlay=' + str(stage / 'overlay.json'),
                        EOS_CORE_TODO_BIN=str(pair / executable), EOS_CORE_TODO_TEST_MANIFEST=str(pair / 'core-manifest.json'))
        npm = 'npm.cmd' if os.name == 'nt' else 'npm'
        self.run([npm, 'run', 'build'], base / 'frontend')
        prefix = ['xvfb-run', '-a'] if os.name != 'nt' else []
        for source in [base, pro]:
            self.run(prefix + ['go', 'test', './...'], source, test_env)
            self.run(['go', 'vet', './...'], source, test_env)
        self.run([npm, 'test', '--', '--run', '--maxWorkers=2', '--testTimeout=15000'], pro / '.compose/frontend')
        self.stage = 'installer lifecycle'
        self.verify_install(candidate)
        return candidate

    def verify_binary(self, binary):
        info = json.loads(self.capture([binary, '--build-info']))
        if any(info[key] != value for key, value in {'version': self.version, 'channel': 'stable',
                'environment': 'production', 'platform': self.platform, 'app_key': 'eos-todo',
                'api_origin': 'https://api.eosaios.com'}.items()):
            raise ValueError('installed application identity differs')
        result = json.loads(self.capture([binary, '--verify-package']))
        if result.get('passed') is not True:
            raise ValueError('installed package did not verify')

    def verify_install(self, candidate):
        data = pathlib.Path(os.environ['APPDATA']) / 'eos-todolist' if os.name == 'nt' else pathlib.Path.home() / '.config/eos-todolist'
        data.mkdir(parents=True, exist_ok=True)
        marker = data / 'candidate-preservation-check.txt'
        marker.write_text('synthetic runner fixture')
        self.install_baseline()
        if os.name == 'nt':
            import winreg
            installer = next(candidate.glob('*.exe'))
            installed = self.root / 'installed'
            for _ in range(2):
                self.run([installer, '/S', '/D=' + str(installed)])
                self.verify_binary(installed / 'eos-todo.exe')
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\eostodo\shell\open\command') as key:
                    command = winreg.QueryValueEx(key, '')[0]
                if str(installed / 'eos-todo.exe').lower() not in command.lower():
                    raise ValueError('installed login protocol differs')
            self.run([installed / 'uninstall.exe', '/S'])
            for _ in range(50):
                if not (installed / 'eos-todo.exe').exists():
                    break
                time.sleep(.1)
            if (installed / 'eos-todo.exe').exists():
                raise ValueError('uninstaller left the executable installed')
        else:
            archive = next(candidate.glob('*.tar.gz'))
            extracted = self.root / 'extracted'
            with tarfile.open(archive) as stream:
                stream.extractall(extracted, filter='data')
            portable = next(extracted.iterdir())
            for _ in range(2):
                self.run(['bash', portable / 'install-user.sh'])
                self.verify_binary(pathlib.Path.home() / '.local/share/eos-todo/eos-todo')
            desktop = pathlib.Path.home() / '.local/share/applications/eos-todo.desktop'
            text = desktop.read_text()
            if 'MimeType=x-scheme-handler/eostodo;' not in text or 'Icon=/' not in text:
                raise ValueError('installed desktop entry differs')
        if marker.read_text() != 'synthetic runner fixture':
            raise ValueError('installer changed user data')

    def install_baseline(self):
        baseline = self.config['baselines'][self.platform]
        parsed = urllib.parse.urlparse(baseline['url'])
        if parsed.scheme != 'https' or parsed.netloc != 'dl.eosaios.com' or not re.fullmatch(r'[0-9a-f]{64}', baseline['sha256']):
            raise ValueError('invalid frozen upgrade baseline')
        package = self.root / ('baseline.exe' if os.name == 'nt' else 'baseline.tar.gz')
        with urllib.request.urlopen(baseline['url'], timeout=120) as source, package.open('wb') as destination:
            shutil.copyfileobj(source, destination)
        if digest(package) != baseline['sha256']:
            raise ValueError('upgrade baseline digest differs')
        if os.name == 'nt':
            binary = self.root / 'installed/eos-todo.exe'
            self.run([package, '/S', '/D=' + str(binary.parent)])
        else:
            extracted = self.root / 'baseline-extracted'
            with tarfile.open(package) as stream:
                stream.extractall(extracted, filter='data')
            self.run(['bash', next(extracted.iterdir()) / 'install-user.sh'])
            binary = pathlib.Path.home() / '.local/share/eos-todo/eos-todo'
        info = json.loads(self.capture([binary, '--build-info']))
        if info['version'] != baseline['version'] or info['channel'] != 'stable':
            raise ValueError('installed upgrade baseline identity differs')


def main():
    output = pathlib.Path(os.environ['RUNNER_TEMP']) / 'todo-export'
    output.mkdir(parents=True, exist_ok=False)
    root = pathlib.Path(os.environ['RUNNER_TEMP']) / 'todo-private'
    root.mkdir(parents=True, exist_ok=False)
    config = json.loads(os.environ['PRIVATE_BUILD_CONFIG'])
    version, platform = os.environ['CANDIDATE_VERSION'], os.environ['CANDIDATE_PLATFORM']
    if platform not in ['windows-amd64', 'linux-amd64']:
        raise ValueError('unsupported native target')
    validate_config(config, version)
    log_path = root / 'build.log'
    success = False
    with log_path.open('wb') as log:
        build = Candidate(config, platform, version, root, log)
        try:
            build.checkout(os.environ['PRIVATE_SOURCE_TOKEN'])
            candidate = build.build()
            build.stage = 'export policy'
            manifest = export_manifest(candidate / 'release-manifest.json', output)
            receipt = dict(platform=platform, version=version, native_package_verified=True,
                           native_regressions_passed=True, installer_lifecycle_passed=True,
                           upgrade_baseline=build.config['baselines'][platform]['version'],
                           sha256=manifest['sha256'])
            (output / 'verification.json').write_text(json.dumps(receipt, indent=2) + '\n')
            success = True
        except Exception:
            log.write(traceback.format_exc().encode())
            print('::error::Candidate failed during ' + build.stage + '. Detailed diagnostics are sealed.')
    sealed = Fernet(config['diagnostics_key'].encode()).encrypt(log_path.read_bytes())
    (output / 'diagnostics.fernet').write_bytes(sealed)
    if not success:
        return 1
    print('Native candidate, regression tests and installer checks passed. Export allowlist verified.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        # Configuration and authentication material must not reach public logs.
        print('::error::Candidate configuration failed; no private diagnostic was printed.')
        raise SystemExit(1)
