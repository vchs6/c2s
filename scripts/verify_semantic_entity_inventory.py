#!/usr/bin/env python3
"""遍历真实项目的全部已识别语义实体并核验SQLite往返/查询闭合。"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "skill" / "src"))

from c2s_skill.entity_construction import construct_and_query_semantic_entities
from c2s_skill.semantic_entity_query import prepare_semantic_entity_query, query_semantic_entities
from c2s_skill.semantic_store import SemanticEntityStore
from c2s_semantic_contract.validation import validate_semantic_entity_model


def verify(project: Path, database: Path, output: Path) -> dict:
    project = project.resolve(strict=True)
    database = database.resolve()
    store = SemanticEntityStore(database)
    initial = construct_and_query_semantic_entities(project, store, "project")
    scope_id = initial["entity"]["ref"]["identity"]["domainId"]
    archived = store.read(scope_id)
    validation = validate_semantic_entity_model(archived)
    if not validation["valid"]:
        raise RuntimeError(f"SQLite回读档案未通过契约验证：{validation['diagnostics']}")

    traversed = []
    failures = []
    query_index = prepare_semantic_entity_query(archived)
    attribute_count = relation_count = referenced_evidence_count = 0
    for entity in archived["entities"]:
        local_id = entity["ref"]["identity"]["localId"]
        result = query_semantic_entities(archived, f"entity:{local_id}", index=query_index)
        if result["status"] != "obtained":
            failures.append({"entity": entity["ref"], "status": result["status"], "gaps": result["gaps"]})
            continue
        returned = result["entity"]
        expected_claims = sorted((item for item in archived["claims"] if item["subject"] == entity["ref"]),
                                 key=lambda item: item["claimId"])
        expected_relations = sorted((item for item in archived["relations"]
            if item["subject"] == entity["ref"] or item["target"] == entity["ref"]),
            key=lambda item: item["relationId"])
        expected_coverage = sorted((item for item in archived["coverage"] if item["entity"] == entity["ref"]),
                                   key=lambda item: item["coverageId"])
        expected_mappings = sorted((item for item in archived.get("sourceMappings", [])
            if item.get("target") == entity["ref"]), key=lambda item: item["mappingId"])
        expected_evidence_ids = {evidence_id for record in expected_claims + expected_relations + expected_coverage
                                 for evidence_id in record.get("evidenceIds", [])}
        expected_evidence_ids.update(evidence_id for attribute in entity["attributes"]
                                     for evidence_id in attribute["evidenceIds"])
        expected_evidence_ids.update(evidence_id for mapping in expected_mappings
                                     for evidence_id in mapping["evidenceIds"])
        returned_evidence_ids = {item["evidenceId"] for item in returned["evidence"]}
        if (returned["ref"] != entity["ref"] or returned["attributes"] != entity["attributes"]
                or returned["claims"] != expected_claims or returned["relations"] != expected_relations
                or returned["coverage"] != expected_coverage or returned["sourceKeys"] != entity["sourceKeys"]
                or returned["sourceMappings"] != expected_mappings
                or returned_evidence_ids != expected_evidence_ids):
            failures.append({"entity": entity["ref"], "code": "ROUND_TRIP_QUERY_MISMATCH",
                             "missingEvidence": sorted(expected_evidence_ids - returned_evidence_ids),
                             "extraEvidence": sorted(returned_evidence_ids - expected_evidence_ids)})
            continue
        attribute_count += len(returned["attributes"])
        relation_count += len(returned["relations"])
        referenced_evidence_count += len(returned["evidence"])
        traversed.append({"ref": returned["ref"], "name": returned["name"],
            "description": returned["description"], "attributes": returned["attributes"],
            "claimIds": [item["claimId"] for item in returned["claims"]],
            "relationIds": [item["relationId"] for item in returned["relations"]],
            "sourceMappingIds": [item["mappingId"] for item in returned["sourceMappings"]],
            "evidenceIds": sorted({evidence_id for item in returned["evidence"]
                                    for evidence_id in [item["evidenceId"]]}),
            "coverage": returned["coverage"],
            "sourceKeys": returned["sourceKeys"]})

    mapped_ids = {item for entity in traversed for item in entity["sourceMappingIds"]}
    unresolved_mappings = [item for item in archived.get("sourceMappings", []) if item.get("target") is None]
    accounted_mappings = mapped_ids | {item["mappingId"] for item in unresolved_mappings}
    if (len(traversed) != len(archived["entities"]) or failures
            or len(accounted_mappings) != len(archived.get("sourceMappings", []))):
        raise RuntimeError(f"实体遍历不完整：{len(traversed)}/{len(archived['entities'])}，缺口 {failures[:5]}")
    coverage_fingerprints = sorted({item["inputFingerprint"] for item in archived["coverage"]})
    revision = subprocess.run(["git", "-C", str(project), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False).stdout.strip() or None
    source_mappings = deepcopy(archived.get("sourceMappings", []))
    for mapping in source_mappings:
        mapping["sourceConstruct"].pop("text", None)
    constructs_by_version = {(item["sourceConstruct"]["constructId"],
                              item["sourceConstruct"]["sha256"]): item["sourceConstruct"]
                             for item in source_mappings}
    construct_kinds = Counter(item["syntaxKind"] for item in constructs_by_version.values())
    entity_kinds = Counter(item["ref"]["kind"] for item in archived["entities"])
    workspace = None
    cargo_manifest = project / "Cargo.toml"
    if cargo_manifest.is_file() and not cargo_manifest.is_symlink():
        cargo_doc = tomllib.loads(cargo_manifest.read_text(encoding="utf-8"))
        member_paths = cargo_doc.get("workspace", {}).get("members", [])
        package_names = []
        for member_path in member_paths:
            member_manifest = project / member_path / "Cargo.toml"
            if member_manifest.is_file() and not member_manifest.is_symlink():
                package_names.append(tomllib.loads(member_manifest.read_text(encoding="utf-8"))
                                     .get("package", {}).get("name", member_path))
        cargo = shutil.which("cargo")
        if cargo:
            version = subprocess.run([cargo, "--version"], capture_output=True, text=True, timeout=5)
            cargo_status = "available" if version.returncode == 0 else "unavailable:" + (
                version.stderr.strip().splitlines()[0] if version.stderr.strip() else "version-command-failed")
        else:
            cargo_status = "unavailable:not-on-path"
        workspace = {"rootPackage": cargo_doc.get("package", {}).get("name"),
            "declaredMembers": member_paths, "memberPackageNames": sorted(package_names),
            "packageCountFromManifest": len(package_names) + int(bool(cargo_doc.get("package", {}).get("name"))),
            "cargoToolStatus": cargo_status,
            "semanticModuleEntityCount": entity_kinds.get("Module", 0),
            "sourceModuleConstructCount": construct_kinds.get("module_declaration", 0)}
    report = {"version": "1.0.0", "profile": "semantic-entity-inventory-1",
        "projectName": project.name, "sourceRevision": revision,
        "inputFingerprints": coverage_fingerprints,
        "constructionStatus": initial["constructionStatus"], "traversalComplete": True,
        "entityCount": len(traversed), "attributeCount": attribute_count,
        "relationCount": len(archived["relations"]), "evidenceCount": len(archived["evidence"]),
        "referencedEvidenceCount": referenced_evidence_count,
        "sourceMappingCount": len(archived.get("sourceMappings", [])),
        "unresolvedSourceMappingCount": len(unresolved_mappings),
        "unresolvedSourceMappingIds": sorted(item["mappingId"] for item in unresolved_mappings),
        "sourceTextIncluded": False,
        "continuityCandidateCount": len(archived["continuityCandidates"]),
        "entityKindCounts": dict(sorted(entity_kinds.items())),
        "sourceConstructKindCounts": dict(sorted(construct_kinds.items())),
        "workspaceStructure": workspace,
        "constructionDiagnostics": initial["constructionDiagnostics"],
        "claims": archived["claims"], "relations": archived["relations"],
        "sourceMappings": source_mappings, "evidence": archived["evidence"],
        "entities": sorted(traversed, key=lambda item: (
            item["ref"]["kind"], item["name"].casefold(), item["ref"]["identity"]["localId"])),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("database", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = verify(args.project, args.database, args.output)
    print(json.dumps({key: report[key] for key in (
        "projectName", "constructionStatus", "traversalComplete", "entityCount",
        "attributeCount", "relationCount", "evidenceCount", "sourceMappingCount",
        "unresolvedSourceMappingCount", "continuityCandidateCount")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
