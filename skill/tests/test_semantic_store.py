import unittest
from contextlib import redirect_stdout
import io
import sqlite3
import json
from jsonschema import Draft202012Validator
from pathlib import Path
from tempfile import TemporaryDirectory

from c2s_skill.semantic_store import (SemanticFactStore, canonicalize_m1, commit_m1,
                                      fact_key_m1, read_m1)
from c2s_skill.__main__ import main


def empty_bundle():
    return {"version": "1.0.0", "profile": "m1-project-discovery-1", "registrations": [],
            "assessments": [], "facts": [], "evidence": [], "coverage": [], "diagnostics": []}


def bundle_with_fact(value="Example", evidence_id="ev-1", fact_id="fact-1"):
    bundle = empty_bundle()
    ref = {"identity": {"authority": "c2s-local",
                         "domainId": "00000000-0000-4000-8000-000000000003", "localId": "subject-a"},
           "kind": "Project"}
    bundle["registrations"] = [{"ref": ref, "sourceKey": "manifest:project", "evidenceIds": [evidence_id]}]
    bundle["evidence"] = [{"evidenceId": evidence_id, "source": "input", "path": "pyproject.toml",
        "artifactId": None, "originalPath": "pyproject.toml", "sha256": ("a" if evidence_id == "ev-1" else "c") * 64,
        "startByte": 0, "endByte": 1, "method": "tomllib", "toolName": None, "toolVersion": None}]
    bundle["facts"] = [{"factId": fact_id, "predicate": "project.name", "subject": ref, "value": value,
        "claimMode": "declaration", "condition": {"kind": "true"}, "evidenceIds": [evidence_id]}]
    return bundle


def session_for(root, store_path):
    return {"analysisId": "00000000-0000-4000-8000-000000000001",
        "inputId": "00000000-0000-4000-8000-000000000002", "root": str(root), "store": str(store_path),
        "identityDomain": "00000000-0000-4000-8000-000000000003", "sourceCommit": None, "inputDigest": "b" * 64,
        "host": {"os": "linux", "arch": "x86_64", "pythonVersion": "3.12.14"},
        "target": {"value": None, "basisEvidenceIds": [], "status": "unknown"},
        "tools": [], "profile": "m1-project-discovery-1"}


def candidate(root, store_path, bundle, operation_id="operation-1", generation=0):
    return {"session": session_for(root, store_path), "operationId": operation_id,
            "expectedGeneration": generation, "bundle": bundle, "artifacts": []}


