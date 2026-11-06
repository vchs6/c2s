import json
import hashlib
import sys
import unittest
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skill" / "src"))

from c2s_semantic_contract.validation import _manifest_integrity, register_m1, validate_model
from c2s_semantic_contract.projection import project_query_to_m1
from c2s_skill.inventory import source_fingerprint


def empty_bundle():
    return {"version": "1.0.0", "profile": "m1-project-discovery-1", "registrations": [],
            "assessments": [], "facts": [], "evidence": [], "coverage": [], "diagnostics": []}


def fixed_catalogs():
    root = Path(__file__).resolve().parents[2] / "contracts" / "semantic-model"
    return {name: json.loads((root / filename).read_text(encoding="utf-8"))
            for name, filename in (("types", "types.json"), ("predicates", "predicates.json"))}


def bundle_with_fact(predicate="project.name", subject_kind="Project", value="Example"):
    bundle = empty_bundle()
    identity = {"authority": "c2s-local", "domainId": "domain-a", "localId": "subject-a"}
    ref = {"identity": identity, "kind": subject_kind}
    bundle["registrations"].append({"ref": ref, "sourceKey": "manifest:project", "evidenceIds": ["ev-1"]})
    bundle["evidence"].append({"evidenceId": "ev-1", "source": "input", "path": "pyproject.toml",
        "artifactId": None, "originalPath": "pyproject.toml", "sha256": "a" * 64,
        "startByte": 0, "endByte": 1, "method": "tomllib", "toolName": None, "toolVersion": None})
    bundle["facts"].append({"factId": "fact-1", "predicate": predicate, "subject": ref, "value": value,
        "claimMode": "declaration", "condition": {"kind": "true"}, "evidenceIds": ["ev-1"]})
    return bundle


