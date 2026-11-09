"""语义实体模型契约的公开行为测试。"""

from __future__ import annotations

import sys
import unittest
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from _historical_validation import (
    _validate_semantic_entity_catalogs,
    validate_semantic_entity_model,
)
import _historical_validation as validation_module


def entity_ref(local_id: str, kind: str = "DataEntity") -> dict:
    return {"identity": {"authority": "test", "domainId": "scope-a", "localId": local_id},
            "kind": kind}


def valid_entity_model() -> dict:
    project = entity_ref("project", "Project")
    record = entity_ref("record")
    return {
        "version": "1.0.0",
        "profile": "semantic-entity-model-1",
        "scopeId": "scope-a",
        "entities": [
            {"ref": project, "name": "Example", "aliases": [], "description": "项目",
             "attributes": [], "sourceKeys": [], "observationViews": ["E0"]},
            {"ref": record, "name": "订单", "aliases": ["Order"], "description": "订单数据",
             "attributes": [{"attributeId": "record.status", "name": "状态", "semanticType": "状态",
                             "implementationType": "String", "valueRange": {"kind": "unknown"},
                             "cardinality": "one", "constraints": [], "evidenceIds": ["ev-1"]}],
             "sourceKeys": ["src:record"], "observationViews": ["E2"]}],
        "claims": [],
        "relations": [{"relationId": "r1", "predicate": "defines", "subject": project,
                       "target": record, "evidenceIds": ["ev-1"], "condition": {"kind": "true"}}],
        "continuityCandidates": [],
        "evidence": [{"evidenceId": "ev-1", "source": "source", "description": "声明证据"}],
        "coverage": [{"coverageId": "cov-1", "entity": record, "selector": "attributes",
                      "status": "obtained", "inputFingerprint": "sha256:abc",
                      "analyzerVersion": "1.0.0"}],
    }


