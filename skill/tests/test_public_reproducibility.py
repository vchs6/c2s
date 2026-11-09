"""公开最小环境必须支持同主次版本，并独立解析已有图输出。"""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from codesemantics.fact_query import execute_fact_query
from codesemantics.capability_matrix import detect_available_tools,load_tool_matrix

class PublicReproducibilityTests(unittest.TestCase):
    def test_python_patch_version_is_not_a_tool_gate(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'m.py').write_text('def run():\n return 1\n')
            with patch('platform.python_version',return_value='3.12.5'):
                self.assertIn('python-ast',detect_available_tools(load_tool_matrix()))
                self.assertEqual(['run'],[i['name'] for i in execute_fact_query(root,'functions')['items']])
    def test_unvalidated_minor_is_not_claimed_available(self):
        with patch('platform.python_version',return_value='3.13.0'):
            self.assertNotIn('python-ast',detect_available_tools(load_tool_matrix()))
    def test_supplied_graph_output_needs_parser_not_local_tool(self):
        original=importlib.util.find_spec
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'m.py').write_text('def run():\n return 1\n')
            raw={'status':'ok','pattern':'callees_of','target':'m.py::run','result_count':0,'results_omitted':0,'results':[],'edges':[]}
            with patch.object(importlib.util,'find_spec',side_effect=lambda name,*a,**k:None if name=='code_review_graph' else original(name,*a,**k)):
                result=execute_fact_query(root,{'target':{'kind':'function','name':'run'},'facets':['relations']},tool_runner=lambda *a:{'response':raw,'toolVersion':'2.3.9'})
            self.assertTrue(result['artifacts']);self.assertFalse(result['complete'])
            self.assertIn('GRAPH_INDEX_FRESHNESS_UNVERIFIED',[d['code'] for d in result['diagnostics']])
    def test_absent_fixture_skip_is_explicit_and_strict_mode_fails(self):
        from real_project_support import require_real_project
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'absent'
            with patch.dict(os.environ,{'C2S_REQUIRE_REAL_PROJECTS':'0'}):
                with self.assertRaises(unittest.SkipTest):require_real_project(self,path)
            with patch.dict(os.environ,{'C2S_REQUIRE_REAL_PROJECTS':'1'}):
                with self.assertRaises(AssertionError):require_real_project(self,path)

    def test_each_required_dependency_version_affects_profile_without_optional_python_grammar(self):
        from codesemantics.acquisition import analysis_profile_digest
        import importlib.metadata
        def versions(rust):
            def version(name):
                if name == 'tree-sitter-python':
                    raise importlib.metadata.PackageNotFoundError(name)
                return rust if name == 'tree-sitter-rust' else '1.0.0'
            return version
        with patch('importlib.metadata.version', side_effect=versions('0.24.2')):
            before = analysis_profile_digest()
        with patch('importlib.metadata.version', side_effect=versions('0.24.3')):
            self.assertNotEqual(before, analysis_profile_digest())
    def test_unconfigured_cargo_is_not_accepted_as_native_test_prerequisite(self):
        from real_project_support import require_usable_cargo
        import subprocess
        failed = subprocess.CompletedProcess(['cargo', '--version'], 1, '', 'no default toolchain')
        with patch('subprocess.run', return_value=failed), patch.dict(os.environ, {'C2S_REQUIRE_REAL_PROJECTS': '0'}):
            with self.assertRaises(unittest.SkipTest):
                require_usable_cargo(self, 'cargo')
        with patch('subprocess.run', return_value=failed), patch.dict(os.environ, {'C2S_REQUIRE_REAL_PROJECTS': '1'}):
            with self.assertRaises(AssertionError):
                require_usable_cargo(self, 'cargo')
