"""计划只对请求缺口分配工作，不因缓存不足构造全仓语义。"""
import unittest
from c2s_skill.fact_request import normalize_fact_request
from c2s_skill.construction_plan import plan_fact_request

class ConstructionPlanTests(unittest.TestCase):
    def setUp(self):
        self.q=normalize_fact_request('function:run')
        self.records=[{'recordId':'a','kind':'declaration','name':'run','path':'a.py',
                       'sourceConstruct':{'syntaxKind':'function_declaration'}}]
        self.inv=[{'path':'a.py','kind':'file'},{'path':'unrelated.py','kind':'file'}]
    def test_ambiguous_name_returns_candidates(self):
        records=self.records+[dict(self.records[0],recordId='b',path='b.py')]
        p=plan_fact_request(self.q,{'sourceRecords':records},self.inv)
        self.assertEqual([],p['needs']);self.assertEqual('AMBIGUOUS_TARGET',p['diagnostics'][0]['code'])
        self.assertEqual(2,len(p['candidates']))
    def test_first_algorithm_request_targets_one_function(self):
        p=plan_fact_request(self.q,{'sourceRecords':self.records},self.inv)
        self.assertEqual(['a.py'],p['sourcePaths'])
        self.assertEqual({'run'},{n['target']['name'] for n in p['needs']})
        self.assertTrue(all(n['reason'] for n in p['needs']))
    def test_repeat_request_only_plans_missing_facet(self):
        p=plan_fact_request(self.q,{'sourceRecords':self.records,'reusedFacets':['implementation']},self.inv)
        self.assertEqual(['algorithm'],[n['facet'] for n in p['needs']])
    def test_tool_unavailable_is_gap(self):
        p=plan_fact_request(self.q,{'sourceRecords':self.records,'availableTools':[]},self.inv)
        self.assertTrue(any(d['code']=='TOOL_UNAVAILABLE' for d in p['diagnostics']))
        self.assertNotIn('algorithm',[n['facet'] for n in p['needs']])
    def test_empty_algorithm_target_does_not_schedule_all_algorithms(self):
        p=plan_fact_request(self.q,{},self.inv)
        self.assertEqual(['locate'],[n['facet'] for n in p['needs']])
        self.assertIn('TARGET_NOT_LOCATED',p['stopReasons'])