class SemanticStoreTests(unittest.TestCase):
    def test_public_query_store_persists_and_returns_validated_semantic_bundle(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            (root / "pyproject.toml").write_text(
                '[project]\nname = "sample"\nversion = "0.1.0"\n', encoding="utf-8")
            database = Path(temporary) / "semantic.sqlite"
            output = io.StringIO()

            with redirect_stdout(output):
                status = main(["query", "--root", str(root), "--select", "project",
                               "--store", str(database), "--format", "json"])

            response = json.loads(output.getvalue())
            schema = json.loads((Path(__file__).parents[1] / "contracts" /
                                 "semantic-fact-query.schema.json").read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            self.assertEqual(list(Draft202012Validator(schema).iter_errors(response)), [])
            self.assertEqual(status, 2)  # valid partial result: the tiny fixture lacks declared language metadata
            self.assertTrue(response["semantic_validation"]["valid"])
            self.assertEqual(response["semantic_store"]["state"], "stored")
            self.assertEqual(len(response["semantic_fact_bundle"]["facts"]), 1)
            with sqlite3.connect(database) as connection:
                analysis_id = connection.execute("SELECT analysis_id FROM sessions").fetchone()[0]
            loaded = read_m1(database, analysis_id)
            self.assertEqual(loaded["bundle"], response["semantic_fact_bundle"])

    def test_public_semantic_store_rejects_query_facts_outside_its_m1_profile(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            (root / "main.py").write_text("class Sample:\n    pass\n", encoding="utf-8")
            output = io.StringIO()

            with redirect_stdout(output):
                status = main(["query", "--root", str(root), "--select", "classes",
                               "--store", str(Path(temporary) / "facts.sqlite")])

            self.assertEqual(status, 64)
            self.assertEqual(output.getvalue(), "")

    def test_fact_equivalence_ignores_record_and_evidence_ids_but_keeps_claim_context(self):
        first = bundle_with_fact()["facts"][0]
        second = bundle_with_fact(evidence_id="ev-2", fact_id="fact-2")["facts"][0]
        changed_condition = {**second, "condition": {"kind": "unknown"}}

        self.assertEqual(fact_key_m1(first), fact_key_m1(second))
        self.assertNotEqual(fact_key_m1(first), fact_key_m1(changed_condition))

    def test_canonicalization_merges_new_evidence_without_copying_subject_or_fact(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            db = root.parent / f"{root.name}.sqlite"
            store = SemanticFactStore(db)
            stored = read_m1(store, session_for(root, db)["analysisId"])
            first = bundle_with_fact()
            second = bundle_with_fact(evidence_id="ev-2", fact_id="fact-2")
            stored["bundle"] = first

            merged = canonicalize_m1(session_for(root, db), stored, second, [])

            self.assertEqual(len(merged["bundle"]["registrations"]), 1)
            self.assertEqual(len(merged["bundle"]["facts"]), 1)
            self.assertEqual(merged["bundle"]["facts"][0]["factId"], "fact-1")
            self.assertEqual(merged["bundle"]["facts"][0]["evidenceIds"], ["ev-1", "ev-2"])

    def test_commit_retries_and_equivalent_claims_are_idempotent(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            db = Path(temporary) / "facts.sqlite"
            store = SemanticFactStore(db)
            first = commit_m1(store, candidate(root, db, bundle_with_fact()))
            retry = commit_m1(store, candidate(root, db, bundle_with_fact()))
            additional_evidence = commit_m1(store, candidate(
                root, db, bundle_with_fact(evidence_id="ev-2", fact_id="fact-2"),
                operation_id="operation-2", generation=first["generation"]))
            loaded = read_m1(store, session_for(root, db)["analysisId"])

            self.assertEqual(first["state"], "stored")
            self.assertEqual(retry, first)
            self.assertEqual(additional_evidence["state"], "stored")
            self.assertEqual(len(loaded["bundle"]["facts"]), 1)
            self.assertEqual(loaded["bundle"]["facts"][0]["evidenceIds"], ["ev-1", "ev-2"])
            self.assertEqual(loaded["bundle"]["facts"][0]["subject"]["identity"]["localId"], "subject-a")

    def test_conflicting_claim_values_are_both_retained(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            db = Path(temporary) / "facts.sqlite"
            store = SemanticFactStore(db)
            first = commit_m1(store, candidate(root, db, bundle_with_fact()))
            second = commit_m1(store, candidate(root, db,
                bundle_with_fact("Different", evidence_id="ev-2", fact_id="fact-2"),
                operation_id="operation-2", generation=first["generation"]))
            loaded = read_m1(store, session_for(root, db)["analysisId"])

            self.assertEqual(second["state"], "stored")
            self.assertEqual({fact["value"] for fact in loaded["bundle"]["facts"]}, {"Example", "Different"})

    def test_same_operation_id_with_changed_payload_is_rejected(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            db = Path(temporary) / "facts.sqlite"
            store = SemanticFactStore(db)
            commit_m1(store, candidate(root, db, bundle_with_fact()))

            with self.assertRaisesRegex(ValueError, "operation ID"):
                commit_m1(store, candidate(root, db, bundle_with_fact("Different")))

    def test_invalid_bundle_is_rejected_without_persisting_a_session_or_partial_facts(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            db = Path(temporary) / "facts.sqlite"
            store = SemanticFactStore(db)
            invalid = bundle_with_fact()
            invalid["facts"][0]["evidenceIds"] = ["missing"]

            with self.assertRaises(ValueError):
                commit_m1(store, candidate(root, db, invalid))

            read_back = read_m1(store, session_for(root, db)["analysisId"])
            self.assertIsNone(read_back["session"])
            self.assertEqual(read_back["generation"], 0)
            self.assertEqual(read_back["bundle"]["facts"], [])

    def test_session_ids_must_be_uuids_and_match_registration_identity_domain(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            db = Path(temporary) / "facts.sqlite"
            malformed = candidate(root, db, empty_bundle())
            malformed["session"]["identityDomain"] = "not-a-uuid"
            with self.assertRaisesRegex(ValueError, "must be UUIDs"):
                commit_m1(db, malformed)

            mismatched = candidate(root, db, bundle_with_fact())
            mismatched["session"]["identityDomain"] = "00000000-0000-4000-8000-000000000004"
            with self.assertRaisesRegex(ValueError, "does not match"):
                commit_m1(db, mismatched)

    def test_store_must_live_outside_the_analyzed_project(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            db = root / "facts.sqlite"
            store = SemanticFactStore(db)

            with self.assertRaisesRegex(ValueError, "outside the analyzed project"):
                commit_m1(store, candidate(root, db, bundle_with_fact()))
            self.assertFalse(db.exists())

    def test_failed_sqlite_transaction_does_not_publish_a_partial_bundle(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            db = Path(temporary) / "facts.sqlite"
            store = SemanticFactStore(db)
            with store._connect() as connection:
                connection.execute("CREATE TRIGGER reject_fact BEFORE INSERT ON facts BEGIN SELECT RAISE(ABORT, 'injected'); END")

            receipt = commit_m1(store, candidate(root, db, bundle_with_fact()))
            read_back = read_m1(store, session_for(root, db)["analysisId"])

            self.assertEqual(receipt["state"], "failed")
            self.assertEqual(read_back["generation"], 0)
            self.assertEqual(read_back["bundle"]["facts"], [])


if __name__ == "__main__":
    unittest.main()
