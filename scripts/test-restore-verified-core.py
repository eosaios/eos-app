import base64
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('restore',Path(__file__).with_name('restore-verified-core.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class CoreRecovery(unittest.TestCase):
 def fixture(self,root):
  source=root/'source';source.mkdir();(source/'eos-core').write_bytes(b'fixture-core')
  manifest={'source_commit':'a'*40,'target':'aarch64-apple-darwin','binary':'eos-core','sha256':'sha256:'+hashlib.sha256(b'fixture-core').hexdigest(),'signature_algorithm':'ed25519','signature':base64.b64encode(b'0'*64).decode()};(source/'manifest.json').write_text(json.dumps(manifest))
  return source,manifest
 def test_restore_only_exact_frozen_core_and_keep_executable(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);source,_=self.fixture(root);destination=root/'restored';module.restore(source,destination,'a'*40,'aarch64-apple-darwin')
   self.assertEqual((source/'manifest.json').read_bytes(),(destination/'manifest.json').read_bytes());self.assertEqual((destination/'eos-core').stat().st_mode&0o777,0o755)
 def test_reject_changed_source_target_binary_or_signature(self):
  for field,value in [('source_commit','b'*40),('target','x86_64-apple-darwin'),('binary','other'),('sha256','sha256:'+'0'*64),('signature','unsigned-development-placeholder')]:
   with self.subTest(field=field),tempfile.TemporaryDirectory() as directory:
    root=Path(directory);source,manifest=self.fixture(root);manifest[field]=value;(source/'manifest.json').write_text(json.dumps(manifest))
    with self.assertRaises((ValueError,base64.binascii.Error)):module.restore(source,root/'restored','a'*40,'aarch64-apple-darwin')
 def test_reject_extra_files_and_symlinks(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);source,_=self.fixture(root);(source/'extra.pem').write_text('fixture')
   with self.assertRaises(ValueError):module.restore(source,root/'restored','a'*40,'aarch64-apple-darwin')
if __name__=='__main__':unittest.main()
