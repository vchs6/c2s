"""受限的旧档案迁移；只有显式身份映射才创建语义实体。"""

from __future__ import annotations

import json
from copy import deepcopy

from c2s_semantic_contract.validation import validate_semantic_entity_model
from .semantic_store import SemanticEntityStore, _identity_key


def import_legacy_bundle(bundle: dict, scope_id: str, known_entities: list[dict]) -> dict:
    """Map only explicitly identified legacy subjects and report every unsupported loss."""
    if bundle.get("version") != "1.0.0" or bundle.get("profile") not in {
            "semantic-fact-model-1", "m1-project-discovery-1"}:
        raise ValueError("不支持的旧模型档案")
    entities_by_identity = {_identity_key(item["ref"]): item for item in deepcopy(known_entities)}
    model = {"version": "1.0.0", "profile": "semantic-entity-model-1", "scopeId": scope_id,
             "entities": list(known_entities), "claims": [], "relations": [],
             "continuityCandidates": [], "evidence": [], "coverage": []}
    losses = []
    evidence_by_id = {}
    for evidence in bundle.get("evidence", []):
        record = {key: evidence[key] for key in ("evidenceId", "source", "description", "path", "sha256",
            "startByte", "endByte", "method", "toolName", "toolVersion") if key in evidence}
        evidence_by_id[record["evidenceId"]] = record
    model["evidence"] = sorted(evidence_by_id.values(), key=lambda item: item["evidenceId"])
    for registration in bundle.get("registrations", []):
        entity = entities_by_identity.get(_identity_key(registration.get("ref", {"identity": {}})))
        if entity is None:
            losses.append({"code": "LEGACY_REGISTRATION_UNMAPPED", "recordId": registration.get("sourceKey", ""),
                           "reason": "旧源码注册没有显式语义实体身份映射，不会自动升级为实体。"})
            continue
        entity["sourceKeys"] = sorted(set(entity["sourceKeys"]) | {registration["sourceKey"]})
    for fact in bundle.get("facts", []):
        entity = entities_by_identity.get(_identity_key(fact.get("subject", {"identity": {}})))
        if entity is None:
            losses.append({"code": "LEGACY_SUBJECT_UNMAPPED", "recordId": fact.get("factId"),
                           "reason": "孤立源码声明或事实没有显式语义实体身份映射。"})
            continue
        evidence_ids = [item for item in fact.get("evidenceIds", []) if item in evidence_by_id]
        model["claims"].append({"claimId": f"legacy-{fact['factId']}", "subject": entity["ref"],
            "predicate": fact["predicate"], "value": fact.get("value"), "evidenceIds": evidence_ids,
            "claimStatus": "provisional"})
        if fact.get("claimMode") not in {None, "analysis"} or fact.get("condition", {"kind": "true"}) != {"kind": "true"}:
            losses.append({"code": "LEGACY_FACT_CONTEXT_LOSS", "recordId": fact["factId"],
                           "reason": "旧事实的主张模式或条件在实体主张中没有等价字段。"})
    handled = {"facts", "evidence", "registrations"}
    for collection, records in bundle.items():
        if collection not in handled and isinstance(records, list) and records:
            losses.append({"code": "LEGACY_COLLECTION_UNMAPPED", "recordId": collection,
                           "reason": f"旧集合 {collection} 尚无无损实体档案映射。"})
    validation = validate_semantic_entity_model(model)
    if not validation["valid"]:
        raise ValueError(f"迁移产物违反实体模型契约：{validation['diagnostics']}")
    return {"model": model, "losses": sorted(losses, key=lambda item: (item["code"], item["recordId"])),
            "valid": True}


def import_into_store(store: SemanticEntityStore, bundle: dict, scope_id: str,
                      known_entities: list[dict]) -> dict:
    migrated = import_legacy_bundle(bundle, scope_id, known_entities)
    written = store.write(migrated["model"])
    return {**migrated, "generation": written["generation"]}


def export_legacy_bundle(model: dict) -> dict:
    """Deterministically project supported claims and enumerate every unrepresentable collection."""
    validation = validate_semantic_entity_model(model)
    if not validation["valid"]:
        raise ValueError(f"实体档案无效，不能导出：{validation['diagnostics']}")
    registrations = []
    evidence_by_entity: dict[str, set[str]] = {}
    for claim in model["claims"]:
        evidence_by_entity.setdefault(_identity_key(claim["subject"]), set()).update(claim["evidenceIds"])
    for entity in model["entities"]:
        evidence_ids = sorted(evidence_by_entity.get(_identity_key(entity["ref"]), set()))
        if evidence_ids:
            registrations.append({"ref": entity["ref"], "sourceKey": "entity:" + entity["ref"]["identity"]["localId"],
                                  "evidenceIds": evidence_ids})
    facts = [{"factId": "export-" + claim["claimId"], "predicate": claim["predicate"],
        "subject": claim["subject"], "value": claim["value"], "claimMode": "analysis",
        "condition": {"kind": "true"}, "evidenceIds": claim["evidenceIds"]} for claim in model["claims"]]
    bundle = {"version": "1.0.0", "profile": "semantic-fact-model-1",
        "registrations": sorted(registrations, key=lambda item: item["sourceKey"]), "assessments": [],
        "facts": sorted(facts, key=lambda item: item["factId"]),
        "evidence": sorted(model["evidence"], key=lambda item: item["evidenceId"]), "coverage": [],
        "dependencies": [], "dependencyResolutions": [], "semanticStates": [], "diagnostics": [],
        "contextDomains": [], "contexts": []}
    mapped_entities = {_identity_key(claim["subject"]) for claim in model["claims"]}
    losses = []
    for collection in ("relations", "continuityCandidates", "sourceMappings", "coverage"):
        if model.get(collection, []):
            losses.append({"code": "ENTITY_COLLECTION_UNMAPPED", "recordId": collection,
                           "reason": f"实体集合 {collection} 没有旧档案的无损映射。"})
    for entity in model["entities"]:
        if _identity_key(entity["ref"]) not in mapped_entities:
            losses.append({"code": "ENTITY_WITHOUT_CLAIMS", "recordId": entity["ref"]["identity"]["localId"],
                           "reason": "该语义实体在旧模型中没有可表达的主张记录。"})
        if entity["attributes"]:
            losses.append({"code": "ENTITY_ATTRIBUTES_UNMAPPED", "recordId": entity["ref"]["identity"]["localId"],
                           "reason": "实体属性和值域不能投影到旧事实而不丢失类型信息。"})
    return {"bundle": bundle, "losses": sorted(losses, key=lambda item: (item["code"], item["recordId"]))}
