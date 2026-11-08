"""图工具检索输出只产生带边界的候选，不证明绑定或枚举完整。"""
import tempfile
import unittest
from pathlib import Path
from c2s_skill.codegraph_adapter import parse_codegraph_response

class CodeGraphAdapterTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name)
        (self.root/'m.py').write_text('def f():\n return 1\n')
        self.node={'id':'upstream:1','name':'f','kind':'function','filePath':'m.py','startLine':1,'endLine':2}
    def test_cli_array_parsed(self):
        r=parse_codegraph_response([{'node':self.node,'score':99}],self.root,'query')
        self.assertEqual('f',r['candidates'][0]['name']);self.assertEqual('m.py',r['candidates'][0]['path'])
    def test_path_escape_rejected(self):
        self.node['filePath']='../escape.py'
        r=parse_codegraph_response([{'node':self.node}],self.root,'query')
        self.assertEqual([],r['candidates']);self.assertIn('GRAPH_PATH_INVALID',[x['code'] for x in r['diagnostics']])
    def test_unbounded_search_not_full_enumeration(self):
        r=parse_codegraph_response([{'node':self.node}],self.root,'query')
        self.assertFalse(r['coverage']['complete'])
        self.assertIn('GRAPH_ENUMERATION_UNPROVEN',[x['code'] for x in r['diagnostics']])
    def test_missing_freshness_is_gap(self):
        r=parse_codegraph_response([],self.root,'query')
        self.assertIn('GRAPH_INDEX_FRESHNESS_UNVERIFIED',[x['code'] for x in r['diagnostics']])
    def test_raw_response_preserved(self):
        raw={'symbol':'f','definitions':[{'definition':self.node,'callees':[self.node]}]}
        r=parse_codegraph_response(raw,self.root,'callees')
        self.assertEqual(raw,r['artifact']['payload']);self.assertEqual(1,len(r['relations']))
        self.assertEqual('static_may',r['relations'][0]['claimMode'])
    def test_bad_json_shape_not_empty_success(self):
        r=parse_codegraph_response({'unexpected':True},self.root,'query')
        self.assertIn('GRAPH_OUTPUT_INVALID',[x['code'] for x in r['diagnostics']])

    def test_stderr_truncation_preserved(self):
        raw={'toolVersion':'1.6.2','payload':[{'node':self.node}],
             'stderr':'Results truncated at 10; pass --limit to widen.'}
        r=parse_codegraph_response(raw,self.root,'query')
        self.assertIn('GRAPH_RESULTS_TRUNCATED',[d['code'] for d in r['diagnostics']])
        self.assertEqual(raw,r['artifact']['payload'])
