"""覆盖口径、重复失败、缺引用和连接生命周期的审核反例。"""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from c2s_skill.fact_query import execute_fact_query,project_fact_result
from c2s_skill.semantic_store import SemanticEntityStore
from c2s_skill.store import QueryResultCache

class ReviewCorrectnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);base=Path(self.tmp.name)
        self.root=base/'p';self.root.mkdir();(self.root/'m.py').write_text('def run():\n return 1\n')
        self.store=SemanticEntityStore(base/'facts.sqlite')
    def model(self,result):
        return self.store.read_request(result['request']['scopeId'],result['request'],result['cost']['inputFingerprint'],result['cost']['configurationDigest'])['model']
    def test_non_source_paths_do_not_invalidate_module_coverage(self):
        for name in ('README.md','data.json','notes.txt'):(self.root/name).write_text('{}')
        r=execute_fact_query(self.root,'modules',self.store)
        self.assertTrue(r['complete']);self.assertEqual([],r['coverage'][0]['unprocessedPaths'])
        self.assertEqual({'README.md','data.json','notes.txt'},set(r['coverage'][0]['outOfScopePaths']))
    def test_retryable_effective_coverage_and_runs_do_not_grow(self):
        q={'target':{'kind':'function','name':'run'},'facets':['relations']}
        for _ in range(12):
            r=execute_fact_query(self.root,q,self.store);m=self.model(r)
            self.assertEqual(1,len(r['coverage']));self.assertEqual(1,len(m['sourceCoverage']))
            self.assertEqual(1,len(m['acquisitionRuns']))
        with self.store._connect() as c:self.assertEqual(12,c.execute('SELECT count(*) FROM semantic_entity_v2_operations').fetchone()[0])
    def test_retry_recovery_replaces_old_gap(self):
        q={'target':{'kind':'function','name':'run'},'facets':['relations']}
        execute_fact_query(self.root,q,self.store)
        raw={'status':'ok','pattern':'callees_of','target':'m.py::run','result_count':0,'results_omitted':0,'results':[],'edges':[]}
        r=execute_fact_query(self.root,q,self.store,tool_runner=lambda *a:{'response':raw,'toolVersion':'2.3.9'})
        self.assertNotIn('RELATIONS_NOT_ACQUIRED',[d['code'] for d in r['diagnostics']]);self.assertEqual(1,len(r['coverage']))
        self.assertTrue(r['artifacts'])
    def test_projection_reports_missing_references(self):
        r=execute_fact_query(self.root,'function:run',self.store);m=self.model(r)
        rec=next(s for s in m['sourceRecords'] if 'algorithm' in s)
        rec['algorithm']['evidence_refs'].append('missing:evidence')
        rec['value']['observations'].append({'artifactId':'missing:artifact'})
        p=project_fact_result(m,r['request']);codes={d['code'] for d in p['diagnostics']}
        self.assertIn('EVIDENCE_REFERENCE_MISSING',codes);self.assertIn('ARTIFACT_REFERENCE_MISSING',codes);self.assertFalse(p['complete'])
    def test_store_and_cache_connections_close_after_exit(self):
        for obj in (self.store,QueryResultCache(Path(self.tmp.name)/'cache.sqlite')):
            with obj._connect() as c:c.execute('SELECT 1')
            with self.assertRaises(sqlite3.ProgrammingError):c.execute('SELECT 1')
    def test_connection_closes_and_transaction_rolls_back_on_error(self):
        with self.store._connect() as c:c.execute('CREATE TABLE checkpoint(x)')
        try:
            with self.store._connect() as c:
                c.execute('INSERT INTO checkpoint VALUES(1)');raise RuntimeError('故意中断')
        except RuntimeError:pass
        with self.assertRaises(sqlite3.ProgrammingError):c.execute('SELECT 1')
        with self.store._connect() as again:self.assertEqual(0,again.execute('SELECT count(*) FROM checkpoint').fetchone()[0])
