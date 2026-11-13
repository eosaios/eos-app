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


def verified_live_catalog(root, platform):
    live_gate = json.loads((root / 'dist' / f'live-capability-catalog-{platform}.json').read_text())
    expected_snapshot = root / 'dist' / f'expected-capability-catalog-{platform}.json'
    expected_catalog = json.loads(expected_snapshot.read_text())
    assert live_gate['url'] == 'https://api.eosaios.com/api/v1/model-capabilities/v1.json'
    assert live_gate['actual_core_https_fetch_verified'] and live_gate['persisted_cache_verified']
    assert (live_gate['revision'], live_gate['models']) == (expected_catalog['revision'], len(expected_catalog['models']))
    return live_gate, sha(expected_snapshot)


def record(args):
    root = Path.cwd()
    version = args.version.removeprefix('v')
    channel = args.channel
    names = {'stable': 'EOS Agent', 'beta': 'EOS Agent Beta', 'dev': 'EOS Agent Dev'}
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
    proxy_gate = json.loads((root / 'dist' / f'proxy-{args.platform}.json').read_text())
    assert proxy_gate['no_cloud_requests'] and len(proxy_gate['requests']) == 27
    expected = {(protocol, route) for protocol in ('openai_chat', 'openai_responses', 'anthropic')
                for route in ('proxy-one', 'proxy-two', 'direct')}
    assert {(check['protocol'], check['route']) for check in proxy_gate['checks']} == expected
    assert all(check['list'] and check['verify'] and check['turn_stream'] for check in proxy_gate['checks'])
    capability_gate = json.loads((root / 'dist' / f'capabilities-{args.platform}.json').read_text())
    assert capability_gate['no_cloud_requests'] and capability_gate['restart_preserved_upstream_limits']
    assert [(turn['request_effort'], turn['actual_context_window']) for turn in capability_gate['turns']] == [
        (level, 1_050_000) for level in ('low', 'medium', 'high', 'xhigh', 'max', 'none')
    ] + [('max', 64_000)]
    dynamic_gate = json.loads((root / 'dist' / f'dynamic-capabilities-{args.platform}.json').read_text())
    assert len(dynamic_gate['actual_turns']) == len(dynamic_gate['requests']) == 15
    assert sum(turn['image_input'] for turn in dynamic_gate['actual_turns']) == 14
    for check in ('provider_priority_per_field', 'online_catalog_update_without_rebuild',
                  'removed_provider_claims_use_catalog', 'vision_denied_before_inference',
                  'invalid_catalog_keeps_valid_cache', 'offline_restart_uses_cached_capabilities',
                  'catalog_requests_have_no_credentials', 'no_cloud_inference'):
        assert dynamic_gate[check], check
    def image_blocks(value):
        if isinstance(value, dict):
            if value.get('type') in ('image', 'image_url', 'input_image'):
                yield value
            for child in value.values():
                yield from image_blocks(child)
        elif isinstance(value, list):
            for child in value:
                yield from image_blocks(child)
    for request in dynamic_gate['requests']:
        assert len(list(image_blocks(request['body']))) == int(request['actual_image_bytes_sent'])
    live_gate, expected_catalog_sha = verified_live_catalog(root, args.platform)
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
        'build_workflow_run_id': os.environ.get('EOS_REUSED_BUILD_RUN_ID', os.environ['GITHUB_RUN_ID']),
        'expected_catalog_sha256': expected_catalog_sha,
        'bundle_id': bundle_id, 'app_binary_sha256': sha(binary),
        'core_sha256': core_sha, 'core_manifest_sha256': sha(core_dir / 'manifest.json'),
        'environment': 'sandbox' if channel == 'dev' else 'production',
        'api_origin': 'https://api-test.eosaios.com' if channel == 'dev' else 'https://api.eosaios.com',
        'native_upgrade_gate': gate, 'native_proxy_gate': proxy_gate,
        'native_capability_gate': capability_gate, 'native_dynamic_capability_gate': dynamic_gate,
        'native_live_catalog_gate': live_gate, 'files': files,
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
