from __future__ import annotations

import concurrent.futures
import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path

from c2s_skill.semantic_store import SemanticEntityStore


def model():
    project = {"identity": {"authority": "test", "domainId": "scope-a", "localId": "project"},
               "kind": "Project"}
    record = {"identity": {"authority": "test", "domainId": "scope-a", "localId": "record"},
              "kind": "DataEntity"}
    return {"version": "1.0.0", "profile": "semantic-entity-model-1", "scopeId": "scope-a",
        "entities": [
            {"ref": project, "name": "Example", "aliases": [], "description": "项目", "attributes": [],
             "sourceKeys": [], "observationViews": ["E0"]},
            {"ref": record, "name": "订单", "aliases": [], "description": "数据", "attributes": [],
             "sourceKeys": ["source:record"], "observationViews": ["E2"]}],
        "claims": [],
        "relations": [{"relationId": "relation-1", "predicate": "defines", "subject": project,
            "target": record, "evidenceIds": ["ev-1"], "condition": {"kind": "true"}}],
        "continuityCandidates": [],
        "evidence": [{"evidenceId": "ev-1", "source": "source", "description": "源声明"}],
        "coverage": [{"coverageId": "coverage-1", "entity": record, "selector": "members",
            "status": "obtained", "inputFingerprint": "sha256:a", "analyzerVersion": "1.0.0"}]}


class SemanticEntityStoreTests(unittest.TestCase):
    def test_complete_entity_profile_round_trips_without_mixing_fact_profiles(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "semantic.sqlite"
            store = SemanticEntityStore(path)
            original = model()
            self.assertTrue(store.write(original)["valid"])
            self.assertEqual(store.read("scope-a"), original)
            with sqlite3.connect(path) as connection:
                names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                indexed = connection.execute("SELECT kind,name,source_key FROM semantic_entity_index "
                                             "WHERE source_key='source:record'").fetchone()
            self.assertIn("semantic_entity_archives", names)
            self.assertIn("semantic_entity_index", names)
            self.assertEqual(indexed, ("DataEntity", "订单", "source:record"))
            self.assertNotIn("sessions", names)

    def test_registry_reuses_stable_identity_and_merges_evidence_atomically(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = SemanticEntityStore(Path(temporary) / "semantic.sqlite")
            first = store.register("scope-a", "source:key", "DataEntity", "订单", ["ev-1"])
            second = store.register("scope-a", "source:key", "DataEntity", "订单", ["ev-2"])
            self.assertEqual(first["ref"], second["ref"])
            self.assertEqual(second["evidenceIds"], ["ev-1", "ev-2"])

    def test_registry_rejects_kind_conflict_and_keeps_existing_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = SemanticEntityStore(Path(temporary) / "semantic.sqlite")
            first = store.register("scope-a", "source:key", "DataEntity", "订单", ["ev-1"])
            with self.assertRaises(ValueError):
                store.register("scope-a", "source:key", "ComputationEntity", "订单", ["ev-2"])
            self.assertEqual(store.lookup("scope-a", "source:key"), first)

    def test_invalid_model_is_rejected_without_publishing_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = SemanticEntityStore(Path(temporary) / "semantic.sqlite")
            invalid = model()
            invalid["relations"][0]["target"] = {
                "identity": {"authority": "test", "domainId": "scope-a", "localId": "missing"},
                "kind": "DataEntity"}
            with self.assertRaises(ValueError):
                store.write(invalid)
            self.assertIsNone(store.read("scope-a"))

    def test_conflicting_merge_rolls_back_and_keeps_previous_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = SemanticEntityStore(Path(temporary) / "semantic.sqlite")
            original = model()
            store.write(original)
            conflicting = copy.deepcopy(original)
            conflicting["evidence"][0]["description"] = "conflicting evidence payload"
            with self.assertRaises(ValueError):
                store.write(conflicting)
            self.assertEqual(store.read("scope-a"), original)

    def test_concurrent_registration_retries_resolve_to_same_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "semantic.sqlite"
            def run(index):
                return SemanticEntityStore(path).register("scope-a", "source:key", "DataEntity", "订单",
                                                          [f"ev-{index}"])
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(run, range(8)))
            self.assertEqual(len({item["ref"]["identity"]["localId"] for item in results}), 1)
            merged = SemanticEntityStore(path).lookup("scope-a", "source:key")
            self.assertEqual(merged["evidenceIds"], [f"ev-{index}" for index in range(8)])

    def test_source_move_keeps_distinct_identity_and_proposes_unresolved_continuity(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = SemanticEntityStore(Path(temporary) / "semantic.sqlite")
            previous = store.register("scope-a", "src:old/path", "DataEntity", "订单", ["ev-old"])
            current = store.register("scope-a", "src:new/path", "DataEntity", "订单", ["ev-new"])
            self.assertNotEqual(previous["ref"], current["ref"])
            self.assertEqual(current["continuityCandidates"][0]["status"], "continuity_unresolved")
            self.assertEqual(len(store.continuity_candidates("scope-a")), 1)


if __name__ == "__main__":
    unittest.main()
