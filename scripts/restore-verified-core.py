#!/usr/bin/env python3
"""Restore one signed Core from a previously verified candidate without rebuilding it."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import shutil


def restore(source, destination, expected_commit, target):
    executable = 'eos-core.exe' if 'windows' in target else 'eos-core'
    names = {executable, 'manifest.json'}
    if {path.name for path in source.iterdir()} != names or any(not (source/name).is_file() or (source/name).is_symlink() for name in names):
        raise ValueError('Recovery artifact must contain only the expected regular files')
    manifest = json.loads((source/'manifest.json').read_text())
    if (manifest.get('source_commit'), manifest.get('target'), manifest.get('binary')) != (expected_commit, target, executable):
        raise ValueError('Recovery Core does not match the frozen source or platform')
    if manifest.get('sha256') != 'sha256:'+hashlib.sha256((source/executable).read_bytes()).hexdigest():
        raise ValueError('Recovery Core checksum differs from its signed manifest')
    signature = manifest.get('signature', '').removeprefix('ed25519:')
    if manifest.get('signature_algorithm') != 'ed25519' or len(base64.b64decode(signature, validate=True)) != 64:
        raise ValueError('Recovery Core requires a complete Ed25519 signature')
    destination.mkdir(parents=True, exist_ok=True)
    if any(path.name not in names for path in destination.iterdir()):
        raise ValueError('Recovery destination contains unexpected files')
    for name in names:
        shutil.copy2(source/name, destination/name)
    (destination/executable).chmod(0o755)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--expected-commit',required=True);parser.add_argument('--target',required=True)
    args=parser.parse_args();restore(args.source,args.destination,args.expected_commit,args.target)
