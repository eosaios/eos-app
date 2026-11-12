#!/usr/bin/env python3
"""Re-record a frozen candidate whose only failed step was provenance recording."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tarfile
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--platform', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--triple', required=True)
    args = parser.parse_args()
    run = json.loads(subprocess.check_output([
        'gh', 'run', 'view', args.run_id, '-R', 'eosaios/eos-app',
        '--json', 'status,jobs,headSha,url',
    ], text=True))
    assert run['status'] == 'completed', 'Build must finish before recovering evidence'
    jobs = [job for job in run['jobs'] if job['name'] == 'build (' + args.platform.replace('-', '/') + ')']
    assert len(jobs) == 1
    job = jobs[0]
    failures = [step['name'] for step in job['steps'] if step['conclusion'] == 'failure']
    assert failures == ['Record packaged provenance'], failures
    passed = {step['name'] for step in job['steps'] if step['conclusion'] == 'success'}
    assert {'Build release archive', 'Verify packaged legacy upgrade and restart'} <= passed
    assert ('Verify Windows login protocol registration' if args.platform.startswith('windows-')
            else 'Verify Linux login protocol registration') in passed or args.platform.startswith('darwin-')

    root = Path.cwd()
    version = args.version.removeprefix('v')
    suffix = '.zip' if args.platform.startswith('windows-') else '.tar.gz'
    archive = root / 'dist' / f'eos-app_{version}_{args.platform}{suffix}'
    # The immutable archive came from this repository's checked build workflow.
    # Reject path traversal before unpacking the stage used by the recorder.
    if suffix == '.zip':
        with zipfile.ZipFile(archive) as zipped:
            for name in zipped.namelist():
                assert not Path(name).is_absolute() and '..' not in Path(name).parts
            zipped.extractall(root / 'dist')
    else:
        with tarfile.open(archive) as tar:
            for item in tar.getmembers():
                assert not Path(item.name).is_absolute() and '..' not in Path(item.name).parts
            tar.extractall(root / 'dist', filter='data')
    os.environ['EOS_REUSED_BUILD_RUN_ID'] = args.run_id
    recorder = Path(__file__).with_name('record-app-build.py')
    subprocess.run([
        'python3', str(recorder), '--channel', 'stable', '--version', args.version,
        '--platform', args.platform, '--triple', args.triple,
    ], check=True)
    output = root / 'dist' / f'provenance-{args.platform}.json'
    record = json.loads(output.read_text())
    record['recovery'] = {'original_build_run': args.run_id, 'original_job_id': job['databaseId'],
                          'only_original_failure': failures[0], 'archives_rebuilt': False,
                          'original_distribution_commit': run['headSha'], 'original_run_url': run['url']}
    output.write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