class SemanticEntityModelContractTests(unittest.TestCase):
    def test_valid_entity_model_separates_semantic_and_implementation_types(self):
        result = validate_semantic_entity_model(valid_entity_model())
        self.assertTrue(result["valid"], result["diagnostics"])

    def test_versioned_entity_catalogs_and_schema_are_pinned_together(self):
        catalogs, diagnostics = _validate_semantic_entity_catalogs()
        self.assertEqual([], diagnostics)
        self.assertEqual("semantic-entity-model-1", catalogs["types"]["profile"])

    def test_catalog_and_manifest_cannot_be_rewritten_together(self):
        source_root = ROOT / "contracts" / "semantic-model"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            filenames = ["semantic-entity-types.json", "semantic-entity-predicates.json",
                         "semantic-entity-model.schema.json", "semantic-entity-catalog-manifest.json"]
            for filename in filenames:
                shutil.copyfile(source_root / filename, root / filename)
            types_path = root / filenames[0]
            types = json.loads(types_path.read_text(encoding="utf-8"))
            types["types"][0]["description"] = "被未授权改写的实体类型"
            types_path.write_text(json.dumps(types, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            manifest_path = root / filenames[3]
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["digests"][filenames[0]] = hashlib.sha256(json.dumps(
                types, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            with patch.multiple(validation_module,
                _SEMANTIC_ENTITY_TYPES_PATH=root / filenames[0],
                _SEMANTIC_ENTITY_PREDICATES_PATH=root / filenames[1],
                _SEMANTIC_ENTITY_SCHEMA_PATH=root / filenames[2],
                _SEMANTIC_ENTITY_MANIFEST_PATH=manifest_path):
                _, diagnostics = _validate_semantic_entity_catalogs()
        self.assertIn("ENTITY_CATALOG_DIGEST_MISMATCH", {item["ruleCode"] for item in diagnostics})

    def test_entity_identity_domain_must_match_analysis_scope(self):
        document = valid_entity_model()
        document["entities"][1]["ref"]["identity"]["domainId"] = "other-scope"
        result = validate_semantic_entity_model(document)
        self.assertFalse(result["valid"])
        self.assertIn("ENTITY_SCOPE_MISMATCH", {item["ruleCode"] for item in result["diagnostics"]})

    def test_attribute_evidence_references_must_resolve(self):
        document = valid_entity_model()
        document["entities"][1]["attributes"][0]["evidenceIds"] = ["missing-evidence"]
        result = validate_semantic_entity_model(document)
        self.assertFalse(result["valid"])
        self.assertIn("ENTITY_EVIDENCE_MISSING", {item["ruleCode"] for item in result["diagnostics"]})

    def test_claim_evidence_references_must_resolve(self):
        document = valid_entity_model()
        document["claims"].append({"claimId": "claim-1", "subject": entity_ref("record"),
            "predicate": "attribute.status", "value": "paid", "evidenceIds": ["missing-evidence"],
            "claimStatus": "provisional"})
        result = validate_semantic_entity_model(document)
        self.assertFalse(result["valid"])
        self.assertIn("ENTITY_EVIDENCE_MISSING", {item["ruleCode"] for item in result["diagnostics"]})

    def test_evidence_can_retain_source_path_digest_and_byte_span(self):
        document = valid_entity_model()
        document["evidence"][0].update({"path": "src/order.py", "sha256": "a" * 64,
                                        "startByte": 4, "endByte": 12, "method": "python-ast"})
        result = validate_semantic_entity_model(document)
        self.assertTrue(result["valid"], result["diagnostics"])

    def test_evidence_rejects_inverted_source_byte_span(self):
        document = valid_entity_model()
        document["evidence"][0].update({"path": "src/order.py", "sha256": "a" * 64,
                                        "startByte": 12, "endByte": 4, "method": "python-ast"})
        result = validate_semantic_entity_model(document)
        self.assertFalse(result["valid"])
        self.assertIn("ENTITY_EVIDENCE_RANGE_INVALID",
                      {item["ruleCode"] for item in result["diagnostics"]})

    def test_source_mapping_retains_construct_identity_and_resolves_target(self):
        document = valid_entity_model()
        document["sourceMappings"] = [{"mappingId": "mapping-1", "target": document["entities"][1]["ref"],
            "sourceConstruct": {"constructId": "construct-1", "sourceKey": "source-key-1",
                "language": "python", "syntaxKind": "class_declaration", "name": "Order",
                "path": "src/order.py", "sha256": "a" * 64, "startByte": 0, "endByte": 12,
                "parserId": "python-ast", "parserVersion": "3.12"},
            "role": "represents", "mappingStatus": "mapped", "evidenceIds": ["ev-1"]}]
        result = validate_semantic_entity_model(document)
        self.assertTrue(result["valid"], result["diagnostics"])

    def test_source_mapping_rejects_missing_target(self):
        document = valid_entity_model()
        document["sourceMappings"] = [{"mappingId": "mapping-1",
            "target": entity_ref("missing"), "sourceConstruct": {"constructId": "construct-1",
                "sourceKey": "source-key-1", "language": "python", "syntaxKind": "function_declaration",
                "name": "f", "path": "src/f.py", "sha256": "a" * 64, "startByte": 0,
                "endByte": 1, "parserId": "python-ast", "parserVersion": "3.12"},
            "role": "implements", "mappingStatus": "mapped", "evidenceIds": ["ev-1"]}]
        result = validate_semantic_entity_model(document)
        self.assertIn("ENTITY_MAPPING_TARGET_MISSING",
                      {item["ruleCode"] for item in result["diagnostics"]})

    def test_same_entity_identity_cannot_have_two_kinds(self):
        document = valid_entity_model()
        document["entities"].append({"ref": entity_ref("record", "ComputationEntity"),
            "name": "另一个对象", "aliases": [], "description": "冲突身份", "attributes": [],
            "sourceKeys": [], "observationViews": ["E2"]})
        result = validate_semantic_entity_model(document)
        self.assertFalse(result["valid"])
        self.assertIn("ENTITY_IDENTITY_KIND_CONFLICT", {item["ruleCode"] for item in result["diagnostics"]})

    def test_relation_endpoint_must_resolve_to_registered_entity(self):
        document = valid_entity_model()
        document["relations"][0]["target"] = entity_ref("missing")
        result = validate_semantic_entity_model(document)
        self.assertFalse(result["valid"])
        self.assertIn("ENTITY_RELATION_ENDPOINT_MISSING", {item["ruleCode"] for item in result["diagnostics"]})

    def test_relation_predicate_rejects_disallowed_endpoint_kinds(self):
        document = valid_entity_model()
        document["relations"][0]["subject"] = entity_ref("record")
        document["relations"][0]["target"] = entity_ref("project", "Project")
        result = validate_semantic_entity_model(document)
        self.assertFalse(result["valid"])
        self.assertIn("ENTITY_RELATION_KIND_INVALID", {item["ruleCode"] for item in result["diagnostics"]})

    def test_relation_reference_kind_must_match_registered_entity_kind(self):
        document = valid_entity_model()
        document["relations"][0]["target"] = entity_ref("record", "ComputationEntity")
        result = validate_semantic_entity_model(document)
        self.assertFalse(result["valid"])
        self.assertIn("ENTITY_REF_KIND_MISMATCH", {item["ruleCode"] for item in result["diagnostics"]})

    def test_continuity_candidate_can_remain_unresolved_without_merging_identity(self):
        document = valid_entity_model()
        document["continuityCandidates"].append({"candidateId": "continuity-1",
            "previous": entity_ref("old"), "current": entity_ref("record"),
            "status": "continuity_unresolved", "reason": "源码移动但证据不足"})
        result = validate_semantic_entity_model(document)
        self.assertTrue(result["valid"], result["diagnostics"])
        self.assertNotEqual(document["continuityCandidates"][0]["previous"],
                            document["continuityCandidates"][0]["current"])

    def test_entity_attribute_must_not_claim_unproven_value_domain(self):
        document = valid_entity_model()
        document["entities"][1]["attributes"][0]["valueRange"] = {
            "kind": "finite_set", "values": ["paid", "unpaid"], "evidenceIds": []}
        result = validate_semantic_entity_model(document)
        self.assertFalse(result["valid"])
        self.assertIn("ENTITY_VALUE_RANGE_EVIDENCE_MISSING",
                      {item["ruleCode"] for item in result["diagnostics"]})


if __name__ == "__main__":
    unittest.main()
