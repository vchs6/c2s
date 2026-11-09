"""分发完整性、可移植运行及安装事务的行为测试。"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.codesemantics_release'),'缺少产出构建/安装器')
        from scripts.codesemantics_release import build_bundle,install_bundle,validate_bundle,default_target
        return build_bundle,install_bundle,validate_bundle,default_target
    def bundle(self):
        build,*_=self.api();target=self.base/'bundle';build(ROOT,target);return target
    def test_bundle_is_self_contained_and_clean(self):
        bundle=self.bundle();*_,validate,_=self.api()
        manifest=validate(bundle)
        self.assertEqual('codesemantics',manifest['name'])
        self.assertTrue((bundle/'SKILL.md').is_file())
        self.assertFalse((bundle/'runtime/skill/contracts/semantic-entity-query.schema.json').exists())
        for name in manifest['files']:
            text=(bundle/name).read_text()
            self.assertNotRegex(name+'\n'+text,r'(?i)c2s|\bddd\b|非DDD|历史|遗留|版本沿革|旧版|legacy')
            self.assertNotIn('/tests/',name)
        project=self.base/'project';project.mkdir();(project/'m.py').write_text('def run():\n return 1\n')
        result=subprocess.run([sys.executable,str(bundle/'scripts/codesemantics.py'),'query','--root',str(project),'--select','modules'],cwd=self.base,capture_output=True,text=True)
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertEqual(1,len(json.loads(result.stdout)['items']))
        validate(bundle)  # 正常运行不能破坏已校验的分发目录
    def test_explicit_target_installs_and_default_refuses_overwrite(self):
        bundle=self.bundle();_,install,*_=self.api();target=self.base/'skills/codesemantics'
        install(bundle,target)
        self.assertTrue((target/'SKILL.md').is_file())
        with self.assertRaises(FileExistsError):install(bundle,target)
        self.assertTrue((target/'SKILL.md').is_file())
    def test_modified_payload_is_rejected_before_target_write(self):
        bundle=self.bundle();_,install,*_=self.api();(bundle/'README.md').write_text('损坏的载荷')
        target=self.base/'skills/codesemantics'
        with self.assertRaises(ValueError):install(bundle,target)
        self.assertFalse(target.exists())
    def test_zip_traversal_and_symlink_are_rejected(self):
        self.api()
        from scripts.codesemantics_release import install_bundle
        for name,mode in (('codesemantics/../../outside',0o100644),('codesemantics/evil',0o120777)):
            archive=self.base/'bad.zip'
            with zipfile.ZipFile(archive,'w') as z:
                info=zipfile.ZipInfo(name);info.external_attr=mode<<16;z.writestr(info,'outside')
            with self.assertRaises(ValueError):install_bundle(archive,self.base/'installed')
            self.assertFalse((self.base/'outside').exists())
            self.assertFalse((self.base/'installed').exists())
    def test_failed_environment_setup_rolls_back_owned_target(self):
        bundle=self.bundle();_,install,*_=self.api();target=self.base/'installed';install(bundle,target)
        before=(target/'SKILL.md').read_bytes()
        def fail(path):raise RuntimeError('安装中断')
        with self.assertRaises(RuntimeError):install(bundle,target,replace=True,prepare=fail)
        self.assertEqual(before,(target/'SKILL.md').read_bytes())
        self.assertEqual([],list(self.base.glob('.codesemantics-*')))
    def test_unrecognized_assistant_requires_an_explicit_path(self):
        *_,defaults=self.api()
        for assistant in ('atomcode','qcode'):
            with self.assertRaises(ValueError):defaults(assistant,'user',self.base,self.base)
        self.assertEqual(self.base/'.codeartsdoer/skills/codesemantics',defaults('codearts','user',self.base,self.base))
    def test_standalone_archive_installer_works_from_another_directory(self):
        bundle=self.bundle();archive=self.base/'codesemantics.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for p in bundle.rglob('*'):
                if p.is_file():z.write(p,'codesemantics/'+p.relative_to(bundle).as_posix())
        target=self.base/'portable/codesemantics'
        result=subprocess.run([sys.executable,str(bundle/'install.py'),'--archive',str(archive),'--target',str(target),'--no-runtime'],cwd=self.base,capture_output=True,text=True)
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertTrue((target/'SKILL.md').is_file())

    def test_codex_directories_follow_public_conventions_and_explicit_home(self):
        *_,defaults=self.api()
        with patch('scripts.codesemantics_release.os.environ',{}):
            self.assertEqual(self.base/'.agents/skills/codesemantics',defaults('codex','user',self.base,self.base))
            self.assertEqual(self.base/'.agents/skills/codesemantics',defaults('codex','project',self.base,self.base))
        with patch('scripts.codesemantics_release.os.environ',{'CODEX_HOME':str(self.base/'configured')}):
            self.assertEqual(self.base/'configured/skills/codesemantics',defaults('codex','user',self.base,self.base))

    def test_malformed_manifest_and_portable_device_paths_are_rejected(self):
        bundle=self.bundle();_,install,*_=self.api()
        (bundle/'manifest.json').write_text('[]')
        with self.assertRaises(ValueError):install(bundle,self.base/'target')
        from scripts.codesemantics_release import _relative
        for name in ('NUL','runtime/CON.txt','scripts/COM1.py','scripts/name.','scripts/name '):
            with self.subTest(name=name),self.assertRaises(ValueError):_relative(name)
