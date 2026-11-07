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
        "sourceMappings": [{"mappingId": "mapping-1", "target": record,
            "sourceConstruct": {"constructId": "construct-1", "sourceKey": "source-key-1",
                "language": "python", "syntaxKind": "class_declaration", "name": "Order",
                "path": "src/order.py", "sha256": "a" * 64, "startByte": 0, "endByte": 12,
                "parserId": "python-ast", "parserVersion": "3.12", "text": "class Order"},
            "role": "represents", "mappingStatus": "mapped", "evidenceIds": ["ev-1"]}],
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
                mapping_indexed = connection.execute("SELECT source_construct_id,source_path,mapping_status "
                    "FROM semantic_entity_mapping_index WHERE mapping_id='mapping-1'").fetchone()
            self.assertIn("semantic_entity_archives", names)
            self.assertIn("semantic_entity_index", names)
            self.assertEqual(indexed, ("DataEntity", "订单", "source:record"))
            self.assertEqual(mapping_indexed, ("construct-1", "src/order.py", "mapped"))
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

    def test_repeated_attribute_evidence_merges_without_changing_semantic_range(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = SemanticEntityStore(Path(temporary) / "semantic.sqlite")
            first = model()
            first["entities"][1]["attributes"] = [{"attributeId": "status", "name": "状态",
                "semanticType": "unknown", "valueRange": {"kind": "finite_set", "values": ["paid"],
                    "evidenceIds": ["ev-1"]}, "cardinality": "one", "constraints": [],
                "evidenceIds": ["ev-1"]}]
            store.write(first)
            second = copy.deepcopy(first)
            second["evidence"].append({"evidenceId": "ev-2", "source": "source", "description": "补充"})
            second["entities"][1]["attributes"][0]["evidenceIds"].append("ev-2")
            second["entities"][1]["attributes"][0]["valueRange"]["evidenceIds"].append("ev-2")
            store.write(second)
            merged = store.read("scope-a")["entities"][1]["attributes"][0]
            self.assertEqual(merged["valueRange"]["evidenceIds"], ["ev-1", "ev-2"])

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
            current = store.register("scope-a", "src:new/path", "DataEntity", "订单", ["ev-new"],
                                     continuity_from=[previous])
            self.assertNotEqual(previous["ref"], current["ref"])
            self.assertEqual(current["continuityCandidates"][0]["status"], "continuity_unresolved")
            self.assertEqual(len(store.continuity_candidates("scope-a")), 1)


if __name__ == "__main__":
    unittest.main()
