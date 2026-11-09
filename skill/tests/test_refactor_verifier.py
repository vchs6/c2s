"""集成验证器必须识别丢记录和输入变化，不把图数量当语义正确性。"""
import sys
import tempfile
import unittest
from pathlib import Path
from copy import deepcopy
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from verify_source_fact_refactor import verify_published_model
from codesemantics.fact_query import execute_fact_query, project_fact_result, prepare_fact_projection_index
from codesemantics.semantic_store import SemanticEntityStore
from codesemantics.acquisition import analysis_profile_digest
from codesemantics.inventory import source_fingerprint
from codesemantics.fact_request import normalize_fact_request

class RefactorVerifierTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);base=Path(self.tmp.name)
        self.root=base/'p';self.root.mkdir();(self.root/'m.py').write_text('def run(x):\n return x+1\n')
        store=SemanticEntityStore(base/'v2.sqlite')
        response=execute_fact_query(self.root,'all-declarations',store)
        self.fp=source_fingerprint(self.root)
        self.model=store.read_request(response['request']['scopeId'],response['request'],self.fp,response['cost']['configurationDigest'])['model']
    def test_verifier_detects_missing_record(self):
        missing=next(s['recordId'] for s in self.model['sourceRecords'] if s['name']=='run')
        self.model['sourceRecords']=[s for s in self.model['sourceRecords'] if s['recordId']!=missing]
        for run in self.model['acquisitionRuns']:run['sourceRecordIds']=[i for i in run['sourceRecordIds'] if i!=missing]
        result=verify_published_model(self.model,self.root,expected_fingerprint=self.fp)
        self.assertFalse(result['valid'])
        self.assertIn('SOURCE_DECLARATION_MISSING',[d['code'] for d in result['diagnostics']])
    def test_verifier_rejects_changed_source(self):
        (self.root/'m.py').write_text('def changed():\n return 2\n')
        result=verify_published_model(self.model,self.root,expected_fingerprint=self.fp)
        self.assertFalse(result['valid']);self.assertIn('INPUT_CHANGED',[d['code'] for d in result['diagnostics']])
    def test_verifier_does_not_equate_source_with_semantic_coverage(self):
        result=verify_published_model(self.model,self.root,expected_fingerprint=self.fp)
        self.assertTrue(result['valid'],result['diagnostics'])
        self.assertFalse(result['semanticInterpretationComplete'])
        self.assertEqual(1,result['sourceDeclarationsVerified'])
    def test_verifier_checks_evidence_byte_bounds(self):
        self.model['evidence'][0]['endByte']=10000
        result=verify_published_model(self.model,self.root,expected_fingerprint=self.fp)
        self.assertFalse(result['valid']);self.assertIn('SOURCE_SPAN_INVALID',[d['code'] for d in result['diagnostics']])
    def test_projection_index_matches_plain_query(self):
        q=normalize_fact_request('all-declarations')
        indexed=project_fact_result(self.model,q,index=prepare_fact_projection_index(self.model))
        self.assertEqual(project_fact_result(self.model,q),indexed)

    def test_verifier_detects_query_claim_loss(self):
        from unittest.mock import patch
        import verify_source_fact_refactor as verifier
        store=SemanticEntityStore(Path(self.tmp.name)/'entities.sqlite')
        response=execute_fact_query(self.root,{'view':'entity','target':{'kind':'all'},'facets':['attributes','relations'],'detail':'list'},store)
        model=store.read_request(response['request']['scopeId'],response['request'],self.fp,response['cost']['configurationDigest'])['model']
        self.assertTrue(model['claims'])
        original=verifier.project_fact_result
        def lose_claims(m,q,**kwargs):
            result=original(m,q,**kwargs)
            if q['view']=='entity':result['claims']=[]
            return result
        with patch.object(verifier,'project_fact_result',side_effect=lose_claims):
            result=verify_published_model(model,self.root,expected_fingerprint=self.fp)
        self.assertFalse(result['valid']);self.assertIn('CLAIM_QUERY_LOSS',[d['code'] for d in result['diagnostics']])

    def test_real_verifier_exercises_target_before_broader_query(self):
        import subprocess
        from verify_source_fact_refactor import run_verification
        (self.root/'m.rs').write_text('enum Color { Red, Blue }\nstruct Data { color: Color }\n')
        (self.root/'Cargo.toml').write_text('[package]\nname="order-check"\nversion="0.1.0"\n[lib]\npath="m.rs"\n')
        subprocess.run(['git','init','-q'],cwd=self.root,check=True)
        subprocess.run(['git','add','.'],cwd=self.root,check=True)
        subprocess.run(['git','-c','user.name=公开验证','-c','user.email=test@example.invalid','commit','-qm','固定公开夹具'],cwd=self.root,check=True)
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=self.root,text=True).strip()
        import os,shutil
        from unittest.mock import patch
        import verify_source_fact_refactor as verifier
        cargo=Path(__file__).resolve().parents[2]/'.local/cargo/bin/cargo'
        local_cargo=cargo.is_file()
        if not local_cargo:
            configured=os.environ.get('CARGO') or shutil.which('cargo')
            if not configured:
                if os.environ.get('C2S_REQUIRE_REAL_PROJECTS')=='1':self.fail('强制集成需要Cargo')
                self.skipTest('此原生工作空间顺序回归需要Cargo')
            cargo=Path(configured)
        original=verifier.execute_fact_query;calls=[]
        def bounded(*args,**kwargs):
            calls.append(args[1])
            if len(calls)>12:raise RuntimeError('验证器重复插入请求导致无界循环')
            return original(*args,**kwargs)
        cargo_env={'CARGO':str(cargo)}
        if local_cargo:cargo_env.update({'RUSTUP_HOME':str(cargo.parents[2]/'rustup'),'CARGO_HOME':str(cargo.parents[1])})
        with patch.dict(os.environ,cargo_env), patch.object(verifier,'execute_fact_query',side_effect=bounded):
            from real_project_support import require_usable_cargo
            require_usable_cargo(self, cargo)
            result=run_verification(self.root,commit,Path(self.tmp.name)/'ordered.sqlite',[])
        self.assertTrue(result['queryOrderChecks'])
        self.assertTrue(all(check['sameAttributes'] for check in result['queryOrderChecks']))
