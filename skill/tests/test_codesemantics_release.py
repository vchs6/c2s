"""首版命名、当前契约独立性和运行环境判定。"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

class CodesemanticsReleaseTests(unittest.TestCase):
    def test_product_has_canonical_import_names(self):
        self.assertIsNotNone(importlib.util.find_spec('codesemantics'))
        self.assertIsNotNone(importlib.util.find_spec('codesemantics_contract'))
        self.assertIsNone(importlib.util.find_spec('c2s_skill'))
        self.assertIsNone(importlib.util.find_spec('c2s_semantic_contract'))

    def test_current_validator_does_not_load_other_model_schemas(self):
        self.assertIsNotNone(importlib.util.find_spec('codesemantics'))
        from codesemantics.fact_query import execute_fact_query
        original=Path.read_text
        forbidden={'semantic-entity-model.schema.json','semantic-entity-catalog-manifest.json'}
        def read(path,*args,**kwargs):
            if path.name in forbidden:raise AssertionError('不能依赖非当前契约：'+path.name)
            return original(path,*args,**kwargs)
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'m.py').write_text('def run():\n return 1\n')
            with patch.object(Path,'read_text',read):
                result=execute_fact_query(root,{'view':'entity','target':{'kind':'ComputationEntity','name':'run'},'detail':'self'})
            self.assertEqual('run',result['items'][0]['name'])

    def test_prerelease_interpreter_is_unavailable_without_parsing_crash(self):
        self.assertIsNotNone(importlib.util.find_spec('codesemantics'))
        from codesemantics.capability_matrix import detect_available_tools,load_tool_matrix
        for version in ('3.12.0rc1','3.13.0dev1'):
            with self.subTest(version=version),patch('platform.python_version',return_value=version):
                self.assertNotIn('python-ast',detect_available_tools(load_tool_matrix()))
