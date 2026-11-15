#!/usr/bin/env python3
"""Verify a frozen EOS Agent release, then synchronize only its stable packages."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

ADMIN = 'https://admin.eosaios.com'
PLATFORMS = {'windows-amd64': 'Windows x64', 'darwin-arm64': 'macOS Apple Silicon',
             'darwin-amd64': 'macOS Intel', 'linux-amd64': 'Linux x64', 'linux-arm64': 'Linux ARM64'}
PREFIX = '/api/v1/admin/version-management'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


CLIENT = urllib.request.build_opener(NoRedirect())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def request(path, token='', payload=None, method=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(ADMIN + path, data=data, headers=headers, method=method)
    try:
        with CLIENT.open(req, timeout=90) as response:
            return json.load(response)['data']
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'{req.method} {path}: HTTP {error.code}') from None


def expected_files(version):
    files = {f'eos-agent-setup-v{version}.exe': ('windows-amd64', 'installer')}
    for platform in PLATFORMS:
        suffix = '.zip' if platform.startswith('windows-') else '.tar.gz'
        files[f'eos-agent_{version}_{platform}{suffix}'] = (platform, 'archive' if platform.startswith(('windows-', 'darwin-')) else 'installer')
        if platform.startswith('darwin-'):
            files[f'eos-agent_{version}_{platform}.dmg'] = (platform, 'installer')
    return files


def validate_release(root, version, expected_lock):
    raw = (root / 'release-lock.json').read_bytes()
    if not re.fullmatch('[a-f0-9]{64}', expected_lock) or digest(raw) != expected_lock:
        raise ValueError('Release lock does not match the approved digest')
    lock = json.loads(raw)
    if lock.get('version') != version or not re.fullmatch('[a-f0-9]{40}', lock.get('app_commit', '')):
        raise ValueError('Release version or frozen source is invalid')
    expected = expected_files(version)
    if set(lock['files']) != set(expected):
        raise ValueError('Release requires exactly eight named distribution files')
    for name, (platform, kind) in expected.items():
        item = lock['files'][name]
        path = root / name
        if (item['platform'], item['kind']) != (platform, kind) or item['size'] <= 0 or not re.fullmatch('[a-f0-9]{64}', item['sha256']):
            raise ValueError('Artifact identity is invalid: ' + name)
        if path.stat().st_size != item['size'] or digest(path.read_bytes()) != item['sha256']:
            raise ValueError('Artifact differs from the verified candidate: ' + name)
    return lock


def stable_apps(apps):
    selected = {}
    for platform in PLATFORMS:
        matches = [app for app in apps if app['app_key'] == 'eos-app' and app['platform'] == platform and app['release_channel'] == 'stable']
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous stable application: ' + platform)
        selected[platform] = matches[0]
    return selected


def check_version(row, expected):
    fields = ('application_id', 'platform', 'product_version', 'commit', 'file_size', 'sha256_hash')
    if any(row[field] != expected[field] for field in fields) or not row['is_active'] or row['is_deprecated'] or row['quality'] != 'stable':
        raise ValueError('Stored candidate is unavailable or differs from the verified artifact')


def verify_download(row, filename):
    url = urllib.parse.urlsplit(row['file_url'])
    prefix = f"/versions/{row['application_id']}/{row['product_version']}/{row['platform']}/"
    if (url.scheme, url.netloc) != ('https', 'dl.eosaios.com') or url.query or url.fragment or not url.path.startswith(prefix):
        raise ValueError('Unapproved artifact download origin or version path')
    tail = url.path[len(prefix):].split('/')
    if tail[-1] != filename or len(tail) not in (1, 2) or len(tail) == 2 and not re.fullmatch('[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}', tail[0]):
        raise ValueError('Unapproved artifact download filename')
    with CLIENT.open(row['file_url'], timeout=300) as response:
        value = hashlib.sha256(); size = 0
        while chunk := response.read(1024 * 1024):
            value.update(chunk); size += len(chunk)
    if (size, value.hexdigest()) != (row['file_size'], row['sha256_hash']):
        raise ValueError('Server download differs from verified artifact')


def upload(root, name, expected, notes, token):
    boundary = 'eos-agent-' + uuid.uuid4().hex
    fields = {**{key: str(value) for key, value in expected.items() if key in ('application_id', 'platform', 'product_version', 'commit')},
              'quality': 'stable', 'release_notes': notes, 'is_current': 'false'}
    body = bytearray()
    for key, value in fields.items():
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode())
    body.extend((root / name).read_bytes()); body.extend(f'\r\n--{boundary}--\r\n'.encode())
    req = urllib.request.Request(ADMIN + PREFIX + '/versions/upload', data=body,
        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'multipart/form-data; boundary=' + boundary})
    try:
        with CLIENT.open(req, timeout=600) as response:
            json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'Candidate upload HTTP {error.code}; no overwrite or permission expansion attempted') from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operation', choices=['preflight', 'sync'], required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--root', type=Path, default=Path('assets'))
    parser.add_argument('--lock-sha256', default='')
    parser.add_argument('--notes', type=Path)
    args = parser.parse_args()
    version = args.version.removeprefix('v')
    if not re.fullmatch(r'\d+\.\d+\.\d+', version) or tuple(map(int, version.split('.'))) < (1, 0, 19):
        raise ValueError('Only the renamed stable release series can be synchronized')
    lock = validate_release(args.root, version, args.lock_sha256) if args.operation == 'sync' else None
    token = request('/api/v1/admin/auth/login', payload={'email': os.environ['EOS_ADMIN_EMAIL'], 'password': os.environ['EOS_ADMIN_PASSWORD']})['access_token']
    family = request(PREFIX + '/applications?keyword=eos-app&page_size=100', token)['applications']
    apps = stable_apps(family)
    before = request('/api/v1/download/packages')['packages']
    if args.operation == 'preflight':
        print(json.dumps({'authenticated': True, 'stable_platforms': list(apps), 'legacy_display_names': sum('EOS App' in app['display_name'] for app in family), 'production_writes': False}))
        return
    notes = args.notes.read_text()
    targets, previous = {}, {}
    for name, item in lock['files'].items():
        if item['kind'] != 'installer':
            continue
        platform = item['platform']; app = apps[platform]
        rows = request(PREFIX + '/versions?application_id=' + str(app['id']), token)
        old = [row for row in rows if row['is_current']]
        if len(old) != 1:
            raise ValueError('Stable platform must have one existing current version')
        if tuple(map(int, old[0]['product_version'].split('.'))) > tuple(map(int, version.split('.'))):
            raise ValueError('A newer stable version is already current; refusing downgrade')
        previous[platform] = old[0]['id']
        expected = {'application_id': app['id'], 'platform': platform, 'product_version': version,
                    'commit': lock['app_commit'], 'file_size': item['size'], 'sha256_hash': item['sha256']}
        found = [row for row in rows if row['product_version'] == version]
        if len(found) > 1:
            raise ValueError('Duplicate target version')
        if not found:
            upload(args.root, name, expected, notes, token)
            found = [row for row in request(PREFIX + '/versions?application_id=' + str(app['id']), token) if row['product_version'] == version]
        if len(found) != 1:
            raise ValueError('Uploaded candidate could not be identified')
        check_version(found[0], expected); verify_download(found[0], name)
        targets[platform] = found[0]
    if request('/api/v1/download/packages')['packages'] != before:
        raise ValueError('Current catalogue changed while candidates were verified')
    promoted = []
    try:
        for platform, row in targets.items():
            result = request(PREFIX + '/versions/status', token, {'version_id': row['id'], 'is_current': True}, 'PUT')
            if result.get('success') is not True:
                raise ValueError('Promotion was not acknowledged')
            promoted.append(platform)
        after = request('/api/v1/download/packages')['packages']
        for platform, row in targets.items():
            matches = [entry for entry in after if entry['appKey'] == 'eos-app' and entry['platform'] == platform]
            if len(matches) != 1 or (matches[0]['versionId'], matches[0]['productVersion'], matches[0]['fileSize'], matches[0]['sha256Hash']) != (row['id'], version, row['file_size'], row['sha256_hash']):
                raise ValueError('Public catalogue does not expose the verified release')
        if [row for row in before if row['appKey'] != 'eos-app'] != [row for row in after if row['appKey'] != 'eos-app']:
            raise ValueError('An unrelated current product changed')
    except Exception:
        for platform in reversed(promoted):
            request(PREFIX + '/versions/status', token, {'version_id': previous[platform], 'is_current': True}, 'PUT')
        raise
    for platform, app in apps.items():
        request(PREFIX + '/applications/' + str(app['id']), token,
                {'display_name': 'EOS Agent (' + PLATFORMS[platform] + ')', 'description': 'EOS Agent 桌面端'}, 'PUT')
    print(json.dumps({'version': version, 'platforms': list(targets), 'verified_downloads': True, 'unrelated_products_unchanged': True}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('EOS Agent synchronization failed: ' + type(error).__name__ + ': ' + str(error), file=sys.stderr)
        raise SystemExit(1)
