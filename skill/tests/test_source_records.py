"""来源组织独立于语义解释，范围和字节证据可复核。"""
import tempfile
import unittest
from pathlib import Path
from dataclasses import replace
from c2s_skill.acquisition import scan_project
from c2s_skill.source_records import collect_source_records

class SourceRecordsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'a.py').write_text('def calculate(x):\n    return x + 1\n')
        (self.root/'bad.py').write_text('def broken(:')
        (self.root/'.hidden').mkdir();(self.root/'.hidden/example.py').write_text('x=1\n')
        (self.root/'nested').mkdir();(self.root/'nested/pyproject.toml').write_text('[project]\nname="inner"\n')
    def collect(self,paths=None):
        scan=scan_project(self.root,source_paths=paths)
        return collect_source_records(self.root,scan,{'scopeId':'test','target':{'kind':'all'},'facets':['organization']})
    def test_module_without_semantic_mapping_queryable(self):
        result=self.collect()
        modules=[x for x in result['sourceRecords'] if x['kind']=='source_module']
        self.assertIn('a.py',[m['path'] for m in modules])
        self.assertNotIn('entities',result)
        self.assertTrue(any(x['name']=='calculate' for x in result['sourceRecords']))
    def test_nested_manifest_ownership_unresolved(self):
        result=self.collect()
        m=next(x for x in result['sourceRecords'] if x['path']=='nested/pyproject.toml')
        self.assertEqual('inner',m['name']);self.assertEqual('project_manifest',m['kind'])
        self.assertNotIn('entityRef',m)
    def test_hidden_examples_inventory_retained(self):
        result=self.collect()
        self.assertIn('.hidden/example.py',[x['path'] for x in result['sourceRecords']])
    def test_selected_paths_do_not_parse_unrelated(self):
        scan=scan_project(self.root,source_paths=frozenset({'a.py'}))
        self.assertEqual(['a.py'],[x.path for x in scan.files])
        result=collect_source_records(self.root,scan,{'scopeId':'s','target':{'kind':'all'},'facets':['organization']})
        self.assertIn('bad.py',result['sourceCoverage'][0]['unprocessedPaths'])
    def test_reacquisition_same_source_record_id(self):
        a=self.collect();b=self.collect()
        self.assertEqual(a['sourceRecords'],b['sourceRecords'])
    def test_tool_disagreement_preserves_claims(self):
        scan=scan_project(self.root,source_paths=frozenset({'a.py'}))
        parsed=scan.files[0];construct=next(c for c in parsed.constructs if c.name=="calculate")
        other=replace(construct,parser_id='other',declared_type='conflicting')
        scan=replace(scan,files=(replace(parsed,constructs=parsed.constructs+(other,)),))
        result=collect_source_records(self.root,scan,{'scopeId':'s','target':{'kind':'all'},'facets':['organization']})
        record=next(x for x in result['sourceRecords'] if x['name']=='calculate')
        self.assertEqual(2,len(record['evidenceIds']))
        self.assertEqual(2,len(record['value']['observations']))
        self.assertTrue(result['diagnostics'])
    def test_bad_selected_path_rejected(self):
        with self.assertRaises(ValueError):scan_project(self.root,source_paths=frozenset({'../bad.py'}))
