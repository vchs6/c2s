import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from c2s_semantic_contract.validation import register_m1, validate_model


def empty_bundle():
    return {"version": "1.0.0", "profile": "m1-project-discovery-1", "registrations": [],
            "assessments": [], "facts": [], "evidence": [], "coverage": [], "diagnostics": []}


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
        valid = validate_model(empty_bundle(), {})
        self.assertTrue(valid["valid"])
        self.assertEqual(valid["stages"]["structure"], "pass")

        invalid_bundle = empty_bundle()
        invalid_bundle["untypedPayload"] = {"hidden": "semantic body"}
        invalid = validate_model(invalid_bundle, {})
        self.assertFalse(invalid["valid"])
        self.assertEqual(invalid["stages"]["structure"], "fail")
        self.assertIn("CONTRACT_INVALID", {item["ruleCode"] for item in invalid["diagnostics"]})

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

        result = validate_model(bundle, {})

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

        result = validate_model(bundle, {})

        self.assertFalse(result["valid"])
        self.assertEqual(result["stages"]["invariants"], "fail")
        self.assertIn("BYTE_RANGE_INVALID", {item["ruleCode"] for item in result["diagnostics"]})

    def test_registration_references_require_existing_evidence_records(self):
        bundle = empty_bundle()
        registration = register_m1("domain-a", [], "SourceDeclaration", "py:main:entry", ["ev-missing"])
        bundle["registrations"].append(registration)

        result = validate_model(bundle, {})

        self.assertFalse(result["valid"])
        self.assertIn("EVIDENCE_REF_MISSING", {item["ruleCode"] for item in result["diagnostics"]})


if __name__ == "__main__":
    unittest.main()
