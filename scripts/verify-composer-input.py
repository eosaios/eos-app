"""Exercise the packaged Core input budget with isolated loopback model metadata."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.dont_write_bytecode = True


def packaged_core(args):
    temporary = Path(os.environ['RUNNER_TEMP'])
    if args.platform.startswith('windows-'):
        return temporary / 'EOS-protocol-check/core' / args.triple / 'eos-core.exe'
    if args.platform.startswith('linux-'):
        return temporary / 'eos-protocol-data/eos-app/core' / args.triple / 'eos-core'
    name = {'stable': 'EOS Agent', 'beta': 'EOS Agent Beta', 'dev': 'EOS Agent Dev'}[args.channel]
    return Path('dist') / f'eos-agent_{args.version.removeprefix("v")}_{args.platform}' / f'{name}.app/Contents/Resources/core' / args.triple / 'eos-core'


def verify(core, directory):
    spec = importlib.util.spec_from_file_location('input_probe_rpc', Path('tools/probe-provider-migration.py').resolve())
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    root = directory / 'state'
    workspace = root / 'workspace'
    workspace.mkdir(parents=True)
    os.environ.update(EOS_HOME=str(root / 'home'), EOS_WORKSPACE_ROOT=str(workspace),
                      EOS_MEMORIES_GENERATE='0', EOS_MEMORIES_USE='0',
                      EOS_MODEL_CAPABILITY_CATALOG_URL='fixture://isolated/composer-input')
    posts = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != '/v1/models':
                self.send_error(404)
                return
            raw = json.dumps({'data': [
                {'id': 'composer-small', 'context_window': 8},
                {'id': 'composer-large', 'context_window': 256},
                {'id': 'composer-unknown'},
            ]}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            posts.append(self.path)
            self.send_error(500, 'Oversized input must not reach inference')

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    rpc = migration.Rpc(core, root)
    try:
        saved = rpc.connection(action='save', name='Composer input fixture', provider_id='openai',
                               plan='api', format='openai_chat',
                               api_base=f'http://127.0.0.1:{server.server_port}/v1', api_key='fixture-input-key')
        discovered = rpc.connection(action='discover_models', id=saved['connections'][0]['id'])
        models = {item['model']: item for item in discovered['models']}

        def budget(model, text):
            return rpc.call('model/input_budget', {'model_name': models[model]['name'], 'text': text})

        text = 'hello ' * 8
        exact = budget('composer-small', text.strip())
        assert exact == {'model_name': models['composer-small']['name'], 'estimated_tokens': 8, 'max_input_tokens': 8}, exact
        large = budget('composer-large', text.strip())
        assert large == {**exact, 'model_name': models['composer-large']['name'], 'max_input_tokens': 256}, large
        unknown = budget('composer-unknown', 'hello')
        assert unknown == {'model_name': models['composer-unknown']['name'], 'estimated_tokens': 1, 'max_input_tokens': None}, unknown
        unicode = budget('composer-large', '中文 👩🏽‍💻\nplain text')
        assert 0 < unicode['estimated_tokens'] <= 256
        assert budget('composer-small', '') == {**exact, 'estimated_tokens': 0}
        rpc.call('model/activate', {'name': models['composer-small']['name']})
        session = rpc.call('session/create', {'workspace_root': str(workspace)})
        try:
            rpc.call('turn/start', {'session_id': session['id'], 'input': 'hello ' * 30, 'use_memory': False})
        except AssertionError as error:
            assert '输入内容超过所选模型上限' in str(error), str(error)
        else:
            raise AssertionError('Oversized turn was accepted')
        try:
            rpc.call('insight/refine_input', {'draft': 'hello ' * 30})
        except AssertionError as error:
            assert '输入内容超过所选模型上限' in str(error), str(error)
        else:
            raise AssertionError('Oversized AI polish input was accepted')
        assert rpc.call('session/messages/load', {'session_id': session['id']}) == []
        assert posts == [], posts
        return {'passed': True, 'exact_boundary': exact, 'selected_larger_model': large,
                'unknown_limit_explicit': unknown['max_input_tokens'] is None,
                'unicode_estimated_tokens': unicode['estimated_tokens'],
                'oversized_turn_rejected_before_persistence': True, 'inference_requests': len(posts),
                'oversized_polish_rejected_before_inference': True,
                'no_cloud_requests': True}
    finally:
        rpc.close()
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', required=True)
    parser.add_argument('--triple', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--channel', choices=['stable', 'beta', 'dev'], default='stable')
    parser.add_argument('--core', type=Path, help='Explicit Core for local verifier testing')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    core = (args.core or packaged_core(args)).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix='composer-input-') as temporary:
        result = verify(core, Path(temporary))
    report = args.report or Path('dist') / f'composer-input-{args.platform}.json'
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
