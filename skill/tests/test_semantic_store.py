import unittest
from contextlib import redirect_stdout
import io
import sqlite3
import json
from jsonschema import Draft202012Validator
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from c2s_skill.semantic_store import (SemanticFactStore, canonicalize_m1, commit_m1,
                                      fact_key_m1, read_m1)
from c2s_skill.__main__ import main as _main


def main(args):
    """本组历史协议断言显式验证v1兼容入口。"""
    return _main([*args, "--model-profile", "semantic-entity-model-1"])


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


def session_for(root, store_path, profile="m1-project-discovery-1"):
    return {"analysisId": "00000000-0000-4000-8000-000000000001",
        "inputId": "00000000-0000-4000-8000-000000000002", "root": str(root), "store": str(store_path),
        "identityDomain": "00000000-0000-4000-8000-000000000003", "sourceCommit": None, "inputDigest": "b" * 64,
        "host": {"os": "linux", "arch": "x86_64", "pythonVersion": "3.12.14"},
        "target": {"value": None, "basisEvidenceIds": [], "status": "unknown"},
        "tools": [], "profile": profile}


def candidate(root, store_path, bundle, operation_id="operation-1", generation=0):
    return {"session": session_for(root, store_path), "operationId": operation_id,
            "expectedGeneration": generation, "bundle": bundle, "artifacts": []}


