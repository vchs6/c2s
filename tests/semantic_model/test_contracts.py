import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from c2s_semantic_contract.validation import _manifest_integrity, register_m1, validate_model


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