class M1IdentityTests(unittest.TestCase):
    def test_real_query_projection_builds_valid_m1_project_facts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = b'[project]\nname = "sample"\nrequires-python = ">=3.11"\n'
            (root / "pyproject.toml").write_bytes(source)
            facts = [SimpleNamespace(path="pyproject.toml", start_byte=10, end_byte=25,
                                     kind="project_name", name="sample", subject_id="project-1",
                                     claim_mode="declaration", owner=None, id="fact-name"),
                     SimpleNamespace(path="pyproject.toml", start_byte=26, end_byte=len(source),
                                     kind="language_declared", name="Python", subject_id="project-1",
                                     claim_mode="declaration", owner=None, id="fact-language")]
            query_result = SimpleNamespace(root=str(root), facts=tuple(facts), gaps=(), complete=True,
                                           source_digest=source_fingerprint(root))

            projection = project_query_to_m1(query_result)
            validation = validate_model(projection["bundle"], fixed_catalogs(), projection["sourceObservations"])

            self.assertTrue(validation["valid"])
            self.assertEqual({fact["predicate"] for fact in projection["bundle"]["facts"]},
                             {"project.name", "project.language_declared"})
            self.assertEqual(len({item["ref"]["identity"]["localId"]
                                  for item in projection["bundle"]["registrations"]}), 1)
            self.assertEqual(validation["consistency"], "undetermined")

    def test_real_query_projection_keeps_workspace_membership_typed_and_unchecked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = b'[workspace]\nmembers = ["crate"]\n'
            (root / "Cargo.toml").write_bytes(source)
            fact = SimpleNamespace(path="Cargo.toml", start_byte=0, end_byte=len(source),
                                   kind="workspace_member", name="crate", subject_id="package-1",
                                   claim_mode="cargo_metadata", owner="crate/Cargo.toml", id="fact-member")
            query_result = SimpleNamespace(root=str(root), facts=(fact,), gaps=(), complete=True,
                                           source_digest=source_fingerprint(root))

            projection = project_query_to_m1(query_result)
            bundle = projection["bundle"]
            membership = bundle["facts"][0]
            validation = validate_model(bundle, fixed_catalogs(), projection["sourceObservations"])

            self.assertTrue(validation["valid"])
            self.assertEqual(membership["predicate"], "workspace.member")
            self.assertEqual(membership["subject"]["kind"], "NativeWorkspace")
            self.assertEqual(membership["value"]["kind"], "PackageSpecification")
            self.assertFalse(bundle["coverage"][0]["complete"])
            self.assertIn("EVIDENCE_UNCHECKED", {item["code"] for item in bundle["coverage"][0]["diagnostics"]})

    def test_workspace_projection_captures_and_binds_cargo_metadata_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = b'[workspace]\nmembers = ["crate"]\n'
            (root / "Cargo.toml").write_bytes(source)
            fact = SimpleNamespace(path="Cargo.toml", start_byte=0, end_byte=len(source),
                                   kind="workspace_member", name="crate", subject_id="package-1",
                                   claim_mode="cargo_metadata", owner="crate/Cargo.toml", id="fact-member")
            query_result = SimpleNamespace(root=str(root), facts=(fact,), gaps=(), complete=True,
                                           source_digest=source_fingerprint(root))
            metadata_output = json.dumps({"packages": [{"name": "crate"}]})
            cargo_metadata = subprocess.CompletedProcess([], 0, metadata_output, "")
            cargo_version = subprocess.CompletedProcess([], 0, "cargo 1.0.0\n", "")
            with patch("c2s_semantic_contract.projection.shutil.which", return_value="/fake/cargo"), \
                    patch("c2s_semantic_contract.projection.subprocess.run",
                          side_effect=[cargo_metadata, cargo_version]):
                projection = project_query_to_m1(query_result)

            bundle = projection["bundle"]
            evidence = bundle["evidence"][0]
            attachment = projection["artifacts"][0]
            validation = validate_model(bundle, fixed_catalogs(), projection["sourceObservations"])
            self.assertEqual(evidence["source"], "tool_output")
            self.assertEqual(evidence["artifactId"], attachment["artifactId"])
            self.assertEqual(hashlib.sha256(attachment["content"].encode()).hexdigest(), evidence["sha256"])
            self.assertEqual(projection["sourceObservations"]["items"][0]["status"], "verified")
            self.assertTrue(bundle["coverage"][0]["complete"])
            self.assertTrue(validation["valid"])

    def test_projection_rejects_sources_changed_after_query_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = b'[project]\nname = "before"\n'
            manifest = root / "pyproject.toml"
            manifest.write_bytes(source)
            fact = SimpleNamespace(path="pyproject.toml", start_byte=10, end_byte=25,
                                   kind="project_name", name="before", subject_id="project-1",
                                   claim_mode="declaration", owner=None, id="fact-before")
            query_result = SimpleNamespace(root=str(root), facts=(fact,), gaps=(), complete=True,
                                           source_digest=source_fingerprint(root))
            manifest.write_bytes(b'[project]\nname = "after"\n')

            with self.assertRaisesRegex(ValueError, "sources changed"):
                project_query_to_m1(query_result)

    @staticmethod
    def assessment(assessment_id, declaration, status, projects, *, rule_id="boundary-v1", supersedes=None):
        return {"assessmentId": assessment_id, "declaration": declaration, "status": status,
                "projects": projects, "ruleId": rule_id, "evidenceIds": ["ev-assessment"],
                "supersedes": supersedes or [], "diagnostics": []}

    @staticmethod
    def assessment_bundle(assessments):
        bundle = empty_bundle()
        declaration = {"identity": {"authority": "c2s-local", "domainId": "domain-a", "localId": "decl"},
                       "kind": "SourceDeclaration"}
        project_a = {"identity": {"authority": "c2s-local", "domainId": "domain-a", "localId": "project-a"},
                     "kind": "Project"}
        project_b = {"identity": {"authority": "c2s-local", "domainId": "domain-a", "localId": "project-b"},
                     "kind": "Project"}
        bundle["registrations"] = [
            {"ref": ref, "sourceKey": f"source:{ref['kind']}:{ref['identity']['localId']}",
             "evidenceIds": ["ev-assessment"]} for ref in (declaration, project_a, project_b)]
        bundle["evidence"].append({"evidenceId": "ev-assessment", "source": "input", "path": "project.toml",
            "artifactId": None, "originalPath": "project.toml", "sha256": "a" * 64,
            "startByte": 0, "endByte": 1, "method": "fixture", "toolName": None, "toolVersion": None})
        bundle["assessments"] = [
            M1IdentityTests.assessment(item["assessmentId"], declaration, item["status"],
                                       [project_a if name == "a" else project_b for name in item["projects"]],
                                       rule_id=item.get("ruleId", "boundary-v1"), supersedes=item.get("supersedes"))
            for item in assessments]
        return bundle

    def test_registration_reuses_identity_and_merges_new_evidence(self):
        first = register_m1("domain-a", [], "SourceDeclaration", "python:module:entry", ["ev-1"])
        second = register_m1("domain-a", [first], "SourceDeclaration", "python:module:entry", ["ev-2"])

        self.assertEqual(second["ref"]["identity"], first["ref"]["identity"])
        self.assertEqual(second["evidenceIds"], ["ev-1", "ev-2"])
        self.assertEqual(second["sourceKey"], "python:module:entry")
        self.assertNotIn("path", second["ref"]["identity"])
        second["ref"]["identity"]["localId"] = "caller-mutated"
        self.assertNotEqual(first["ref"]["identity"]["localId"], "caller-mutated")

    def test_registration_rejects_source_key_kind_conflict(self):
        first = register_m1("domain-a", [], "SourceDeclaration", "python:module:entry", ["ev-1"])
        result = register_m1("domain-a", [first], "Project", "python:module:entry", ["ev-2"])

        self.assertEqual(result["code"], "CONTRACT_INVALID")
        self.assertEqual(result["severity"], "error")
        self.assertEqual(result["recordId"], first["ref"]["identity"]["localId"])

    def test_registration_rejects_malformed_registry_inputs_without_crashing(self):
        result = register_m1("domain-a", [None], "SourceDeclaration", "py:main:entry", ["ev-1"])
        self.assertEqual(result["code"], "CONTRACT_INVALID")

    def test_m1_schema_accepts_its_versioned_bundle_and_rejects_unknown_fields(self):
        valid = validate_model(empty_bundle(), fixed_catalogs())
        self.assertTrue(valid["valid"])
        self.assertEqual(valid["stages"]["structure"], "pass")

        invalid_bundle = empty_bundle()
        invalid_bundle["untypedPayload"] = {"hidden": "semantic body"}
        invalid = validate_model(invalid_bundle, fixed_catalogs())
        self.assertFalse(invalid["valid"])
        self.assertEqual(invalid["stages"]["structure"], "fail")
        self.assertIn("CONTRACT_INVALID", {item["ruleCode"] for item in invalid["diagnostics"]})

    def test_model_validation_rejects_missing_fixed_catalogs_before_structure(self):
        result = validate_model(empty_bundle(), {})
        self.assertFalse(result["valid"])
        self.assertEqual(result["stages"]["catalog"], "fail")
        self.assertEqual(result["stages"]["structure"], "not_run")
        self.assertIn("CATALOG_BUNDLE_MISMATCH", {item["ruleCode"] for item in result["diagnostics"]})

    def test_failed_structure_stops_references_and_invariants(self):
        bundle = empty_bundle()
        bundle["extra"] = True

        result = validate_model(bundle, fixed_catalogs())

        self.assertEqual(result["stages"], {
            "catalog": "pass", "structure": "fail", "references": "not_run", "invariants": "not_run"})
        self.assertFalse(result["valid"])
        self.assertEqual(result["consistency"], "undetermined")

    def test_reference_failure_stops_invariants_without_hiding_conflict(self):
        bundle = empty_bundle()
        ref_a = {"identity": {"authority": "c2s-local", "domainId": "domain-a", "localId": "same"},
                 "kind": "Project"}
        ref_b = {"identity": dict(ref_a["identity"]), "kind": "PackageSpecification"}
        bundle["registrations"] = [
            {"ref": ref_a, "sourceKey": "source:a", "evidenceIds": ["ev-a"]},
            {"ref": ref_b, "sourceKey": "source:b", "evidenceIds": ["ev-b"]},
        ]

        result = validate_model(bundle, fixed_catalogs())

        self.assertEqual(result["stages"]["references"], "fail")
        self.assertEqual(result["stages"]["invariants"], "not_run")
        self.assertEqual(result["consistency"], "undetermined")
        conflict = next(item for item in result["diagnostics"] if item["ruleCode"] == "IDENTITY_KIND_CONFLICT")
        self.assertEqual(conflict["recordRef"], "registration:1")
        self.assertEqual(conflict["relatedRefs"], ["registration:0"])

    def test_valid_checked_subset_is_never_reported_as_semantically_consistent(self):
        result = validate_model(empty_bundle(), fixed_catalogs())

        self.assertTrue(result["valid"])
        self.assertEqual(result["stages"]["invariants"], "partial")
        self.assertEqual(result["consistency"], "undetermined")

    def test_project_boundary_assessments_enforce_status_cardinality(self):
        cases = [("resolved", ["a"], True), ("ambiguous", ["a", "b"], True),
                 ("unresolved", [], True), ("resolved", [], False),
                 ("ambiguous", ["a"], False), ("unresolved", ["a"], False)]
        for status, project_keys, expected_valid in cases:
            with self.subTest(status=status, projects=project_keys):
                result = validate_model(self.assessment_bundle([{
                    "assessmentId": "assessment-1", "status": status, "projects": project_keys}]), fixed_catalogs())
                self.assertEqual(result["valid"], expected_valid)
                if not expected_valid:
                    self.assertIn("ASSESSMENT_CARDINALITY", {item["ruleCode"] for item in result["diagnostics"]})

    def test_assessment_supersedes_must_preserve_declaration_and_rule_and_be_acyclic(self):
        base = {"assessmentId": "assessment-1", "status": "resolved", "projects": ["a"]}
        replacement = {"assessmentId": "assessment-2", "status": "resolved", "projects": ["a"],
                       "supersedes": ["assessment-1"]}
        self.assertTrue(validate_model(self.assessment_bundle([base, replacement]), fixed_catalogs())["valid"])

        wrong_rule = dict(replacement, ruleId="boundary-v2")
        result = validate_model(self.assessment_bundle([base, wrong_rule]), fixed_catalogs())
        self.assertIn("SUPERSEDES_KEY_MISMATCH", {item["ruleCode"] for item in result["diagnostics"]})

        cycle_base = dict(base, supersedes=["assessment-2"])
        cycle_replacement = dict(replacement, supersedes=["assessment-1"])
        result = validate_model(self.assessment_bundle([cycle_base, cycle_replacement]), fixed_catalogs())
        self.assertIn("SUPERSEDES_CYCLE", {item["ruleCode"] for item in result["diagnostics"]})

    def test_source_observations_distinguish_unchecked_matching_and_mismatched_evidence(self):
        bundle = bundle_with_fact()
        unchecked = validate_model(bundle, fixed_catalogs())
        self.assertTrue(unchecked["valid"])
        self.assertIn("EVIDENCE_UNCHECKED", {item["ruleCode"] for item in unchecked["diagnostics"]})
        matching = validate_model(bundle, fixed_catalogs(), {"items": [
            {"evidenceId": "ev-1", "status": "verified", "observedSha256": "a" * 64}]})
        self.assertNotIn("EVIDENCE_UNCHECKED", {item["ruleCode"] for item in matching["diagnostics"]})
        mismatch = validate_model(bundle, fixed_catalogs(), {"items": [
            {"evidenceId": "ev-1", "status": "mismatch", "observedSha256": "b" * 64}]})
        self.assertFalse(mismatch["valid"])
        self.assertIn("INPUT_MISMATCH", {item["ruleCode"] for item in mismatch["diagnostics"]})

    def test_invalid_source_observation_shapes_fail_invariants(self):
        bundle = bundle_with_fact()
        observations = {"items": [{"evidenceId": "ev-1", "status": "verified", "observedSha256": None}]}
        result = validate_model(bundle, fixed_catalogs(), observations)
        self.assertFalse(result["valid"])
        self.assertIn("OBSERVATION_INVALID", {item["ruleCode"] for item in result["diagnostics"]})

        malformed_status = {"items": [{"evidenceId": "ev-1", "status": [], "observedSha256": None}]}
        result = validate_model(bundle, fixed_catalogs(), malformed_status)
        self.assertIn("OBSERVATION_INVALID", {item["ruleCode"] for item in result["diagnostics"]})

    def test_coverage_complete_cannot_hide_gap_diagnostics(self):
        bundle = empty_bundle()
        bundle["coverage"] = [{"coverageId": "coverage-1", "selector": "project", "subject": None,
            "checkedPaths": [], "evidenceIds": [], "complete": True, "supersedes": [],
            "resolvedDiagnosticKeys": [], "diagnostics": [{"code": "READ_FAILED", "severity": "gap",
            "recordId": "file:a.py", "path": "a.py", "message": "Could not read file."}]}]
        result = validate_model(bundle, fixed_catalogs())
        self.assertFalse(result["valid"])
        self.assertIn("COVERAGE_COMPLETE_WITH_GAPS", {item["ruleCode"] for item in result["diagnostics"]})

    def test_coverage_lineage_requires_same_selector_and_subject_and_is_acyclic(self):
        bundle = empty_bundle()
        bundle["registrations"].append({"ref": {"identity": {"authority": "c2s-local", "domainId": "d", "localId": "p"},
            "kind": "Project"}, "sourceKey": "project:p", "evidenceIds": ["ev"]})
        bundle["evidence"].append({"evidenceId": "ev", "source": "input", "path": "x", "artifactId": None,
            "originalPath": "x", "sha256": "a" * 64, "startByte": 0, "endByte": 1, "method": "test",
            "toolName": None, "toolVersion": None})
        subject = bundle["registrations"][0]["ref"]
        old = {"coverageId": "coverage-old", "selector": "project", "subject": subject, "checkedPaths": [],
            "evidenceIds": [], "complete": False, "supersedes": [], "resolvedDiagnosticKeys": [],
            "diagnostics": [{"code": "READ_FAILED", "severity": "gap", "recordId": "x", "path": "x",
                             "message": "read failed"}]}
        new = dict(old, coverageId="coverage-new", complete=True, supersedes=["coverage-old"],
                   resolvedDiagnosticKeys=['["READ_FAILED","x","x"]'], diagnostics=[])
        bundle["coverage"] = [old, new]
        self.assertTrue(validate_model(bundle, fixed_catalogs())["valid"])

        wrong_key = dict(new, selector="functions")
        result = validate_model(dict(bundle, coverage=[old, wrong_key]), fixed_catalogs())
        self.assertIn("SUPERSEDES_KEY_MISMATCH", {item["ruleCode"] for item in result["diagnostics"]})

        cycle_old = dict(old, supersedes=["coverage-new"])
        result = validate_model(dict(bundle, coverage=[cycle_old, new]), fixed_catalogs())
        self.assertIn("SUPERSEDES_CYCLE", {item["ruleCode"] for item in result["diagnostics"]})

    def test_closed_m1_catalog_accepts_project_name_with_a_project_subject(self):
        result = validate_model(bundle_with_fact(), fixed_catalogs())
        self.assertTrue(result["valid"])
        self.assertEqual(result["stages"]["catalog"], "pass")
        self.assertEqual(result["stages"]["invariants"], "partial")

    def test_closed_m1_catalog_rejects_unknown_fact_predicates(self):
        result = validate_model(bundle_with_fact(predicate="project.unknown"), fixed_catalogs())
        self.assertFalse(result["valid"])
        self.assertIn("UNSUPPORTED_PREDICATE", {item["ruleCode"] for item in result["diagnostics"]})

    def test_closed_m1_catalog_rejects_wrong_subject_role_kind(self):
        result = validate_model(bundle_with_fact(predicate="workspace.member", subject_kind="Project"), fixed_catalogs())
        self.assertFalse(result["valid"])
        self.assertIn("ROLE_TYPE_MISMATCH", {item["ruleCode"] for item in result["diagnostics"]})

    def test_single_value_claim_conflicts_remain_valid_and_preserve_both_facts(self):
        bundle = bundle_with_fact(value="first")
        conflicting = dict(bundle["facts"][0], factId="fact-2", value="second")
        bundle["facts"].append(conflicting)

        result = validate_model(bundle, fixed_catalogs())

        self.assertTrue(result["valid"])
        self.assertEqual(result["consistency"], "conflicting")
        self.assertEqual(len(bundle["facts"]), 2)
        conflicts = [item for item in result["diagnostics"] if item["ruleCode"] == "SINGLE_VALUE_CONFLICT"]
        self.assertEqual({item["recordRef"] for item in conflicts}, {"fact:fact-1", "fact:fact-2"})
        self.assertTrue(all(item["severity"] == "conflict" for item in conflicts))

    def test_single_value_comparison_does_not_cross_claim_modes(self):
        bundle = bundle_with_fact(value="declared name")
        second = dict(bundle["facts"][0], factId="fact-2", value="interpreted name", claimMode="interpretation")
        bundle["facts"].append(second)

        result = validate_model(bundle, fixed_catalogs())

        self.assertTrue(result["valid"])
        self.assertEqual(result["consistency"], "undetermined")
        self.assertNotIn("SINGLE_VALUE_CONFLICT", {item["ruleCode"] for item in result["diagnostics"]})

    def test_single_value_conflict_detection_respects_disjoint_contexts(self):
        bundle = bundle_with_fact(value="linux-name")
        bundle["profile"] = "semantic-fact-model-1"
        second = dict(bundle["facts"][0], factId="fact-2", value="windows-name",
                       subject=dict(bundle["facts"][0]["subject"]))
        bundle["facts"].append(second)
        bundle["contextDomains"] = [{"keyId": "target", "values": ["linux", "windows"]}]
        bundle["facts"][0]["condition"] = {"kind": "eq", "key": "target", "value": "linux"}
        second["condition"] = {"kind": "eq", "key": "target", "value": "windows"}

        result = validate_model(bundle, fixed_catalogs())

        self.assertTrue(result["valid"])
        self.assertEqual(result["consistency"], "undetermined")
        self.assertNotIn("SINGLE_VALUE_CONFLICT", {item["ruleCode"] for item in result["diagnostics"]})

    def test_overlapping_unknown_conditions_yield_potential_conflict(self):
        bundle = bundle_with_fact(value="first")
        bundle["profile"] = "semantic-fact-model-1"
        second = dict(bundle["facts"][0], factId="fact-2", value="second")
        bundle["facts"].append(second)
        bundle["facts"][0]["condition"] = {"kind": "source", "expression": "target feature"}
        second["condition"] = {"kind": "true"}

        result = validate_model(bundle, fixed_catalogs())

        self.assertTrue(result["valid"])
        potential = [item for item in result["diagnostics"] if item["ruleCode"] == "POTENTIAL_CONFLICT"]
        self.assertEqual({item["recordRef"] for item in potential}, {"fact:fact-1", "fact:fact-2"})
        self.assertEqual(result["consistency"], "undetermined")

    def test_contradictory_fact_condition_is_a_contract_error(self):
        bundle = bundle_with_fact()
        bundle["profile"] = "semantic-fact-model-1"
        bundle["contextDomains"] = [{"keyId": "target", "values": ["linux", "windows"]}]
        bundle["facts"][0]["condition"] = {"kind": "all", "conditions": [
            {"kind": "eq", "key": "target", "value": "linux"},
            {"kind": "eq", "key": "target", "value": "windows"}]}

        result = validate_model(bundle, fixed_catalogs())

        self.assertFalse(result["valid"])
        self.assertIn("CTX_CONTRADICTION", {item["ruleCode"] for item in result["diagnostics"]})

    def test_contextual_references_do_not_duplicate_subject_identity(self):
        bundle = bundle_with_fact(value="linux-name")
        bundle["profile"] = "semantic-fact-model-1"
        second = dict(bundle["facts"][0], factId="fact-2", value="windows-name",
                       subject=dict(bundle["facts"][0]["subject"]))
        bundle["facts"].append(second)
        bundle["contextDomains"] = [{"keyId": "target", "values": ["linux", "windows"]}]
        bundle["contexts"] = [
            {"contextId": "context-linux", "assignments": {"target": "linux"}},
            {"contextId": "context-windows", "assignments": {"target": "windows"}},
        ]
        bundle["facts"][0]["subject"]["contextRef"] = "context-linux"
        second["subject"]["contextRef"] = "context-windows"

        result = validate_model(bundle, fixed_catalogs())

        self.assertTrue(result["valid"])
        self.assertEqual(bundle["facts"][0]["subject"]["identity"],
                         bundle["facts"][1]["subject"]["identity"])
        self.assertNotIn("SINGLE_VALUE_CONFLICT", {item["ruleCode"] for item in result["diagnostics"]})

    def test_unknown_context_reference_fails_reference_stage(self):
        bundle = bundle_with_fact()
        bundle["profile"] = "semantic-fact-model-1"
        bundle["facts"][0]["subject"]["contextRef"] = "missing-context"

        result = validate_model(bundle, fixed_catalogs())

        self.assertEqual(result["stages"]["references"], "fail")
        self.assertIn("CONTEXT_REF_MISSING", {item["ruleCode"] for item in result["diagnostics"]})

    def test_m1_profile_rejects_context_features(self):
        bundle = bundle_with_fact()
        bundle["facts"][0]["condition"] = {"kind": "false"}

        result = validate_model(bundle, fixed_catalogs())

        self.assertFalse(result["valid"])
        self.assertIn("M1_CONTEXT_UNSUPPORTED", {item["ruleCode"] for item in result["diagnostics"]})

    def test_context_domain_rejects_mixed_value_types(self):
        bundle = bundle_with_fact()
        bundle["profile"] = "semantic-fact-model-1"
        bundle["contextDomains"] = [{"keyId": "target", "values": ["linux", True]}]

        result = validate_model(bundle, fixed_catalogs())

        self.assertFalse(result["valid"])
        self.assertIn("CONTEXT_DOMAIN_INVALID", {item["ruleCode"] for item in result["diagnostics"]})

    def test_dependency_resolution_cardinality_is_explicit_and_scope_is_independent(self):
        bundle = bundle_with_fact()
        bundle["profile"] = "semantic-fact-model-1"
        provider = {"identity": {"authority": "cargo", "domainId": "registry", "localId": "serde"},
                    "kind": "PackageSpecification"}
        bundle["registrations"].append({"ref": provider, "sourceKey": "registry:serde", "evidenceIds": ["ev-1"]})
        requirement = {"dependencyId": "dep-1", "consumer": bundle["facts"][0]["subject"],
            "purpose": "build", "stage": "compile", "path": None, "version": "^1",
            "condition": {"kind": "true"}, "evidenceIds": ["ev-1"]}
        bundle["dependencies"] = [requirement]
        bundle["dependencyResolutions"] = [{"resolutionId": "res-1", "dependencyId": "dep-1",
            "status": "resolved", "providers": [provider], "configuration": "linux",
            "visibility": "registry", "scopePosition": "outside", "evidenceIds": ["ev-1"]}]

        result = validate_model(bundle, fixed_catalogs())

        self.assertTrue(result["valid"])
        self.assertEqual(result["consistency"], "undetermined")

    def test_dependency_resolution_rejects_status_cardinality_mismatch(self):
        bundle = bundle_with_fact()
        bundle["profile"] = "semantic-fact-model-1"
        bundle["dependencies"] = [{"dependencyId": "dep-1", "consumer": bundle["facts"][0]["subject"],
            "purpose": "build", "stage": "compile", "path": None, "version": None,
            "condition": {"kind": "true"}, "evidenceIds": ["ev-1"]}]
        bundle["dependencyResolutions"] = [{"resolutionId": "res-1", "dependencyId": "dep-1",
            "status": "resolved", "providers": [], "configuration": None, "visibility": None,
            "scopePosition": "unknown", "evidenceIds": ["ev-1"]}]

        result = validate_model(bundle, fixed_catalogs())

        self.assertFalse(result["valid"])
        self.assertIn("DEPENDENCY_CARDINALITY", {item["ruleCode"] for item in result["diagnostics"]})

    def test_dependency_condition_contradiction_is_not_silently_dropped(self):
        bundle = bundle_with_fact()
        bundle["profile"] = "semantic-fact-model-1"
        bundle["contextDomains"] = [{"keyId": "target", "values": ["linux", "windows"]}]
        bundle["contexts"] = [{"contextId": "linux", "assignments": {"target": "linux"}}]
        consumer = dict(bundle["facts"][0]["subject"], contextRef="linux")
        bundle["dependencies"] = [{"dependencyId": "dep-1", "consumer": consumer, "purpose": "build",
            "stage": "compile", "path": None, "version": None,
            "condition": {"kind": "eq", "key": "target", "value": "windows"}, "evidenceIds": ["ev-1"]}]

        result = validate_model(bundle, fixed_catalogs())

        self.assertFalse(result["valid"])
        self.assertIn("DEPENDENCY_CONDITION_CONTRADICTION", {item["ruleCode"] for item in result["diagnostics"]})

    def test_resolved_dependency_cycle_is_reported_without_becoming_contract_error(self):
        bundle = bundle_with_fact()
        bundle["profile"] = "semantic-fact-model-1"
        project = bundle["facts"][0]["subject"]
        package = {"identity": {"authority": "cargo", "domainId": "registry", "localId": "serde"},
                   "kind": "PackageSpecification"}
        bundle["registrations"].append({"ref": package, "sourceKey": "registry:serde", "evidenceIds": ["ev-1"]})
        bundle["contextDomains"] = [{"keyId": "x", "values": ["A", "B"]}]
        bundle["dependencies"] = [
            {"dependencyId": "a-to-b", "consumer": project, "purpose": "build", "stage": "compile",
             "path": None, "version": None, "condition": {"kind": "eq", "key": "x", "value": "A"},
             "evidenceIds": ["ev-1"]},
            {"dependencyId": "b-to-a", "consumer": package, "purpose": "build", "stage": "compile",
             "path": None, "version": None, "condition": {"kind": "eq", "key": "x", "value": "B"},
             "evidenceIds": ["ev-1"]},
        ]
        bundle["dependencyResolutions"] = [
            {"resolutionId": "res-a", "dependencyId": "a-to-b", "status": "resolved", "providers": [package],
             "configuration": "default", "visibility": "local", "scopePosition": "inside", "evidenceIds": ["ev-1"]},
            {"resolutionId": "res-b", "dependencyId": "b-to-a", "status": "resolved", "providers": [project],
             "configuration": "default", "visibility": "local", "scopePosition": "inside", "evidenceIds": ["ev-1"]},
        ]

        result = validate_model(bundle, fixed_catalogs())

        self.assertTrue(result["valid"])
        self.assertEqual(result["dependencyCycles"][0]["configuration"], "default")
        self.assertEqual(result["dependencyCycles"][0]["cycles"][0]["status"], "infeasible")

    def test_catalog_rejects_unsupported_constraint_ids(self):
        catalogs = fixed_catalogs()
        catalogs["predicates"]["predicates"][0]["constraints"].append("UNSAFE_EVAL")
        result = validate_model(empty_bundle(), catalogs)
        self.assertFalse(result["valid"])
        self.assertEqual(result["stages"]["catalog"], "fail")
        self.assertIn("RULE_UNSUPPORTED", {item["ruleCode"] for item in result["diagnostics"]})

    def test_catalog_rejects_same_version_content_drift(self):
        catalogs = fixed_catalogs()
        catalogs["predicates"]["predicates"][0]["description"] = "changed semantics"
        result = validate_model(empty_bundle(), catalogs)
        self.assertFalse(result["valid"])
        self.assertIn("CATALOG_BUNDLE_MISMATCH", {item["ruleCode"] for item in result["diagnostics"]})

    def test_m1_predicate_directory_keeps_layer_roles_and_claim_comparison_explicit(self):
        test_root = Path(__file__).resolve().parent
        expected = json.loads((test_root / "fixtures/predicates.json").read_text(encoding="utf-8"))
        predicates = fixed_catalogs()["predicates"]["predicates"]
        self.assertEqual(expected["version"], fixed_catalogs()["predicates"]["version"])
        self.assertEqual(expected["profile"], fixed_catalogs()["predicates"]["profile"])
        self.assertEqual({item["predicateId"] for item in predicates}, set(expected["expectedPredicateIds"]))
        for predicate in predicates:
            self.assertEqual(predicate["category"], "Semantic")
            self.assertEqual(predicate["primaryLayer"], expected["primaryLayer"])
            self.assertEqual(predicate["relationKind"], expected["relationKinds"][predicate["predicateId"]])
            role_by_position = {role["position"]: role for role in predicate["roles"]}
            self.assertEqual(set(role_by_position), {"subject", "value"})
            self.assertEqual(role_by_position["subject"]["allowedKinds"], expected["subjectKinds"][predicate["predicateId"]])
            value_kinds = expected["valueKinds"][predicate["predicateId"]]
            if isinstance(value_kinds, list):
                self.assertEqual(role_by_position["value"]["allowedKinds"], value_kinds)
                self.assertEqual(role_by_position["value"]["valueType"], "M1SubjectRef")
            else:
                self.assertEqual(role_by_position["value"]["valueType"], value_kinds)
            self.assertIn(predicate["claimCardinality"], {"single_value_per_context", "multi_value"})
            self.assertEqual(predicate["comparisonPolicy"], "same_claim_mode_only")

    def test_catalog_rejects_dangling_type_references_and_mixed_versions(self):
        catalogs = fixed_catalogs()
        catalogs["types"]["types"][0]["fields"]["authority"]["type"] = "MissingType"
        invalid_type = validate_model(empty_bundle(), catalogs)
        self.assertEqual(invalid_type["stages"]["catalog"], "fail")
        self.assertIn("CATALOG_TYPE_REF_MISSING", {item["ruleCode"] for item in invalid_type["diagnostics"]})

        catalogs = fixed_catalogs()
        catalogs["types"]["version"] = "2.0.0"
        mixed_version = validate_model(empty_bundle(), catalogs)
        self.assertEqual(mixed_version["stages"]["catalog"], "fail")
        self.assertEqual(mixed_version["stages"]["structure"], "not_run")

    def test_catalog_rejects_malformed_predicate_roles(self):
        catalogs = fixed_catalogs()
        del catalogs["predicates"]["predicates"][0]["roles"]
        result = validate_model(empty_bundle(), catalogs)
        self.assertFalse(result["valid"])
        self.assertEqual(result["stages"]["catalog"], "fail")
        self.assertIn("CATALOG_INVALID", {item["ruleCode"] for item in result["diagnostics"]})

    def test_catalog_manifest_digest_is_pinned_to_the_contract_implementation(self):
        root = Path(__file__).resolve().parents[2] / "contracts" / "semantic-model"
        manifest = json.loads((root / "catalog-manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(_manifest_integrity(manifest))
        manifest["ruleSetId"] = "replacement-rules"
        self.assertFalse(_manifest_integrity(manifest))

    def test_validation_rejects_an_unregistered_internal_subject_reference(self):
        bundle = empty_bundle()
        bundle["evidence"].append({"evidenceId": "ev-1", "source": "input", "path": "main.py",
            "artifactId": None, "originalPath": "src/main.py", "sha256": "a" * 64,
            "startByte": 0, "endByte": 1, "method": "python-ast", "toolName": None,
            "toolVersion": None})
        bundle["facts"].append({"factId": "fact-1", "predicate": "project.name",
            "subject": {"identity": {"authority": "c2s-local", "domainId": "domain-a", "localId": "id-a"},
                        "kind": "Project"},
            "value": "example", "claimMode": "declaration", "condition": {"kind": "true"},
            "evidenceIds": ["ev-1"]})

        result = validate_model(bundle, fixed_catalogs())

        self.assertFalse(result["valid"])
        self.assertIn("INTERNAL_REF_MISSING", {item["ruleCode"] for item in result["diagnostics"]})
        self.assertEqual(result["stages"]["structure"], "pass")
        self.assertEqual(result["stages"]["references"], "fail")

    def test_validation_rejects_an_inverted_source_byte_range(self):
        bundle = empty_bundle()
        bundle["evidence"].append({"evidenceId": "ev-1", "source": "input", "path": "main.py",
            "artifactId": None, "originalPath": "src/main.py", "sha256": "a" * 64,
            "startByte": 5, "endByte": 4, "method": "python-ast", "toolName": None,
            "toolVersion": None})

        result = validate_model(bundle, fixed_catalogs())

        self.assertFalse(result["valid"])
        self.assertEqual(result["stages"]["invariants"], "fail")
        self.assertIn("BYTE_RANGE_INVALID", {item["ruleCode"] for item in result["diagnostics"]})

    def test_registration_references_require_existing_evidence_records(self):
        bundle = empty_bundle()
        registration = register_m1("domain-a", [], "SourceDeclaration", "py:main:entry", ["ev-missing"])
        bundle["registrations"].append(registration)

        result = validate_model(bundle, fixed_catalogs())

        self.assertFalse(result["valid"])
        self.assertIn("EVIDENCE_REF_MISSING", {item["ruleCode"] for item in result["diagnostics"]})


if __name__ == "__main__":
    unittest.main()
