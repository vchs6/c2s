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
        q=first['request'];fp=source_fingerprint(self.root);cfg=first['cost']['configurationDigest']
        with patch('c2s_skill.fact_query.scan_project',side_effect=AssertionError('仓库查询不能重构')):
            second=query_entity_store_v2(self.store,q,fp,cfg)
        self.assertEqual(first['items'],second['items'])

    def test_reused_source_index_retains_parser_metadata(self):
        execute_fact_query(self.root,'modules',self.store)
        result=execute_fact_query(self.root,{'view':'entity','target':{'kind':'DataEntity','name':'Record'},'detail':'self'},self.store)
        fields=[r for r in result['sourceRecords'] if r.get('sourceConstruct',{}).get('syntaxKind')=='field_declaration']
        self.assertTrue(fields)
        self.assertTrue(all(len(r['value']['observations'])==1 for r in fields))

    def test_reused_opaque_source_stays_unresolved(self):
        (self.root/'broken.py').write_text('def broken(:')
        execute_fact_query(self.root,'modules',self.store)
        result=execute_fact_query(self.root,'all-declarations',self.store)
        self.assertTrue(any(r.get('sourceConstruct',{}).get('opaque') for r in result['sourceRecords']))
        self.assertTrue(any(c['status']=='partial' for c in result['coverage']))

    def test_entity_name_and_source_path_disambiguation(self):
        (self.root/'other.py').write_text('def run():\n return 2\n')
        q={'view':'entity','target':{'kind':'ComputationEntity','name':'run','path':'m.py'},'facets':['algorithm'],'detail':'self'}
        result=execute_fact_query(self.root,q,self.store)
        self.assertEqual(1,len(result['items']))
        self.assertTrue(any('pseudocode' in s for s in result['sourceRecords']))

    def test_workspace_members_use_native_metadata_not_all_declarations(self):
        from c2s_skill.acquisition import Fact
        (self.root/'Cargo.toml').write_text('[workspace]\nmembers=["crates/*"]\n')
        member=self.root/'crates/a';member.mkdir(parents=True)
        (member/'Cargo.toml').write_text('[package]\nname="a"\nversion="0.1.0"\n')
        def metadata(root,*,raw_output=None):
            if raw_output is not None:raw_output.append({'metadata':{'packages':[{'name':'a'}]},'toolVersion':'test'})
            source=(root/'Cargo.toml').read_text()
            return [Fact('workspace:a','workspace_member','a','Cargo.toml',0,len(source.encode()),'E1','observation',source,'crates/a/Cargo.toml')],None
        with patch('c2s_skill.fact_query.cargo_workspace_facts',side_effect=metadata) as cargo:
            result=execute_fact_query(self.root,'workspace-members',self.store)
        self.assertEqual(['a'],[i['name'] for i in result['items']]);self.assertEqual(1,cargo.call_count)
        self.assertTrue(result['artifacts'])

    def test_confirmed_empty_module_list_not_not_acquired(self):
        (self.root/'m.py').unlink()
        result=execute_fact_query(self.root,'modules',self.store)
        self.assertEqual([],result['items'])
        self.assertEqual('obtained',result['status']);self.assertTrue(result['complete'])
        self.assertNotIn('TARGET_NOT_ACQUIRED',[d['code'] for d in result['diagnostics']])

    def test_entity_detail_does_not_include_unrelated_diagnostics(self):
        def ent(n):return {'ref':{'kind':'Module','identity':{'authority':'t','domainId':'s','localId':n}},'name':n,'attributes':[]}
        a,b=ent('a'),ent('b')
        model={'entities':[a,b],'sourceRecords':[],'relations':[],'claims':[],'evidence':[],'sourceMappings':[],
               'sourceCoverage':[{'coverageId':'broad','view':'entity','target':{'kind':'all'},'facets':['attributes'],
                'status':'partial','inputFingerprint':'f','configurationDigest':'c','conditions':{},
                'processedPaths':[],'unprocessedPaths':[],
                'diagnostics':[{'code':'PROVISIONAL','entity':a['ref']},{'code':'PROVISIONAL','entity':b['ref']}]}]}
        q=normalize_fact_request({'view':'entity','target':{'kind':'Module','ref':a['ref']},'detail':'self','facets':['attributes']})
        result=project_fact_result(model,q)
        self.assertEqual([{'code':'PROVISIONAL','entity':a['ref']}],result['diagnostics'])
        self.assertEqual(result['diagnostics'],result['coverage'][0]['diagnostics'])

    def test_archive_projection_does_not_invent_algorithm_coverage(self):
        from c2s_skill.semantic_entity_query import query_entity_store_v2
        first=execute_fact_query(self.root,'modules',self.store)
        q=normalize_fact_request({'scopeId':first['request']['scopeId'],'view':'source',
            'target':{'kind':'function','name':'run'},'facets':['algorithm'],'detail':'self'})
        result=query_entity_store_v2(self.store,q,first['cost']['inputFingerprint'],first['cost']['configurationDigest'])
        self.assertFalse(result['complete'])
        self.assertIn('FACET_NOT_ACQUIRED',[d['code'] for d in result['diagnostics']])

    def test_legacy_source_selectors_keep_their_information(self):
        (self.root/'m.py').write_text('import os\nVALUE=3\ndef run(x):\n "documentation"\n y=x+1\n return y\n')
        imports=execute_fact_query(self.root,'imports',self.store)
        self.assertEqual(['os'],[r['name'] for r in imports['items']])
        constants=execute_fact_query(self.root,'constants',self.store)
        self.assertIn('VALUE',[r['name'] for r in constants['items']])
        self.assertTrue(all(r.get('sourceConstruct',{}).get('syntaxKind') in {'assignment_binding','constant_declaration','static_declaration'} for r in constants['items']))
        bindings=execute_fact_query(self.root,'local-bindings',self.store)
        self.assertEqual(['y'],[r['name'] for r in bindings['items']])
        docs=execute_fact_query(self.root,'behavior-contracts',self.store)
        self.assertTrue(any('documentation' in json.dumps(r) for r in docs['items']))
        structure=execute_fact_query(self.root,'algorithm-structure',self.store)
        self.assertEqual(1,len(structure['items']));self.assertIn('algorithm',structure['items'][0])

    def test_members_selector_returns_direct_members_only(self):
        (self.root/'m.py').write_text('class Record:\n key: str\n def get(self):\n  local=1\n  return self.key\n')
        result=execute_fact_query(self.root,'members:Record',self.store)
        self.assertEqual({'key','get'},{i['name'] for i in result['items']})
        self.assertNotIn('local',[i['name'] for i in result['items']])
