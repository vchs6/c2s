"""旧实体档案转换须保留身份与载荷，不猜测解释来源。"""
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from c2s_skill.semantic_entity_migration import import_entity_v1, export_entity_v1, backup_entity_archive
from c2s_skill.semantic_store import SemanticEntityStore
from c2s_skill.entity_construction import construct_and_query_semantic_entities
from c2s_semantic_contract.validation import validate_semantic_entity_model_v2

class ModelV2MigrationTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);base=Path(self.t.name)
        self.root=base/'p';self.root.mkdir()
        (self.root/'pyproject.toml').write_text('[project]\nname="sample"\n')
        (self.root/'m.py').write_text('class Record:\n key: str\n\ndef run():\n return 1\n')
        self.store=SemanticEntityStore(base/'old.sqlite')
        result=construct_and_query_semantic_entities(self.root,self.store,'entities')
        self.scope=result['scopeId'];self.old=self.store.read(self.scope)
    def test_v1_refs_evidence_unchanged(self):
        v2=import_entity_v1(self.old)
        self.assertEqual(self.old['entities'],v2['entities'])
        self.assertEqual(self.old['evidence'],v2['evidence'])
        self.assertTrue(validate_semantic_entity_model_v2(v2)['valid'])
    def test_unknown_origin_not_direct(self):
        v2=import_entity_v1(self.old)
        self.assertTrue(v2['claims'])
        self.assertTrue(all(c['origin']=='unclassified_legacy' for c in v2['claims']))
        self.assertTrue(all(c['legacyPayloadArtifactId'] for c in v2['claims']))
        self.assertTrue(all(c['status']=='not_acquired' for c in v2['sourceCoverage']))
    def test_export_reports_unrepresentable_sources(self):
        exported=export_entity_v1(import_entity_v1(self.old))
        self.assertEqual(self.old,exported['document'])
        self.assertTrue(exported['losses'])
        self.assertEqual(exported,export_entity_v1(import_entity_v1(self.old)))
    def test_backup_readback_equal(self):
        backup=Path(self.t.name)/'backup.sqlite'
        receipt=backup_entity_archive(self.store,backup)
        self.assertEqual('verified',receipt['status'])
        self.assertEqual(self.old,SemanticEntityStore(backup).read(self.scope))
        with self.assertRaises(ValueError):backup_entity_archive(self.store,backup)
    def test_failed_upgrade_keeps_v1_default(self):
        from c2s_skill import __main__ as cli
        before=cli.DEFAULT_MODEL_PROFILE
        invalid=deepcopy(self.old);invalid['entities'][0]['ref']['kind']='wrong'
        with self.assertRaises(ValueError):import_entity_v1(invalid)
        self.assertEqual(before,cli.DEFAULT_MODEL_PROFILE)
        self.assertEqual(self.old,self.store.read(self.scope))
