"""Run the desktop restart contract against the actual packaged Core."""
import argparse
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', required=True)
    parser.add_argument('--triple', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--channel', choices=['stable', 'beta', 'dev'], default='stable')
    args = parser.parse_args()
    temporary = Path(os.environ['RUNNER_TEMP'])
    if args.platform.startswith('windows-'):
        core = temporary / 'EOS-protocol-check/core' / args.triple / 'eos-core.exe'
    elif args.platform.startswith('linux-'):
        core = temporary / 'eos-protocol-data/eos-app/core' / args.triple / 'eos-core'
    else:
        name = {'stable': 'EOS Agent', 'beta': 'EOS Agent Beta', 'dev': 'EOS Agent Dev'}[args.channel]
        core = Path('dist') / f'eos-agent_{args.version.removeprefix("v")}_{args.platform}' / f'{name}.app/Contents/Resources/core' / args.triple / 'eos-core'
    core = core.resolve(strict=True)
    core.with_name('manifest.json').resolve(strict=True)
    tests = '^(' + '|'.join([
        'TestColdStartRestoresSelectedPairBeforeRuntimeLatest',
        'TestDesktopSelectionPersistenceClearsSessionAndPreservesConfig',
        'TestMissingWorkspaceListingRetainsHistoryWithoutCreatingDirectory',
        'TestDesktopWorkspaceRealProcessRestart',
        'TestStdioConfigPathMatchesChildEnvironment',
    ]) + ')$'
    report = Path('dist') / f'workspace-restart-{args.platform}.txt'
    result = subprocess.run(
        ['go', 'test', './internal/app', './internal/adapter', '-run', tests, '-count=1', '-v'],
        env={**os.environ, 'EOS_WORKSPACE_RESTART_CORE': str(core),
             'EOS_MEMORIES_GENERATE': '0', 'EOS_MEMORIES_USE': '0'},
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8',
    )
    report.write_text(result.stdout, encoding='utf-8')
    print(result.stdout, end='')
    if result.returncode:
        raise SystemExit(result.returncode)
    if 'phase empty-verify passed in a fresh shell process' not in result.stdout:
        raise ValueError('The real-process restart contract did not execute all five phases')


if __name__ == '__main__':
    main()
