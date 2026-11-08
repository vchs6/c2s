"""规范请求保留来源视图和实体详情边界。"""
import unittest
from c2s_skill.fact_request import normalize_fact_request

class FactRequestTests(unittest.TestCase):
    def test_self_detail_includes_all_own_attributes(self):
        q=normalize_fact_request({'view':'entity','target':{'kind':'DataEntity','name':'Record'},
                                  'detail':'self','facets':['relations']})
        self.assertIn('attributes',q['facets']);self.assertEqual(0,q['expandDepth'])
    def test_function_legacy_selector_is_implementation_view(self):
        q=normalize_fact_request('function:calculate')
        self.assertEqual('source',q['view']);self.assertEqual('calculate',q['target']['name'])
        self.assertIn('algorithm',q['facets'])
    def test_invalid_query_rejected(self):
        for q in ['do anything',{'target':{'kind':'unknown'}},{'expandDepth':9},{'facets':['invent']}]:
            with self.assertRaises(ValueError):normalize_fact_request(q)

    def test_legacy_source_selectors_have_v2_views(self):
        for selector in ['imports','constants','local-bindings','behavior-contracts','algorithm-structure']:
            self.assertEqual('source',normalize_fact_request(selector)['view'])

    def test_fixed_chinese_request_has_source_view(self):
        self.assertEqual('classes',normalize_fact_request('有哪些类')['conditions']['legacySelector'])
    def test_reference_shape_matches_view_and_facets_are_strings(self):
        for q in [{'view':'entity','target':{'kind':'all','ref':{'recordId':'source'}}},
                  {'view':'source','target':{'kind':'all','ref':{'identity':{}}}},
                  {'facets':[{'bad':True}]}]:
            with self.assertRaises(ValueError):normalize_fact_request(q)
