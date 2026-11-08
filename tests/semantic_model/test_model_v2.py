"""v2来源、解释与兼容边界的公开测试。"""
import copy
import unittest
from test_entity_model_contract import valid_entity_model
from c2s_semantic_contract.validation import validate_semantic_entity_model_v2


def model_v2():
    m = valid_entity_model()
    m.update(profile='semantic-entity-model-2', version='2.0.0', sourceRecords=[],
             acquisitionRuns=[], sourceCoverage=[], artifacts=[])
    return m


class ModelV2Tests(unittest.TestCase):
    def test_source_entity_identity_separated(self):
        m = model_v2()
        m['sourceRecords'] = [{'recordId':'s1','kind':'source_module','name':'sample',
            'path':'sample.py','sourceConstructIds':[], 'parentRecordIds':[],
            'relatedRecords':[], 'evidenceIds':['ev-1'], 'status':'obtained'}]
        self.assertTrue(validate_semantic_entity_model_v2(m)['valid'])
        m['relations'][0]['target'] = {'recordId':'s1'}
        self.assertFalse(validate_semantic_entity_model_v2(m)['valid'])

    def test_missing_premise_rejected(self):
        m = model_v2()
        m['claims'] = [{'claimId':'c1','subject':m['entities'][0]['ref'], 'predicate':'purpose',
                        'value':'解释', 'evidenceIds':['ev-1'], 'claimStatus':'provisional',
                        'origin':'derived_analysis', 'method':'rule', 'premiseIds':['missing']}]
        self.assertFalse(validate_semantic_entity_model_v2(m)['valid'])
        m['claims'][0]['premiseIds'] = ['ev-1']
        self.assertTrue(validate_semantic_entity_model_v2(m)['valid'])

    def test_source_relation_dangling_rejected(self):
        m = model_v2()
        m['sourceRecords'] = [{'recordId':'s1','kind':'source_module','name':'x','path':'x.py',
            'sourceConstructIds':[], 'parentRecordIds':['missing'], 'relatedRecords':[],
            'evidenceIds':['ev-1'], 'status':'obtained'}]
        self.assertFalse(validate_semantic_entity_model_v2(m)['valid'])

    def test_optional_views_not_entity_kind(self):
        m=model_v2()
        for e in m['entities']: e['observationViews']=[]
        self.assertTrue(validate_semantic_entity_model_v2(m)['valid'])
        m['entities'][0]['ref']['kind']='E0'
        self.assertFalse(validate_semantic_entity_model_v2(m)['valid'])

    def test_unclassified_legacy_requires_original_payload(self):
        m=model_v2()
        m['claims']=[{'claimId':'old','subject':m['entities'][0]['ref'],'predicate':'purpose',
            'value':'旧解释','evidenceIds':['ev-1'],'claimStatus':'provisional',
            'origin':'unclassified_legacy'}]
        self.assertFalse(validate_semantic_entity_model_v2(m)['valid'])
        m['claims'][0]['legacyPayloadArtifactId']='old-payload'
        m['artifacts']=[{'artifactId':'old-payload','kind':'legacy_payload','payload':{'old':True}}]
        self.assertTrue(validate_semantic_entity_model_v2(m)['valid'])

    def test_v1_still_valid(self):
        from c2s_semantic_contract.validation import validate_semantic_entity_model
        self.assertTrue(validate_semantic_entity_model(valid_entity_model())['valid'])

    def test_source_path_escape_and_duplicate_ids_rejected(self):
        m=model_v2()
        s={'recordId':'s','kind':'source_module','name':'x','path':'../x.py',
           'sourceConstructIds':[],'parentRecordIds':[],'relatedRecords':[],
           'evidenceIds':[],'status':'obtained'}
        m['sourceRecords']=[s]
        self.assertFalse(validate_semantic_entity_model_v2(m)['valid'])
        s['path']='x.py';m['sourceRecords'].append(copy.deepcopy(s))
        self.assertFalse(validate_semantic_entity_model_v2(m)['valid'])

    def test_request_invalid_target_or_missing_field_rejected(self):
        import json
        from pathlib import Path
        from jsonschema import Draft202012Validator
        schema=json.loads((Path(__file__).resolve().parents[2] / 'skill/contracts/semantic-fact-request-2.schema.json').read_text())
        valid={'profile':'semantic-fact-request-2','scopeId':'s','view':'source',
               'target':{'kind':'module'},'facets':['organization'],'detail':'list',
               'expandDepth':0,'conditions':{}}
        validator=Draft202012Validator(schema)
        self.assertFalse(list(validator.iter_errors(valid)))
        valid['target']['kind']='arbitrary'
        self.assertTrue(list(validator.iter_errors(valid)))
        valid['target']['kind']='module';del valid['facets']
        self.assertTrue(list(validator.iter_errors(valid)))
