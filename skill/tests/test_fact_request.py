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