class SemanticStoreTests(unittest.TestCase):
    def test_full_layered_bundle_is_stored_and_queried_by_selector(self):
        from c2s_semantic_contract.projection import project_query_to_semantic_model
        from c2s_semantic_contract.validation import semantic_model_catalogs, validate_model
        from c2s_skill.query import query_project
        from c2s_skill.semantic_store import _commit_legacy_bundle_for_migration, query_bundle, read_bundle

        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            source = root / "run.py"
            source.write_text("def run(value):\n    return value + 1\n", encoding="utf-8")
            db = Path(temporary) / "all-facts.sqlite"
            session = session_for(root, db, "semantic-fact-model-1")
            projected = project_query_to_semantic_model(
                query_project(root, ["function:run"]), identity_domain=session["identityDomain"])
            bundle = projected["bundle"]
            evidence_id = bundle["evidence"][0]["evidenceId"]
            consumer = bundle["facts"][0]["subject"]
            provider = {"identity": {"authority": "registry", "domainId": "packages", "localId": "serde"},
                        "kind": "PackageSpecification"}
            bundle["registrations"].append({"ref": provider, "sourceKey": "registry:serde",
                                             "evidenceIds": [evidence_id]})
            bundle["dependencies"] = [{"dependencyId": "dep-1", "consumer": consumer,
                "purpose": "build", "stage": "compile", "path": None, "version": "^1",
                "condition": {"kind": "true"}, "evidenceIds": [evidence_id]}]
            bundle["dependencyResolutions"] = [{"resolutionId": "resolution-1", "dependencyId": "dep-1",
                "status": "resolved", "providers": [provider], "configuration": "linux",
                "visibility": "registry", "scopePosition": "outside", "evidenceIds": [evidence_id]}]
            bundle["contextDomains"] = [{"keyId": "target", "values": ["linux", "windows"]}]
            bundle["contexts"] = [{"contextId": "linux", "assignments": {"target": "linux"}}]
            artifact_content = '{"tool":"fixture"}'
            artifact = {"artifactId": "artifact-fixture", "mediaType": "application/json",
                        "sha256": __import__("hashlib").sha256(artifact_content.encode()).hexdigest(),
                        "content": artifact_content}
            artifact_evidence_id = "artifact-evidence"
            bundle["evidence"].append({"evidenceId": artifact_evidence_id, "source": "tool_output",
                "path": None, "artifactId": artifact["artifactId"], "originalPath": "fixture.json",
                "sha256": artifact["sha256"], "startByte": 0, "endByte": len(artifact_content),
                "method": "code-review-graph", "toolName": "fixture", "toolVersion": "1"})
            bundle["facts"][0]["evidenceIds"].append(artifact_evidence_id)
            bundle["registrations"][0]["evidenceIds"].append(artifact_evidence_id)
            projected["sourceObservations"]["items"].append({"evidenceId": artifact_evidence_id,
                "status": "verified", "observedSha256": artifact["sha256"]})
            checked = validate_model(bundle, semantic_model_catalogs(), projected["sourceObservations"])
            self.assertTrue(checked["valid"], checked["diagnostics"])

            receipt = _commit_legacy_bundle_for_migration(db, {"session": session, "operationId": "full-operation-1",
                "expectedGeneration": 0, "bundle": bundle,
                "sourceObservations": projected["sourceObservations"], "artifacts": [artifact]})
            loaded = read_bundle(db, session["analysisId"])
            selected = query_bundle(db, session["analysisId"], "function:run")

            self.assertEqual(receipt["state"], "stored")
            self.assertEqual(loaded["bundle"]["profile"], "semantic-fact-model-1")
            self.assertEqual({item["evidenceId"] for item in loaded["sourceObservations"]["items"]},
                             {item["evidenceId"] for item in projected["sourceObservations"]["items"]})
            for collection in ("registrations", "assessments", "facts", "evidence", "coverage",
                               "dependencies", "dependencyResolutions", "semanticStates", "diagnostics",
                               "contextDomains", "contexts"):
                self.assertEqual(sorted(loaded["bundle"][collection], key=lambda item: json.dumps(item, sort_keys=True)),
                                 sorted(bundle[collection], key=lambda item: json.dumps(item, sort_keys=True)))
            self.assertTrue(validate_model(loaded["bundle"], semantic_model_catalogs(),
                                           loaded["sourceObservations"])["valid"])
            from c2s_skill.semantic_store import query_artifacts
            self.assertEqual(query_artifacts(db, session["analysisId"], "function:run"), [artifact])
            self.assertEqual({fact["factId"] for fact in selected["facts"]},
                             {fact["factId"] for fact in bundle["facts"]})
            self.assertEqual(selected["coverage"][0]["selector"], "function:run")
            self.assertEqual(len(selected["facts"]), len(bundle["facts"]))
            with sqlite3.connect(db) as connection:
                stored_collections = {row[0] for row in connection.execute(
                    "SELECT DISTINCT collection FROM semantic_records WHERE analysis_id=?", (session["analysisId"],))}
                reference_count = connection.execute(
                    "SELECT COUNT(*) FROM semantic_refs WHERE analysis_id=?", (session["analysisId"],)).fetchone()[0]
            self.assertEqual(stored_collections,
                {name for name in ("registrations", "assessments", "facts", "evidence", "coverage",
                    "dependencies", "dependencyResolutions", "semanticStates", "diagnostics",
                    "contextDomains", "contexts") if bundle[name]})
            self.assertGreater(reference_count, 0)

    def test_full_fact_equivalence_preserves_layer_claim_context_and_merges_evidence(self):
        from c2s_skill.semantic_store import fact_key_semantic

        fact = {"factId": "fact-a", "predicate": "behavior.calls", "subject":
            {"kind": "BehaviorStep", "identity": {"authority": "c2s", "domainId": "d", "localId": "s"}},
            "value": None, "arguments": [{"role": "callee", "value": "target"}],
            "claimMode": "static_may", "condition": {"kind": "true"},
            "evidenceIds": ["ev-a"], "evidenceRefs": [{"evidenceId": "ev-a", "role": "Supports"}],
            "sourceMetadata": {"kind": "call", "layer": "E4", "owner": "f", "text": "target()",
                                "evidenceIncluded": True}}
        same_claim = {**fact, "factId": "fact-b", "evidenceIds": ["ev-b"],
            "evidenceRefs": [{"evidenceId": "ev-b", "role": "Supports"}],
            "sourceMetadata": {**fact["sourceMetadata"], "evidenceIncluded": False, "text": ""}}
        changed_layer_claim = {**fact, "claimMode": "static_must", "factId": "fact-c"}
        changed_derivation = {**fact, "factId": "fact-d", "derivation": {
            "ruleId": "different-rule", "premiseFactIds": ["premise-2"]}}

        self.assertEqual(fact_key_semantic(fact), fact_key_semantic(same_claim))
        self.assertNotEqual(fact_key_semantic(fact), fact_key_semantic(changed_layer_claim))
        self.assertNotEqual(fact_key_semantic(fact), fact_key_semantic(changed_derivation))

    def test_public_query_store_persists_entity_profile_without_writing_legacy_archive(self):
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
            self.assertTrue(response["semantic_entity_validation"]["valid"])
            self.assertEqual(response["semantic_entity_store"]["profile"], "semantic-entity-model-1")
            self.assertEqual(response["semantic_entity_store"]["state"], "stored")
            with sqlite3.connect(database) as connection:
                tables = {row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
                stored = connection.execute(
                    "SELECT payload FROM semantic_entity_archives WHERE scope_id=?",
                    (response["semantic_entity_store"]["scopeId"],)).fetchone()
            self.assertEqual(json.loads(stored[0])["profile"], "semantic-entity-model-1")
            self.assertNotIn("sessions", tables)
            self.assertNotIn("full_bundles", tables)

    def test_public_semantic_store_accepts_source_view_selector_and_persists_entity_profile(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            (root / "main.py").write_text("class Sample:\n    def run(self):\n        return 1\n", encoding="utf-8")
            output = io.StringIO()

            with redirect_stdout(output):
                status = main(["query", "--root", str(root), "--select", "classes",
                               "--store", str(Path(temporary) / "facts.sqlite"), "--format", "json"])

            self.assertIn(status, (0, 2))
            response = json.loads(output.getvalue())
            self.assertEqual(response["semantic_entity_store"]["profile"], "semantic-entity-model-1")

    def test_query_selectors_share_one_entity_archive(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            (root / "main.py").write_text("class Sample:\n    def run(self):\n        return 1\n", encoding="utf-8")
            database = Path(temporary) / "facts.sqlite"
            for selector in ("classes", "functions"):
                with redirect_stdout(io.StringIO()):
                    status = main(["query", "--root", str(root), "--select", selector,
                                   "--store", str(database), "--format", "json"])
                self.assertIn(status, (0, 2))
            with sqlite3.connect(database) as connection:
                rows = connection.execute("SELECT payload FROM semantic_entity_archives").fetchall()
            self.assertEqual(len(rows), 1)
            stored = json.loads(rows[0][0])
            self.assertEqual(stored["profile"], "semantic-entity-model-1")
            self.assertEqual({item["selector"] for item in stored["coverage"]}, {"all-entities"})

    def test_query_entity_archive_is_reused_for_same_source_snapshot(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            (root / "main.py").write_text("class Sample:\n    def run(self):\n        return 1\n", encoding="utf-8")
            database = Path(temporary) / "facts.sqlite"
            args = ["query", "--root", str(root), "--select", "classes", "--store", str(database), "--format", "json"]
            with redirect_stdout(io.StringIO()):
                first_status = main(args)
            output = io.StringIO()
            with redirect_stdout(output):
                second_status = main(args)
            response = json.loads(output.getvalue())
            self.assertIn(first_status, (0, 2))
            self.assertIn(second_status, (0, 2))
            self.assertEqual(response["semantic_entity_store"]["profile"], "semantic-entity-model-1")
            self.assertEqual(response["semantic_entity_query"]["constructionStatus"], "reused")

    def test_default_markdown_query_reports_entity_archive_state(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            (root / "main.py").write_text("class Sample:\n    pass\n", encoding="utf-8")
            args = ["query", "--root", str(root), "--select", "classes",
                    "--store", str(Path(temporary) / "facts.sqlite")]
            with redirect_stdout(io.StringIO()):
                first_status = main(args)
            markdown = io.StringIO()
            with redirect_stdout(markdown):
                second_status = main(args)
            self.assertIn(first_status, (0, 2))
            self.assertIn(second_status, (0, 2))
            self.assertIn("Semantic entities:", markdown.getvalue())

    def test_public_legacy_full_profile_writer_is_disabled_after_cutover(self):
        from c2s_skill.semantic_store import commit_bundle
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            db = Path(temporary) / "legacy.sqlite"
            session = session_for(root, db, "semantic-fact-model-1")
            candidate = {"session": session, "operationId": "legacy-write",
                "expectedGeneration": 0, "bundle": {"version": "1.0.0",
                    "profile": "semantic-fact-model-1", "registrations": [], "assessments": [],
                    "facts": [], "evidence": [], "coverage": [], "dependencies": [],
                    "dependencyResolutions": [], "semanticStates": [], "diagnostics": [],
                    "contextDomains": [], "contexts": []}, "artifacts": []}
            with self.assertRaisesRegex(ValueError, "read-only"):
                commit_bundle(db, candidate)

    def test_entity_cutover_keeps_existing_legacy_archive_readable_in_same_database(self):
        from c2s_skill.semantic_store import (_commit_legacy_bundle_for_migration, read_bundle)
        from c2s_semantic_contract.projection import project_query_to_semantic_model
        from c2s_skill.query import query_project
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            (root / "pyproject.toml").write_text(
                '[project]\nname = "sample"\nversion = "0.1.0"\nrequires-python = ">=3.11"\n',
                encoding="utf-8")
            (root / "main.py").write_text("def run():\n    return 1\n", encoding="utf-8")
            database = Path(temporary) / "combined.sqlite"
            session = session_for(root, database, "semantic-fact-model-1")
            projection = project_query_to_semantic_model(query_project(root, ["functions"]),
                identity_domain=session["identityDomain"])
            legacy_bundle = projection["bundle"]
            _commit_legacy_bundle_for_migration(database, {"session": session,
                "operationId": "before-cutover", "expectedGeneration": 0,
                "bundle": legacy_bundle, "artifacts": [],
                "sourceObservations": projection["sourceObservations"]})
            backup_database = Path(temporary) / "before-cutover.sqlite"
            with sqlite3.connect(database) as source, sqlite3.connect(backup_database) as backup:
                source.backup(backup)

            with redirect_stdout(io.StringIO()):
                status = main(["query", "--root", str(root), "--select", "functions",
                               "--store", str(database), "--format", "json"])

            self.assertIn(status, (0, 2))
            old = read_bundle(database, session["analysisId"])
            backup = read_bundle(backup_database, session["analysisId"])
            self.assertEqual(old["bundle"]["profile"], "semantic-fact-model-1")
            self.assertEqual(old["bundle"]["facts"], legacy_bundle["facts"])
            self.assertEqual(backup["bundle"], old["bundle"])
            with sqlite3.connect(database) as connection:
                entity_payload = connection.execute(
                    "SELECT payload FROM semantic_entity_archives").fetchone()[0]
            self.assertEqual(json.loads(entity_payload)["profile"], "semantic-entity-model-1")

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
