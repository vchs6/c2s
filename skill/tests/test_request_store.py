"""v2按请求原子提交和复用的公开故障/并发测试。"""
import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from c2s_skill.semantic_store import SemanticEntityStore
from c2s_skill.acquisition import scan_project
from c2s_skill.entity_construction import construct_requested_entities
from c2s_skill.fact_request import normalize_fact_request

class RequestStoreTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);base=Path(self.t.name)
        self.root=base/'project';self.root.mkdir();(self.root/'m.py').write_text('def run():\n return 1\n')
        self.q=normalize_fact_request('modules');self.q['scopeId']='s'
        self.model=construct_requested_entities(self.root,scan_project(self.root),{'request':self.q,'needs':[{'facet':'organization'}]})
        self.store=SemanticEntityStore(base/'facts.sqlite')
        self.fp=self.model['sourceCoverage'][0]['inputFingerprint'];self.config=self.model['sourceCoverage'][0]['configurationDigest']
    def test_duplicate_operation_idempotent(self):
        a=self.store.commit_request('op',self.model,self.q);b=self.store.commit_request('op',self.model,self.q)
        self.assertEqual(a['generation'],b['generation'])
        self.assertEqual(a['model'],b['model'])
    def test_operation_id_different_payload_rejected(self):
        self.store.commit_request('op',self.model,self.q)
        self.model['evidence'].append({'evidenceId':'extra','source':'test','description':'extra'})
        with self.assertRaises(ValueError):self.store.commit_request('op',self.model,self.q)
    def test_concurrent_missing_facets_no_lost_update(self):
        from copy import deepcopy
        def publish(i):
            m=deepcopy(self.model);m['evidence'].append({'evidenceId':f'extra{i}','source':'test','description':'补证'})
            return self.store.commit_request(str(i),m,self.q)
        with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(publish,range(8)))
        result=self.store.read_request('s',self.q,self.fp,self.config)
        self.assertEqual(8,len([e for e in result['model']['evidence'] if e['evidenceId'].startswith('extra')]))
    def test_cancel_keeps_unfinished_gap(self):
        self.model['acquisitionRuns']=[{'runId':'cancel','inputFingerprint':self.fp,
            'configurationDigest':self.config,'status':'cancelled','tools':[],
            'sourceRecordIds':[],'evidenceIds':[],'artifactIds':[]}]
        self.store.commit_request('op',self.model,self.q)
        self.assertEqual([],self.store.read_request('s',self.q,self.fp,self.config)['reusedFacets'])
    def test_readback_without_analysis(self):
        self.store.commit_request('op',self.model,self.q)
        result=self.store.read_request('s',self.q,self.fp,self.config)
        self.assertEqual(['organization'],result['reusedFacets'])
        self.assertTrue(result['model']['sourceRecords'])
    def test_input_changed_not_reused(self):
        self.store.commit_request('op',self.model,self.q)
        result=self.store.read_request('s',self.q,'different',self.config)
        self.assertFalse(result['reusedFacets']);self.assertEqual('INPUT_CHANGED',result['diagnostics'][0]['code'])
    def test_invalid_reference_atomic_rejection(self):
        self.model['sourceRecords'][0]['parentRecordIds']=['missing']
        with self.assertRaises(ValueError):self.store.commit_request('op',self.model,self.q)
        self.assertIsNone(self.store.read_request('s',self.q,self.fp,self.config)['model'])

    def test_storage_failure_rolls_back_registry_and_data(self):
        import sqlite3
        q=normalize_fact_request({'view':'entity','target':{'kind':'ComputationEntity','name':'run'}})
        q['scopeId']='s'
        m=construct_requested_entities(self.root,scan_project(self.root),{'request':q,'needs':[{'facet':'attributes'}]})
        self.store.read_request('s',q,self.fp,self.config)
        with self.store._connect() as conn:
            conn.execute("CREATE TRIGGER reject_v2 BEFORE INSERT ON semantic_entity_v2_archives BEGIN SELECT RAISE(ABORT,'failure injection'); END")
        with self.assertRaises(sqlite3.Error):self.store.commit_request('fail',m,q)
        with self.store._connect() as conn:
            self.assertEqual(0,conn.execute('SELECT COUNT(*) FROM semantic_entity_registry').fetchone()[0])
            self.assertEqual(0,conn.execute('SELECT COUNT(*) FROM semantic_entity_v2_operations').fetchone()[0])
