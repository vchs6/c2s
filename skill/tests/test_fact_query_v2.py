"""统一查询必须使用持久事实和真实缺口，不靠隐式全仓重建。"""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from c2s_skill.fact_query import execute_fact_query, project_fact_result, render_fact_result
from c2s_skill.semantic_store import SemanticEntityStore
from c2s_skill.store import QueryResultCache
from c2s_skill.fact_request import normalize_fact_request
from c2s_skill.inventory import source_fingerprint
from c2s_skill.acquisition import analysis_profile_digest

class FactQueryV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);base=Path(self.tmp.name)
        self.root=base/'project';self.root.mkdir()
        (self.root/'m.py').write_text('class Record:\n    key: str\n\ndef run(x):\n    return x+1\n')
        self.store=SemanticEntityStore(base/'store.sqlite');self.cache=QueryResultCache(base/'cache.sqlite')
    def test_stored_algorithm_query_no_reconstruction(self):
        first=execute_fact_query(self.root,'function:run',self.store)
        self.assertTrue(first['items']);self.assertTrue(any('pseudocode' in r for r in first['sourceRecords']))
        with patch('c2s_skill.fact_query.scan_project',side_effect=AssertionError('重复解析')):
            second=execute_fact_query(self.root,'function:run',self.store)
        self.assertEqual(first['items'],second['items'])
        self.assertEqual('reused',second['persistence']['status'])
    def test_unmapped_module_returned(self):
        result=execute_fact_query(self.root,'modules',self.store)
        self.assertEqual(['m.py'],[i['path'] for i in result['items']])
    def test_own_attributes_not_depth_limited(self):
        result=execute_fact_query(self.root,{'view':'entity','target':{'kind':'DataEntity','name':'Record'},'detail':'self','expandDepth':0},self.store)
        self.assertEqual('key',result['items'][0]['attributes'][0]['name'])
    def test_cycle_depth_eight_stops(self):
        q=normalize_fact_request({'view':'entity','target':{'kind':'all','name':'a'},'detail':'self','expandDepth':8})
        def ent(n):return {'ref':{'kind':'Module','identity':{'authority':'test','domainId':'s','localId':n}},'name':n,'attributes':[]}
        a,b=ent('a'),ent('b')
        model={'entities':[a,b],'relations':[{'subject':a['ref'],'target':b['ref'],'predicate':'contains','relationId':'ab','evidenceIds':[]},
                {'subject':b['ref'],'target':a['ref'],'predicate':'contains','relationId':'ba','evidenceIds':[]}],
                'sourceRecords':[],'claims':[],'evidence':[],'sourceCoverage':[],'sourceMappings':[]}
        result=project_fact_result(model,q)
        self.assertIn('ENTITY_RELATION_CYCLE',[d['code'] for d in result['diagnostics']])
        self.assertEqual(2,len(result['items']))
    def test_json_markdown_same_ids_and_gaps(self):
        result=execute_fact_query(self.root,'function:run',self.store)
        markdown=render_fact_result(result,'markdown');encoded=render_fact_result(result,'json')
        self.assertEqual(result,json.loads(encoded))
        for rec in result['sourceRecords']:self.assertIn(rec['recordId'],markdown)
        for diag in result['diagnostics']:self.assertIn(diag['code'],markdown)
    def test_save_error_preserves_facts(self):
        with patch.object(self.store,'commit_request',side_effect=sqlite3.OperationalError('disk failure')):
            result=execute_fact_query(self.root,'function:run',self.store)
        self.assertTrue(result['items']);self.assertEqual('failed',result['persistence']['status'])
    def test_target_not_found_vs_not_acquired(self):
        result=execute_fact_query(self.root,'function:missing',self.store)
        self.assertFalse(result['items']);self.assertIn('SOURCE_TARGET_NOT_FOUND',[d['code'] for d in result['diagnostics']])
        (self.root/'broken.py').write_text('def missing(:')
        result=execute_fact_query(self.root,'function:missing',self.store)
        self.assertIn('TARGET_NOT_ACQUIRED',[d['code'] for d in result['diagnostics']])
    def test_v1_cache_never_hits_v2(self):
        q=normalize_fact_request('modules');fp=source_fingerprint(self.root);cfg=analysis_profile_digest()
        result=execute_fact_query(self.root,q,None)
        self.cache.save_v2(self.root,q,fp,cfg,result)
        self.assertIsNone(self.cache.load_v2(self.root,{**q,'profile':'v1'},fp,cfg))
    def test_normalized_request_profile_cache_key(self):
        q=normalize_fact_request('modules');fp=source_fingerprint(self.root);cfg=analysis_profile_digest()
        result=execute_fact_query(self.root,q,None)
        self.cache.save_v2(self.root,q,fp,cfg,result)
        self.assertEqual(result,self.cache.load_v2(self.root,q,fp,cfg))
    def test_input_config_change_cache_miss(self):
        q=normalize_fact_request('modules');fp=source_fingerprint(self.root);cfg=analysis_profile_digest()
        result=execute_fact_query(self.root,q,None);self.cache.save_v2(self.root,q,fp,cfg,result)
        self.assertIsNone(self.cache.load_v2(self.root,q,fp,'changed'))
        self.assertIsNone(self.cache.load_v2(self.root,q,'changed',cfg))
    def test_cold_organization_skips_implementation_fact_construction(self):
        from c2s_skill.acquisition import _make_fact
        seen=[]
        def record(*args,**kw):seen.append(args[2]);return _make_fact(*args,**kw)
        with patch('c2s_skill.acquisition._make_fact',side_effect=record):execute_fact_query(self.root,'modules',self.store)
        self.assertNotIn('algorithm_step',seen);self.assertNotIn('local_binding',seen)

    def test_persisted_result_cache_hit_preserves_valid_profile(self):
        first=execute_fact_query(self.root,'function:run',self.store,cache=self.cache)
        self.assertEqual('saved',first['persistence']['status'])
        with patch('c2s_skill.fact_query.scan_project',side_effect=AssertionError('缓存命中不应解析')):
            second=execute_fact_query(self.root,'function:run',self.store,cache=self.cache)
        self.assertEqual('cache_hit',second['persistence']['status'])

    def test_explicit_graph_runner_preserves_raw_artifact_and_partial_state(self):
        raw={'status':'ok','pattern':'callees_of','target':'m.py::run','result_count':0,
             'results_omitted':0,'results':[],'edges':[]}
        def runner(tool_id,q):return {'response':raw,'toolVersion':'2.3.9'}
        q={'view':'source','target':{'kind':'function','name':'run'},'facets':['implementation','relations']}
        result=execute_fact_query(self.root,q,self.store,tool_runner=runner)
        self.assertTrue(any(a['payload']==raw for a in result['artifacts']))
        self.assertIn('GRAPH_INDEX_FRESHNESS_UNVERIFIED',[d['code'] for d in result['diagnostics']])

    def test_entity_ref_algorithm_uses_existing_mapping(self):
        first=execute_fact_query(self.root,{'view':'entity','target':{'kind':'ComputationEntity','name':'run'},'facets':['attributes'],'detail':'self'},self.store)
        ref=first['items'][0]['ref']
        second=execute_fact_query(self.root,{'view':'entity','target':{'kind':'ComputationEntity','ref':ref},'facets':['algorithm'],'detail':'self'},self.store)
        self.assertTrue(any('pseudocode' in s for s in second['sourceRecords']))

    def test_public_archive_query_never_reconstructs(self):
        from c2s_skill.semantic_entity_query import query_entity_store_v2
        from c2s_skill.query import query_project_v2
        first=query_project_v2(self.root,'function:run',self.store)
        q=first['request'];fp=source_fingerprint(self.root);cfg=analysis_profile_digest()
        with patch('c2s_skill.fact_query.scan_project',side_effect=AssertionError('仓库查询不能重构')):
            second=query_entity_store_v2(self.store,q,fp,cfg)
        self.assertEqual(first['items'],second['items'])
