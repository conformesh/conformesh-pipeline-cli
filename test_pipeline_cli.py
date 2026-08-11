from __future__ import annotations
import hashlib,tempfile,unittest,zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from conformesh_spike.pipeline_cli import api_url,load_config,provider_metadata,verify

class PipelineCliTests(unittest.TestCase):
 def test_configuration_provider_detection_and_https_requirement(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/"conformesh.yml";path.write_text("schema_version: 1\ngate: strict\nreport_language: es\n")
   self.assertEqual({"schema_version":"1","gate":"strict","report_language":"es"},load_config(str(path)))
  args=SimpleNamespace(repository=None,commit=None,build_id=None,build_url=None,branch=None,tag=None)
  with patch.dict("os.environ",{"TF_BUILD":"True","BUILD_REPOSITORY_NAME":"gateway","BUILD_SOURCEVERSION":"abc","BUILD_BUILDID":"42","BUILD_SOURCEBRANCHNAME":"main","SYSTEM_COLLECTIONURI":"https://dev.azure.com/acme/","SYSTEM_TEAMPROJECT":"Products"},clear=True):metadata=provider_metadata(args)
  self.assertEqual("azure",metadata["provider"]);self.assertEqual("42",metadata["build_id"])
  self.assertEqual("https://conformesh.com",api_url("https://conformesh.com/"))
  with self.assertRaises(SystemExit):api_url("http://conformesh.example")
 def test_offline_snapshot_verification_detects_tampering(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/"snapshot.zip";content=b"evidence";checksum=hashlib.sha256(content).hexdigest()
   with zipfile.ZipFile(path,"w") as archive:archive.writestr("evidence.txt",content);archive.writestr("SHA256SUMS",f"{checksum}  evidence.txt\n")
   self.assertEqual(0,verify(path))
   with zipfile.ZipFile(path,"w") as archive:archive.writestr("evidence.txt",b"altered");archive.writestr("SHA256SUMS",f"{checksum}  evidence.txt\n")
   self.assertEqual(2,verify(path))
