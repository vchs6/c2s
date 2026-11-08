"""显式v2入口与既有命令兼容。"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from c2s_skill.__main__ import main

class CliV2Tests(unittest.TestCase):
    def test_explicit_profile_query(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'m.py').write_text('def run():\n return 1\n')
            output=io.StringIO()
            with contextlib.redirect_stdout(output):
                status=main(['query','--root',t,'--select','function:run','--model-profile','semantic-entity-model-2','--format','json'])
            result=json.loads(output.getvalue())
            self.assertEqual('semantic-fact-result-2',result['profile']);self.assertEqual(2,status)
            self.assertTrue(result['items'])

    def test_structured_entity_request(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t)/'m.py').write_text('class Record:\n key: str\n')
            output=io.StringIO()
            with contextlib.redirect_stdout(output):
                status=main(['entities','--root',t,'--request',json.dumps({'target':{'kind':'DataEntity','name':'Record'},'detail':'self'}),
                             '--model-profile','semantic-entity-model-2','--format','json'])
            self.assertEqual('Record',json.loads(output.getvalue())['items'][0]['name'])

    def test_invalid_option_combinations_are_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(64,main(['query','--root',t,'--select','functions','--all-functions']))
