#!/usr/bin/env python3
"""Explicitly authorized promotion of the three verified Todo 1.0.1 records."""
import json
import os
import pathlib
import urllib.request
from importlib.machinery import SourceFileLoader

upload = SourceFileLoader('todo_candidate', str(pathlib.Path(__file__).with_name('todo-upload-candidate.py'))).load_module()
TARGETS = [
    (7, 121, 'darwin-arm64', 12146790, '6579cbaa05892f4c3c0d3d76f6af476901f5a419858f7683cea47d155632cc48'),
    (8, 122, 'linux-amd64', 12098821, 'b3c669bff910bc77c0e4906e7679710e020227276157abc9e03b1bdd7cb54c89'),
    (9, 123, 'windows-amd64', 13452793, 'bdbdcfdc5b5649e7283719694442bef69b2f3a274fbba97e7ac0f48e4947d284'),
]


def main():
    token = upload.request('/api/v1/admin/auth/login', payload={
        'email': os.environ['EOS_ADMIN_EMAIL'], 'password': os.environ['EOS_ADMIN_PASSWORD']})['access_token']
    apps = upload.request('/api/v1/admin/version-management/applications', token)['applications']
    before = upload.request('/api/v1/download/packages')['packages']
    # Validate every target before changing any current flag.
    for app_id, version_id, platform, size, digest in TARGETS:
        app = next(a for a in apps if a['id'] == app_id)
        if app['app_key'] != 'eos-todo' or app['platform'] != platform:
            raise ValueError('Application identity differs from verified release')
        versions = upload.request(f'/api/v1/admin/version-management/versions?application_id={app_id}', token)
        v = next(v for v in versions if v['id'] == version_id)
        if (v['product_version'] != '1.0.1' or v['platform'] != platform or v['sha256_hash'] != digest
                or v['file_size'] != size or not v['is_active'] or v['is_deprecated']):
            raise ValueError('Target version is unavailable or differs from verified release')
    for app_id, version_id, platform, size, digest in TARGETS:
        req = urllib.request.Request(upload.ADMIN + '/api/v1/admin/version-management/versions/status', method='PUT',
            data=json.dumps({'version_id': version_id, 'is_current': True}).encode(),
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
        with upload.CLIENT.open(req, timeout=60) as response:
            if json.load(response)['data'].get('success') is not True:
                raise ValueError('Promotion did not report success')
        print('Current version set: ' + platform + ' 1.0.1', flush=True)
    after = upload.request('/api/v1/download/packages')['packages']
    for app_id, version_id, platform, size, digest in TARGETS:
        matches = [p for p in after if p['appKey'] == 'eos-todo' and p['platform'] == platform]
        if len(matches) != 1:
            raise ValueError('Public current catalogue is ambiguous')
        p = matches[0]
        if (p['versionId'] != version_id or p['productVersion'] != '1.0.1' or p['sha256Hash'] != digest or p['fileSize'] != size):
            raise ValueError('Public catalogue does not expose the promoted release')
        versions = upload.request(f'/api/v1/admin/version-management/versions?application_id={app_id}', token)
        if [v['id'] for v in versions if v['is_current']] != [version_id]:
            raise ValueError('Version management current flag is ambiguous')
    if [p for p in before if p['appKey'] != 'eos-todo'] != [p for p in after if p['appKey'] != 'eos-todo']:
        raise ValueError('An unrelated product current catalogue changed')
    pathlib.Path('todo-current-promotion.json').write_text(json.dumps({
        'version': '1.0.1', 'current_packages': [p for p in after if p['appKey'] == 'eos-todo'],
        'other_products_unchanged': True}, ensure_ascii=False, indent=2) + '\n')
    print('All three public current packages verified; other products unchanged')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Promotion failed: ' + type(error).__name__ + ': ' + str(error))
        raise SystemExit(1)
