#!/usr/bin/env python3
"""Publish verified compiled Todo packages to its existing public binary mirror.
Never changes GitHub latest, platform current versions, portal or private source visibility.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import tempfile

REPO = 'eosaios/eos-todo'


def gh(*args):
    return subprocess.run(['gh', *args], check=True, text=True, capture_output=True).stdout


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifests = list(pathlib.Path('candidate-assets').glob('*/release-manifest.json'))
    if len(manifests) != 3:
        raise ValueError('Exactly three native-verified package manifests required')
    packages = []
    for path in manifests:
        m = json.loads(path.read_text())
        package = path.parent / m['file']
        if (m['environment'] != 'production' or not m['runtime_verified'] or not m['distribution_ready']
                or any(m[k]['dirty'] for k in ['base', 'pro', 'core_source'])
                or package.name != m['file'] or digest(package) != m['sha256']
                or package.stat().st_size != m['file_size']):
            raise ValueError('Unverified mirror payload')
        packages.append((package, m))
    version = packages[0][1]['version']
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('Mirror requires an explicit production version')
    if {m['platform'] for _, m in packages} != {'darwin-arm64', 'linux-amd64', 'windows-amd64'}:
        raise ValueError('Unexpected mirror platforms')
    if any(m['version'] != version for _, m in packages):
        raise ValueError('Mixed mirror versions')
    latest_before = gh('api', f'repos/{REPO}/releases/latest', '--jq', '.tag_name').strip()
    tag = 'todo-mirror-v' + version
    existing = subprocess.run(['gh', 'release', 'view', tag, '--repo', REPO, '--json', 'assets,isDraft,isPrerelease'], text=True, capture_output=True)
    if existing.returncode:
        # Existing public repo only carries compiled artifacts; this prefix does
        # not trigger its v* source build or change the GitHub latest channel.
        gh('release', 'create', tag, '--repo', REPO, '--draft', '--prerelease', '--latest=false',
           '--title', 'EOS Todo ' + version + ' download mirror',
           '--notes', 'Compiled download mirror for EOS Todo platform-managed updates. The production platform controls availability and rollback. This mirror does not publish private source or promote the portal.')
        release = {'assets': [], 'isDraft': True}
    else:
        release = json.loads(existing.stdout)
    assets = {a['name']: a for a in release['assets']}
    for package, m in packages:
        if package.name not in assets:
            gh('release', 'upload', tag, '--repo', REPO, str(package))
        else:
            with tempfile.TemporaryDirectory() as temp:
                gh('release', 'download', tag, '--repo', REPO, '--pattern', package.name, '--dir', temp)
                if digest(pathlib.Path(temp) / package.name) != m['sha256']:
                    raise ValueError('Existing mirror asset differs; never overwrite')
    gh('release', 'edit', tag, '--repo', REPO, '--draft=false', '--prerelease=true', '--latest=false')
    proof = []
    # Re-download the published bytes rather than treating upload success as acceptance.
    with tempfile.TemporaryDirectory() as temp:
        for package, m in packages:
            gh('release', 'download', tag, '--repo', REPO, '--pattern', package.name, '--dir', temp)
            if digest(pathlib.Path(temp) / package.name) != m['sha256']:
                raise ValueError('Published mirror download hash mismatch')
            proof.append({'platform': m['platform'], 'version': version, 'sha256': m['sha256'],
                          'url': f'https://github.com/{REPO}/releases/download/{tag}/{package.name}',
                          'download_verified': True})
    latest_after = gh('api', f'repos/{REPO}/releases/latest', '--jq', '.tag_name').strip()
    if latest_before != latest_after:
        raise ValueError('Public latest channel changed during mirror publication')
    pathlib.Path('todo-mirror-proof.json').write_text(json.dumps({'packages': proof, 'latest_unchanged': True}, indent=2) + '\n')
    print('Three published mirror downloads verified; no current-version promotion')


if __name__ == '__main__':
    main()
