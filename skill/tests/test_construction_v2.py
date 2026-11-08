"""请求构造保留解释证据，且不会把语法类别当确定需求。"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from c2s_skill.acquisition import scan_project
from c2s_skill.entity_construction import construct_requested_entities
from c2s_skill.fact_request import normalize_fact_request
from c2s_semantic_contract.validation import validate_semantic_entity_model_v2

class ConstructionV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        (self.root/'sample.py').write_text('class Record:\n    key: str\n\ndef run(x):\n    return x+1\n\ndef other():\n    return 2\n')
        self.scan=scan_project(self.root)
    def build(self,request):
        q=normalize_fact_request(request);q['scopeId']='test'
        return construct_requested_entities(self.root,self.scan,{'request':q,'needs':[{'facet':f,'target':q['target']} for f in q['facets']]})
    def test_class_does_not_confirm_business_requirement(self):
        m=self.build({'view':'entity','target':{'kind':'DataEntity','name':'Record'},'detail':'self'})
        self.assertTrue(m['entities'])
        self.assertTrue(all(c['claimStatus']=='provisional' for c in m['claims']))
        self.assertTrue(all(c['origin']=='derived_analysis' for c in m['claims']))
        self.assertTrue(validate_semantic_entity_model_v2(m)['valid'])
    def test_rule_claim_records_premises(self):
        m=self.build({'view':'entity','target':{'kind':'ComputationEntity','name':'run'}})
        self.assertTrue(all(c['premiseIds'] and c['method'] for c in m['claims']))
    def test_views_derived_from_content_not_kind(self):
        m=self.build({'view':'entity','target':{'kind':'all'}})
        self.assertTrue(all(e['observationViews']==[] for e in m['entities']))
    def test_unmapped_construct_retained(self):
        m=self.build('modules')
        self.assertTrue(any(r['kind']=='source_module' for r in m['sourceRecords']))
    def test_algorithm_not_run_for_attribute_request(self):
        with patch('c2s_skill.algorithm.extract_python_algorithm',side_effect=AssertionError('无关算法')):
            m=self.build({'view':'entity','target':{'kind':'DataEntity','name':'Record'},'facets':['attributes']})
        self.assertTrue(m['entities']);self.assertFalse(any('algorithm' in r for r in m['sourceRecords']))
    def test_attribute_unknown_domain_preserved(self):
        m=self.build({'view':'entity','target':{'kind':'DataEntity','name':'Record'},'detail':'self'})
        self.assertEqual('unknown',m['entities'][0]['attributes'][0]['valueRange']['kind'])
    def test_one_algorithm_not_other_functions(self):
        from c2s_skill.algorithm import extract_python_algorithm
        with patch('c2s_skill.algorithm.extract_python_algorithm',wraps=extract_python_algorithm) as lowering:
            m=self.build('function:run')
        self.assertEqual(1,lowering.call_count)
        self.assertEqual('run',lowering.call_args.args[2])
        self.assertTrue(any('pseudocode' in s for s in m['sourceRecords']))

    def test_entity_algorithm_validated_and_evidence_closed(self):
        m=self.build({'view':'entity','target':{'kind':'ComputationEntity','name':'run'},'facets':['algorithm']})
        result=validate_semantic_entity_model_v2(m)
        self.assertTrue(result['valid'],result['diagnostics'])
        record=next(r for r in m['sourceRecords'] if 'algorithm' in r)
        self.assertLessEqual(set(record['algorithm']['evidence_refs']),{e['evidenceId'] for e in m['evidence']})

    def test_unknown_implementation_type_omitted_not_null(self):
        (self.root/'untyped.py').write_text('class Unknown:\n value = None\n')
        self.scan=scan_project(self.root)
        m=self.build({'view':'entity','target':{'kind':'DataEntity','name':'Unknown'},'detail':'self'})
        result=validate_semantic_entity_model_v2(m)
        self.assertTrue(result['valid'],result['diagnostics'])
        self.assertNotIn('implementationType',m['entities'][0]['attributes'][0])
