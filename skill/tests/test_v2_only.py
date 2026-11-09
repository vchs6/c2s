"""产品仅提供V2接口，历史档案不得被静默解释或改写。"""
import contextlib
import hashlib
import importlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from c2s_skill.__main__ import main
from c2s_skill.fact_query import execute_fact_query
from c2s_skill.semantic_store import SemanticEntityStore

class V2OnlyTests(unittest.TestCase):
    def test_cli_rejects_v1(self):
        with tempfile.TemporaryDirectory() as t, contextlib.redirect_stderr(io.StringIO()),contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):main(['query','--root',t,'--select','functions','--model-profile','semantic-entity-model-1'])
    def test_old_runtime_symbols_removed(self):
        removed={'c2s_skill.semantic_store':['SemanticFactStore','read_m1','commit_m1','read_bundle','query_bundle'],
                 'c2s_skill.query':['query_project','query_from_scan','result_to_dict','result_to_markdown'],
                 'c2s_skill.entity_construction':['construct_and_query_semantic_entities','add_workspace_observations'],
                 'c2s_skill.semantic_entity_query':['query_entity_store','query_semantic_entities'],
                 'c2s_skill.store':['FactStore'],
                 'c2s_semantic_contract':['register_m1','validate_model','project_query_to_semantic_model']}
        for module,names in removed.items():
            loaded=importlib.import_module(module)
            for name in names:
                with self.subTest(module=module,name=name):self.assertFalse(hasattr(loaded,name))
        from c2s_skill.store import QueryResultCache
        for name in ('save','load'):self.assertFalse(hasattr(QueryResultCache,name))
        for name in ('read','write','register','lookup'):self.assertFalse(hasattr(SemanticEntityStore,name))
        with self.assertRaises(ModuleNotFoundError):importlib.import_module('c2s_skill.semantic_entity_migration')
    def test_legacy_archive_rejected_without_mutation(self):
        with tempfile.TemporaryDirectory() as t:
            db=Path(t)/'old.sqlite'
            with sqlite3.connect(db) as c:
                c.execute('CREATE TABLE semantic_entity_archives(scope_id TEXT PRIMARY KEY,generation INTEGER,payload TEXT)')
                c.execute('INSERT INTO semantic_entity_archives VALUES(?,?,?)',('old',1,'{"profile":"semantic-entity-model-1"}'))
            before=hashlib.sha256(db.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,'UNSUPPORTED_ARCHIVE_PROFILE'):
                SemanticEntityStore(db).read_request('old',{},'x','y')
            self.assertEqual(before,hashlib.sha256(db.read_bytes()).hexdigest())
    def test_default_query_remains_v2(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'p';root.mkdir();(root/'m.py').write_text('def run():\n return 1\n')
            store=SemanticEntityStore(Path(t)/'facts.sqlite')
            first=execute_fact_query(root,'function:run',store);second=execute_fact_query(root,'function:run',store)
            self.assertEqual('semantic-fact-result-2',first['profile']);self.assertTrue(first['items'][0]['algorithm'])
            self.assertEqual(first['items'],second['items']);self.assertEqual(0,second['cost']['parsedFiles'])
            with sqlite3.connect(store.path) as c:
                self.assertFalse(c.execute("SELECT 1 FROM sqlite_master WHERE name='semantic_entity_archives'").fetchone())

    def test_explicit_v2_backup_roundtrip(self):
        from c2s_skill.archive_backup import backup_entity_archive
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'p';root.mkdir();(root/'m.py').write_text('def run():\n return 1\n')
            store=SemanticEntityStore(Path(t)/'facts.sqlite')
            result=execute_fact_query(root,'functions',store)
            receipt=backup_entity_archive(store,Path(t)/'backup.sqlite')
            self.assertEqual('verified',receipt['status'])
            restored=SemanticEntityStore(Path(receipt['path']))
            original=store.read_request(result['request']['scopeId'],result['request'],result['cost']['inputFingerprint'],result['cost']['configurationDigest'])
            self.assertEqual(original,restored.read_request(result['request']['scopeId'],result['request'],result['cost']['inputFingerprint'],result['cost']['configurationDigest']))

    def test_backup_missing_source_does_not_create_archive(self):
        from c2s_skill.archive_backup import backup_entity_archive
        with tempfile.TemporaryDirectory() as t:
            source=Path(t)/'absent.sqlite';target=Path(t)/'backup.sqlite'
            with self.assertRaises(ValueError):backup_entity_archive(SemanticEntityStore(source),target)
            self.assertFalse(source.exists());self.assertFalse(target.exists())

    def test_mixed_archive_never_serves_or_modifies_v1(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'p';root.mkdir();(root/'m.py').write_text('def run():\n return 1\n')
            store=SemanticEntityStore(Path(t)/'facts.sqlite')
            execute_fact_query(root,'functions',store)
            payload='{"profile":"semantic-entity-model-1","private":"untouched"}'
            with sqlite3.connect(store.path) as c:
                c.execute('CREATE TABLE semantic_entity_archives(scope_id TEXT,payload TEXT)')
                c.execute('INSERT INTO semantic_entity_archives VALUES(?,?)',('old',payload))
            result=execute_fact_query(root,'modules',store)
            self.assertEqual('semantic-fact-result-2',result['profile'])
            with sqlite3.connect(store.path) as c:self.assertEqual([('old',payload)],c.execute('SELECT * FROM semantic_entity_archives').fetchall())

    def test_legacy_cache_rejected_without_mutation(self):
        from c2s_skill.store import QueryResultCache
        from c2s_skill.fact_request import normalize_fact_request
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'p';root.mkdir();db=Path(t)/'old-cache.sqlite'
            with sqlite3.connect(db) as c:c.execute('CREATE TABLE query_results(root TEXT,source_digest TEXT,selectors TEXT,result_json TEXT)')
            before=hashlib.sha256(db.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,'UNSUPPORTED_CACHE_PROFILE'):
                QueryResultCache(db).load_v2(root,normalize_fact_request('modules'),'x','y')
            self.assertEqual(before,hashlib.sha256(db.read_bytes()).hexdigest())
