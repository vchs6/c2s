"""默认切换只改变新写入，旧档案与可回滚备份必须保留。"""
import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from c2s_skill.__main__ import main
from c2s_skill.semantic_store import SemanticEntityStore
from c2s_skill.entity_construction import construct_and_query_semantic_entities
from c2s_skill.semantic_entity_migration import backup_entity_archive

class V2CutoverTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);base=Path(self.tmp.name)
        self.root=base/'p';self.root.mkdir()
        (self.root/'pyproject.toml').write_text('[project]\nname="example"\n')
        (self.root/'m.py').write_text('def run(x):\n return x+1\n')
        self.db=base/'facts.sqlite';self.store=SemanticEntityStore(self.db)
    def run_cli(self,args):
        out=io.StringIO();err=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            status=main(args)
        self.assertIn(status,(0,2),err.getvalue())
        return json.loads(out.getvalue())
    def test_default_writes_v2_only(self):
        result=self.run_cli(['query','--root',str(self.root),'--select','function:run','--store',str(self.db),'--format','json'])
        self.assertEqual('semantic-fact-result-2',result['profile'])
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(1,conn.execute('SELECT COUNT(*) FROM semantic_entity_v2_archives').fetchone()[0])
            self.assertEqual(0,conn.execute('SELECT COUNT(*) FROM semantic_entity_archives').fetchone()[0])
    def test_legacy_reads_still_available(self):
        old=construct_and_query_semantic_entities(self.root,self.store,'entities')
        snapshot=self.store.read(old['scopeId'])
        result=self.run_cli(['entities','--root',str(self.root),'--select','entities','--store',str(self.db),
                             '--model-profile','semantic-entity-model-1','--format','json'])
        self.assertTrue(result['members']);self.assertEqual(snapshot,self.store.read(old['scopeId']))
    def test_rollback_restores_readable_backup(self):
        old=construct_and_query_semantic_entities(self.root,self.store,'entities')
        snapshot=self.store.read(old['scopeId'])
        backup=Path(self.tmp.name)/'rollback.sqlite';backup_entity_archive(self.store,backup)
        self.run_cli(['query','--root',str(self.root),'--select','function:run','--store',str(self.db),'--format','json'])
        self.assertEqual(snapshot,SemanticEntityStore(backup).read(old['scopeId']))
        result=self.run_cli(['entities','--root',str(self.root),'--select','entities','--store',str(backup),
                             '--model-profile','semantic-entity-model-1','--format','json'])
        self.assertTrue(result['members'])
    def test_default_write_to_v1_database_creates_verified_backup(self):
        old=construct_and_query_semantic_entities(self.root,self.store,'entities')
        snapshot=self.store.read(old['scopeId'])
        result=self.run_cli(['query','--root',str(self.root),'--select','function:run','--store',str(self.db),'--format','json'])
        backup=result['persistence']['backup']
        self.assertEqual('verified',backup['status'])
        self.assertEqual(snapshot,SemanticEntityStore(Path(backup['path'])).read(old['scopeId']))
        self.assertEqual(snapshot,self.store.read(old['scopeId']))
