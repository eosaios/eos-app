#!/usr/bin/env python3
"""Upload verified Todo candidates as non-current versions; never promote/delete."""
import hashlib
import json
import os
import pathlib
import sys
import urllib.request
import uuid

API = 'https://api.eosaios.com'
ADMIN = os.environ.get('EOS_ADMIN_API_BASE', '').rstrip('/')
if ADMIN != 'https://admin.eosaios.com':
    raise SystemExit('Production candidate upload requires the exact production admin origin')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


CLIENT = urllib.request.build_opener(NoRedirect())


def request(path, token=None, payload=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    # The production admin reverse proxy serves the same backend catalogue;
    # public API Cloudflare rules reject some hosted-runner requests.
    req = urllib.request.Request(ADMIN + path, headers=headers,
                                 data=json.dumps(payload).encode() if payload is not None else None)
    try:
        with CLIENT.open(req, timeout=60) as response:
            return json.load(response)['data']
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'{req.method} {path}: HTTP {error.code}') from None


def sha256(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def upload(manifest, root, app, token):
    package = root / manifest['file']
    boundary = 'eos-todo-' + uuid.uuid4().hex
    fields = {'application_id': str(app['id']), 'product_version': manifest['version'],
              'commit': manifest['pro']['commit'], 'platform': manifest['platform'], 'quality': 'beta' if '-' in manifest['version'] else 'stable',
              'release_notes': '修复浏览器登录回跳状态，新增平台意见反馈，优化无可用更新提示。三平台验收中，门户未切换。', 'is_current': 'false'}
    body = bytearray()
    for name, value in fields.items():
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{package.name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode())
    body.extend(package.read_bytes())
    body.extend(f'\r\n--{boundary}--\r\n'.encode())
    req = urllib.request.Request(ADMIN + '/api/v1/admin/version-management/versions/upload', data=body,
          headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'multipart/form-data; boundary=' + boundary})
    with CLIENT.open(req, timeout=300) as response:
        return json.load(response)['data']


def validate_response(version, manifest):
    expected = {'product_version': manifest['version'], 'platform': manifest['platform'],
                'file_size': manifest['file_size'], 'sha256_hash': manifest['sha256'], 'is_current': False}
    if any(version.get(key) != value for key, value in expected.items()):
        raise ValueError('Stored candidate differs from expected immutable metadata')
    if not version['file_url'].startswith((API + '/storage/versions/', 'https://dl.eosaios.com/versions/')):
        raise ValueError('Unexpected candidate storage origin')


def main():
    if sys.argv[1:] == ['--preflight']:
        token = request('/api/v1/admin/auth/login', payload={'email': os.environ['EOS_ADMIN_EMAIL'],
                        'password': os.environ['EOS_ADMIN_PASSWORD']})['access_token']
        request('/api/v1/admin/version-management/applications', token)['applications']
        print('Production version-management authentication and read access passed')
        return
    manifests = list(pathlib.Path('candidate-assets').glob('*/release-manifest.json'))
    if len(manifests) != 3:
        raise ValueError('Exactly three platform manifests are required')
    packages_before = request('/api/v1/download/packages')['packages']
    token = request('/api/v1/admin/auth/login', payload={'email': os.environ['EOS_ADMIN_EMAIL'],
                    'password': os.environ['EOS_ADMIN_PASSWORD']})['access_token']
    apps = request('/api/v1/admin/version-management/applications', token)['applications']
    results = []
    platforms = set()
    for path in sorted(manifests):
        m = json.loads(path.read_text())
        platform = m['platform']
        if platform in platforms or platform not in {'darwin-arm64', 'windows-amd64', 'linux-amd64'}:
            raise ValueError('Unexpected or duplicate platform')
        platforms.add(platform)
        if m['environment'] != 'production' or not m.get('distribution_ready') or not m.get('runtime_verified'):
            raise ValueError('Candidate did not pass native package verification')
        if any(m[key]['dirty'] for key in ['base', 'pro', 'core_source']):
            raise ValueError('Candidate was built from dirty sources')
        package = path.parent / m['file']
        if package.stat().st_size != m['file_size'] or sha256(package) != m['sha256']:
            raise ValueError('Candidate artifact digest mismatch')
        name = 'eos-todo-' + platform
        matches = [a for a in apps if a['name'] == name]
        if len(matches) > 1:
            raise ValueError('Ambiguous version-management application')
        app = matches[0] if matches else request('/api/v1/admin/version-management/applications', token,
                   {'name': name, 'app_key': 'eos-todo', 'display_name': 'EOS Todo (' + platform + ')',
                    'platform': platform, 'description': 'EOS Todo 桌面端'})
        if app['app_key'] != 'eos-todo' or app['platform'] != platform:
            raise ValueError('Version application identity mismatch')
        existing = request('/api/v1/admin/version-management/versions?application_id=' + str(app['id']), token)
        if not isinstance(existing, list):
            raise ValueError('Unexpected version-list response')
        matches = [v for v in existing if v['product_version'] == m['version']]
        if len(matches) > 1:
            raise ValueError('Duplicate candidate version')
        version = matches[0] if matches else upload(m, path.parent, app, token)
        validate_response(version, m)
        results.append({'platform': platform, 'version': m['version'], 'version_id': version['id'],
                        'application_id': app['id'], 'url': version['file_url'], 'sha256': m['sha256'],
                        'file_size': m['file_size'], 'is_current': False})
        print('Candidate stored and verified: ' + platform, flush=True)
    after = request('/api/v1/download/packages')['packages']
    if after != packages_before:
        raise ValueError('Public current package catalogue changed during upload; investigate before promotion')
    pathlib.Path('todo-downloads.json').write_text(json.dumps({'packages': results, 'public_catalogue_unchanged': True}, indent=2) + '\n')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # HTTP error bodies/authentication responses must never enter public CI logs.
        print('Candidate upload failed: ' + type(error).__name__ + ': ' + str(error), file=sys.stderr)
        raise SystemExit(1)
