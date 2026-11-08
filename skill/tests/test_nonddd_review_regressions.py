"""最终只读审核发现的按需查询、补证及故障回归。"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from c2s_skill.fact_query import execute_fact_query
from c2s_skill.semantic_store import SemanticEntityStore
from c2s_skill.store import QueryResultCache
from c2s_skill.__main__ import main

class NonDddReviewRegressions(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        base=Path(self.temp.name);self.root=base/'source';self.root.mkdir()
        (self.root/'pyproject.toml').write_text('[project]\nname="outer"\n')
        self.store=SemanticEntityStore(base/'facts.sqlite')
    def query(self,kind='all',name=None,facets=None):
        target={'kind':kind}
        if name:target['name']=name
        return execute_fact_query(self.root,{'view':'entity','target':target,'facets':facets or ['attributes','relations','implementation','tests'],'detail':'self'},self.store)
    def test_qualified_method_selector(self):
        (self.root/'m.py').write_text('class Owner:\n def run(self):\n  return 1\n')
        result=execute_fact_query(self.root,'function:Owner.run',self.store)
        self.assertEqual(['run'],[i['name'] for i in result['items']]);self.assertIn('algorithm',result['items'][0])
    def test_unobtained_relations_are_explicit(self):
        (self.root/'m.py').write_text('def run():\n return unknown()\n')
        result=execute_fact_query(self.root,{'target':{'kind':'function','name':'run'},'facets':['relations']},self.store)
        self.assertFalse(result['complete']);self.assertTrue(result['diagnostics'])
    def test_targeted_test_association_matches_full_analysis(self):
        (self.root/'m.py').write_text('def run():\n return 1\ndef test_run():\n assert run()==1\n')
        result=self.query('ComputationEntity','run',['tests'])
        self.assertTrue(any(r['predicate']=='verified_by' for item in result['items'] for r in item.get('relations',[])))
    def test_nested_manifest_is_not_owned_by_root_project(self):
        (self.root/'child').mkdir();(self.root/'child/pyproject.toml').write_text('[project]\nname="inner"\n')
        (self.root/'child/m.py').write_text('def inner():\n return 1\n')
        result=self.query();entities={json.dumps(i['ref'],sort_keys=True):i for i in result['items']}
        outer=next(i for i in result['items'] if i['ref']['kind']=='Project' and i['name']=='outer')
        self.assertFalse(any(r['predicate']=='defines' and entities.get(json.dumps(r['target'],sort_keys=True),{}).get('name')=='inner' for r in outer['relations']))
    def test_context_refinement_does_not_conflict(self):
        (self.root/'m.rs').write_text('enum Color { Red, Blue }\nstruct Data { color: Color }\n')
        first=self.query('DataEntity','Data',['attributes'])
        result=self.query('all',None,['attributes'])
        self.assertTrue(first['items']);self.assertTrue(result['items']);self.assertEqual('saved',result['persistence']['status'])
    def test_cache_cannot_hide_failed_save(self):
        (self.root/'m.py').write_text('def run():\n return 1\n')
        cache=QueryResultCache(Path(self.temp.name)/'cache.sqlite')
        with patch.object(self.store,'commit_request',side_effect=OSError('disk full')):
            first=execute_fact_query(self.root,'functions',self.store,cache=cache)
        self.assertEqual('failed',first['persistence']['status'])
        second=execute_fact_query(self.root,'functions',self.store,cache=cache)
        self.assertEqual('saved',second['persistence']['status'])
        self.assertIsNotNone(self.store.read_request(second['request']['scopeId'],second['request'],second['cost']['inputFingerprint'],second['cost']['configurationDigest'])['model'])
    def test_entity_local_id_cli(self):
        (self.root/'m.py').write_text('def run():\n return 1\n')
        result=self.query();entity=next(i for i in result['items'] if i['name']=='run')
        out=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(io.StringIO()):
            main(['entities','--root',str(self.root),'--select','entity:'+entity['ref']['identity']['localId'],'--store',str(self.store.path),'--format','json'])
        self.assertEqual(['run'],[i['name'] for i in json.loads(out.getvalue())['items']])
    def test_grouped_binding_keeps_original_observations(self):
        (self.root/'m.py').write_text('a=b=1\nimport os, sys\n')
        constants=execute_fact_query(self.root,'constants',self.store)
        imports=execute_fact_query(self.root,'imports',self.store)
        self.assertEqual({'a,b'},{i['name'] for i in constants['items']})
        self.assertEqual({'os,sys'},{i['name'] for i in imports['items']})
        self.assertTrue(all(i['value']['observations'] for i in constants['items']+imports['items']))

    def test_same_named_enums_do_not_cross_source_scopes(self):
        (self.root/'a.rs').write_text('enum Color { Red }\nstruct A { color: Color }\n')
        (self.root/'b.rs').write_text('enum Color { Blue }\nstruct B { color: Color }\n')
        result=self.query('all',None,['attributes'])
        attributes={i['name']:i['attributes'] for i in result['items'] if i['ref']['kind']=='DataEntity'}
        self.assertEqual(['Red'],attributes['A'][0]['valueRange']['values'])
        self.assertEqual(['Blue'],attributes['B'][0]['valueRange']['values'])

    def test_cached_result_does_not_replace_new_store_write(self):
        (self.root/'m.py').write_text('def run():\n return 1\n')
        cache=QueryResultCache(Path(self.temp.name)/'cache.sqlite')
        execute_fact_query(self.root,'functions',self.store,cache=cache)
        other=SemanticEntityStore(Path(self.temp.name)/'other.sqlite')
        result=execute_fact_query(self.root,'functions',other,cache=cache)
        self.assertEqual('saved',result['persistence']['status'])
        self.assertIsNotNone(other.read_request(result['request']['scopeId'],result['request'],result['cost']['inputFingerprint'],result['cost']['configurationDigest'])['model'])

    def test_value_range_can_be_completed_but_not_overwritten(self):
        from copy import deepcopy
        from c2s_skill.fact_request import normalize_fact_request
        from c2s_skill.acquisition import scan_project
        from c2s_skill.entity_construction import construct_requested_entities
        (self.root/'m.rs').write_text('enum Color { Red, Blue }\nstruct Data { color: Color }\n')
        q=normalize_fact_request({'scopeId':'review','view':'entity','target':{'kind':'DataEntity','name':'Data'},'facets':['attributes'],'detail':'self'})
        full=construct_requested_entities(self.root,scan_project(self.root),{'request':q,'needs':[{'facet':'attributes'}]})
        partial=deepcopy(full);partial['entities'][0]['attributes'][0]['valueRange']={'kind':'unknown'}
        self.store.commit_request('partial',partial,q)
        completed=self.store.commit_request('completed',full,q)
        self.assertEqual(['Red','Blue'],completed['model']['entities'][0]['attributes'][0]['valueRange']['values'])
        # 后来的不完整观察不能擦掉已取得值域；相矛盾的确定取值必须拒绝。
        again=self.store.commit_request('unknown-again',partial,q)
        self.assertEqual(completed['model']['entities'],again['model']['entities'])
        conflicting=deepcopy(full);conflicting['entities'][0]['attributes'][0]['valueRange']['values']=['Other']
        with self.assertRaises(ValueError):self.store.commit_request('contradiction',conflicting,q)

    def test_full_then_targeted_attributes_agree(self):
        (self.root/'m.rs').write_text('enum Color { Red, Blue }\nstruct Data { color: Color }\n')
        full=self.query('all',None,['attributes'])
        target=self.query('DataEntity','Data',['attributes'])
        original=next(i for i in full['items'] if i['name']=='Data')
        self.assertEqual(original['attributes'],target['items'][0]['attributes'])

    def test_acquisition_receipt_identifies_actual_parsers(self):
        (self.root/'m.py').write_text('def run():\n return 1\n')
        result=execute_fact_query(self.root,'functions',self.store)
        model=self.store.read_request(result['request']['scopeId'],result['request'],result['cost']['inputFingerprint'],result['cost']['configurationDigest'])['model']
        tools=[t for run in model['acquisitionRuns'] for t in run['tools']]
        self.assertTrue(any(t.get('version') and t.get('name')=='python-ast' for t in tools))
