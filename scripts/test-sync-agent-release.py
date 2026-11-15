import importlib.util
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import io
import unittest

spec=importlib.util.spec_from_file_location('sync',Path(__file__).with_name('sync-agent-release.py'))
sync=importlib.util.module_from_spec(spec);spec.loader.exec_module(sync)

class ReleaseValidation(unittest.TestCase):
    def fixture(self, root):
        files={}
        for name,(platform,kind) in sync.expected_files('1.0.19').items():
            data=('fixture-'+name).encode();(root/name).write_bytes(data)
            files[name]={'platform':platform,'kind':kind,'size':len(data),'sha256':sync.digest(data)}
        lock={'version':'1.0.19','app_commit':'a'*40,'files':files}
        raw=json.dumps(lock).encode();(root/'release-lock.json').write_bytes(raw)
        return lock,sync.digest(raw)

    def test_complete_frozen_release_and_reject_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);lock,digest=self.fixture(root)
            self.assertEqual(sync.validate_release(root,'1.0.19',digest),lock)
            with self.assertRaises(ValueError):sync.validate_release(root,'1.0.19','0'*64)
            with self.assertRaises(ValueError):sync.validate_release(root,'1.0.20',digest)
            name=next(iter(lock['files']));(root/name).write_bytes(b'altered')
            with self.assertRaises(ValueError):sync.validate_release(root,'1.0.19',digest)

    def test_reject_extra_assets_even_when_lock_is_rehashed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);lock,_=self.fixture(root);lock['files']['other.exe']={}
            raw=json.dumps(lock).encode();(root/'release-lock.json').write_bytes(raw)
            with self.assertRaises(ValueError):sync.validate_release(root,'1.0.19',sync.digest(raw))

    def test_stable_identity_never_crosses_channels_or_products(self):
        apps=[{'id':index,'app_key':'eos-app','release_channel':'stable','platform':platform} for index,platform in enumerate(sync.PLATFORMS)]
        others=[{**apps[0],'id':100,'release_channel':'beta'},{**apps[1],'id':101,'app_key':'eos-todo'}]
        self.assertEqual(set(sync.stable_apps(apps+others)),set(sync.PLATFORMS))
        for invalid in [apps[:-1],apps+[apps[0]]]:
            with self.assertRaises(ValueError):sync.stable_apps(invalid)

    def test_existing_version_must_match_every_frozen_field(self):
        expected={'application_id':1,'platform':'darwin-arm64','product_version':'1.0.19','commit':'a'*40,'file_size':123,'sha256_hash':'b'*64}
        row={**expected,'quality':'stable','is_active':True,'is_deprecated':False}
        sync.check_version(row,expected)
        for key,value in [('commit','c'*40),('sha256_hash','d'*64),('quality','beta'),('is_deprecated',True),('is_active',False)]:
            with self.subTest(key=key), self.assertRaises(ValueError):sync.check_version({**row,key:value},expected)

    def test_preflight_authenticates_and_reads_without_release_writes(self):
        apps=[{'id':index+1,'app_key':'eos-app','release_channel':'stable','platform':platform,'display_name':'EOS Agent'} for index,platform in enumerate(sync.PLATFORMS)]
        with patch.dict(sync.os.environ,{'EOS_ADMIN_EMAIL':'fixture','EOS_ADMIN_PASSWORD':'fixture'}), patch.object(sync,'request',side_effect=[{'access_token':'fixture-token'},{'applications':apps},{'packages':[]}]) as request, patch.object(sync.sys,'argv',['sync','--operation','preflight','--version','v1.0.19']), patch('sys.stdout',new_callable=io.StringIO) as output:
            sync.main()
            self.assertEqual(request.call_count,3)
            self.assertTrue(all(call.kwargs.get('method') is None for call in request.call_args_list))
            self.assertNotIn('fixture-token',output.getvalue())
            self.assertFalse(json.loads(output.getvalue())['production_writes'])

    def test_failed_promotion_restores_only_already_changed_platforms(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);lock,digest=self.fixture(root);notes=root/'notes.md';notes.write_text('Fixture release')
            apps=[{'id':index+1,'app_key':'eos-app','release_channel':'stable','platform':platform,'display_name':'EOS Agent'} for index,platform in enumerate(sync.PLATFORMS)]
            statuses=[]
            def request(path,token='',payload=None,method=None):
                if path.endswith('/auth/login'):return {'access_token':'fixture-token'}
                if '/applications?' in path:return {'applications':apps}
                if path.endswith('/download/packages'):return {'packages':[]}
                if '/versions?application_id=' in path:
                    app=apps[int(path.rsplit('=',1)[1])-1]
                    item=next(item for item in lock['files'].values() if item['platform']==app['platform'] and item['kind']=='installer')
                    row={'id':100+app['id'],'application_id':app['id'],'platform':app['platform'],'product_version':'1.0.19','commit':'a'*40,'file_size':item['size'],'sha256_hash':item['sha256'],'is_active':True,'is_deprecated':False,'quality':'stable','is_current':False}
                    return [{**row,'id':app['id']*10,'product_version':'1.0.18','is_current':True},row]
                if path.endswith('/versions/status'):
                    statuses.append(payload['version_id'])
                    if payload['version_id']==102:raise RuntimeError('fixture promotion failure')
                    return {'success':True}
                self.fail('Unexpected mutation '+path)
            args=['sync','--operation','sync','--version','v1.0.19','--root',str(root),'--notes',str(notes),'--lock-sha256',digest]
            with patch.dict(sync.os.environ,{'EOS_ADMIN_EMAIL':'fixture','EOS_ADMIN_PASSWORD':'fixture'}),patch.object(sync,'request',side_effect=request),patch.object(sync,'verify_download'),patch.object(sync.sys,'argv',args):
                with self.assertRaisesRegex(RuntimeError,'fixture promotion failure'):sync.main()
            self.assertEqual(statuses,[101,102,10])

if __name__=='__main__':unittest.main()
