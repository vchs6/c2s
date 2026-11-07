from __future__ import annotations

import unittest

from c2s_skill.semantic_entity_migration import export_legacy_bundle, import_legacy_bundle


def entity():
    return {"ref": {"identity": {"authority": "test", "domainId": "scope-a", "localId": "known"},
                    "kind": "ComputationEntity"}, "name": "calculate", "aliases": [], "description": "",
            "attributes": [], "sourceKeys": ["source:calculate"], "observationViews": ["E2"]}


def legacy():
    subject = {"identity": {"authority": "test", "domainId": "scope-a", "localId": "known"},
               "kind": "function"}
    return {"version": "1.0.0", "profile": "semantic-fact-model-1", "registrations": [],
        "assessments": [], "facts": [{"factId": "f1", "predicate": "function.name", "subject": subject,
            "value": "calculate", "claimMode": "analysis", "condition": {"kind": "true"},
            "evidenceIds": ["ev-1"]}],
        "evidence": [{"evidenceId": "ev-1", "source": "source", "description": "源码声明"}],
        "coverage": [], "dependencies": [], "dependencyResolutions": [], "semanticStates": [],
        "diagnostics": [], "contextDomains": [], "contexts": []}


class SemanticEntityMigrationTests(unittest.TestCase):
    def test_import_requires_known_identity_and_preserves_claim_evidence(self):
        result = import_legacy_bundle(legacy(), "scope-a", [entity()])
        self.assertEqual(result["model"]["claims"][0]["claimId"], "legacy-f1")
        self.assertEqual(result["model"]["claims"][0]["evidenceIds"], ["ev-1"])
        self.assertEqual(result["losses"], [])

    def test_orphan_source_fact_is_reported_instead_of_promoted_to_entity(self):
        data = legacy()
        data["facts"][0]["subject"]["identity"]["localId"] = "orphan"
        result = import_legacy_bundle(data, "scope-a", [entity()])
        self.assertEqual(result["model"]["claims"], [])
        self.assertEqual(result["losses"][0]["code"], "LEGACY_SUBJECT_UNMAPPED")

    def test_m1_source_declaration_is_not_promoted_without_explicit_entity_mapping(self):
        data = {"version": "1.0.0", "profile": "m1-project-discovery-1",
            "registrations": [{"ref": {"identity": {"authority": "old", "domainId": "scope-a",
                "localId": "source"}, "kind": "SourceDeclaration"}, "sourceKey": "source:legacy",
                "evidenceIds": ["ev-1"]}], "facts": [],
            "evidence": [{"evidenceId": "ev-1", "source": "source", "description": "源码"}]}
        result = import_legacy_bundle(data, "scope-a", [])
        self.assertEqual(result["model"]["entities"], [])
        self.assertEqual(result["losses"][0]["code"], "LEGACY_REGISTRATION_UNMAPPED")

    def test_export_is_deterministic_and_declares_loss_free_supported_claim_projection(self):
        imported = import_legacy_bundle(legacy(), "scope-a", [entity()])
        first = export_legacy_bundle(imported["model"])
        second = export_legacy_bundle(imported["model"])
        self.assertEqual(first, second)
        self.assertEqual(first["bundle"]["facts"][0]["predicate"], "function.name")
        self.assertEqual(first["losses"], [])


if __name__ == "__main__":
    unittest.main()
