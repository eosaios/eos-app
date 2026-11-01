#!/usr/bin/env python3
"""Record checked native binaries and archives alongside their frozen Git inputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def revision(repo):
    def git(value):
        return subprocess.check_output(['git', 'rev-parse', value], cwd=repo, text=True).strip()
    return {'commit': git('HEAD'), 'tree': git('HEAD^{tree}')}


def record(args):
    root = Path.cwd()
    version = args.version.removeprefix('v')
    channel = args.channel
    names = {'stable': 'EOS', 'beta': 'EOS Beta', 'dev': 'EOS Dev'}
    bundle_id = 'com.eosaios.eos-app' + ('' if channel == 'stable' else '.' + channel)
    stage = root / 'dist' / f'eos-app_{version}_{args.platform}'
    if args.platform.startswith('darwin-'):
        bundle = stage / (names[channel] + '.app')
        info = plistlib.loads((bundle / 'Contents/Info.plist').read_bytes())
        assert (info['CFBundleIdentifier'], info['CFBundleShortVersionString']) == (bundle_id, version)
        scheme = 'eosagent' + ('' if channel == 'stable' else '-' + channel)
        assert info['CFBundleURLTypes'][0]['CFBundleURLSchemes'] == [scheme]
        binary = bundle / 'Contents/MacOS/eos-app'
        core_dir = bundle / 'Contents/Resources/core' / args.triple
    else:
        binary = stage / ('eos-app.exe' if args.platform.startswith('windows-') else 'eos-app')
        core_dir = stage / 'core' / args.triple
    manifest = json.loads((core_dir / 'manifest.json').read_text())
    core_sha = sha(core_dir / manifest['binary'])
    gate = json.loads((root / 'dist' / f'upgrade-{args.platform}.json').read_text())
    assert manifest['target'] == gate['target'] == args.triple
    assert manifest['sha256'].removeprefix('sha256:') == gate['core_sha256'] == core_sha
    assert gate['passed'] and gate['provider_requests'] >= 6
    app_source = revision(root)
    identity = (root / 'dist' / f'build-identity-{args.platform}.txt').read_text()
    assert 'vcs.revision=' + app_source['commit'] in identity
    assert '-tags=eos_noembed,production' in identity
    files = {p.name: {'sha256': sha(p), 'size': p.stat().st_size}
             for p in (root / 'dist').iterdir()
             if p.is_file() and p.name.endswith(('.dmg', '.tar.gz', '.zip', '.exe'))}
    assert files
    result = {
        'channel': channel, 'version': version, 'platform': args.platform,
        'source_branch': {'stable': 'main', 'beta': 'beta', 'dev': 'dev'}[channel],
        'app_source': app_source, 'cli_source': revision(root.parent / 'eos-cli'),
        'core_source': revision(root.parent / 'eos-core-rs'),
        'distribution_source': revision(root.parent / 'release-tools'),
        'workflow_run_id': os.environ['GITHUB_RUN_ID'],
        'bundle_id': bundle_id, 'app_binary_sha256': sha(binary),
        'core_sha256': core_sha, 'core_manifest_sha256': sha(core_dir / 'manifest.json'),
        'environment': 'sandbox' if channel == 'dev' else 'production',
        'api_origin': 'https://api-test.eosaios.com' if channel == 'dev' else 'https://api.eosaios.com',
        'native_upgrade_gate': gate, 'files': files,
    }
    (root / 'dist' / f'provenance-{args.platform}.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--channel', choices=['stable', 'beta', 'dev'], required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--platform', required=True)
    parser.add_argument('--triple', required=True)
    record(parser.parse_args())
