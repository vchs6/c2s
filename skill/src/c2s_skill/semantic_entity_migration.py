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


def import_entity_v1(document: dict) -> dict:
    """确定性转换v1实体档案；未知来源分类保留为受限旧载荷。"""
    from copy import deepcopy
    from .source_records import stable_id
    from c2s_semantic_contract.validation import validate_semantic_entity_model, validate_semantic_entity_model_v2
    valid=validate_semantic_entity_model(document)
    if not valid['valid']:raise ValueError('v1实体档案无效，不能升级')
    model=deepcopy(document);model.update(version='2.0.0',profile='semantic-entity-model-2')
    model.setdefault('sourceMappings',[])
    artifact_id='legacy:'+stable_id(document)
    model['artifacts']=[{'artifactId':artifact_id,'kind':'legacy_payload','payload':deepcopy(document)}]
    for claim in model['claims']:
        claim['origin']='unclassified_legacy';claim['legacyPayloadArtifactId']=artifact_id
    fingerprint='legacy:'+stable_id(document);config='legacy:unverified'
    records={}
    for mapping in model['sourceMappings']:
        c=mapping['sourceConstruct'];record_id=stable_id([model['scopeId'],fingerprint,c['path'],c['startByte'],c['endByte'],c['syntaxKind']])
        if record_id not in records:
            records[record_id]={'recordId':record_id,'kind':'source_module' if c['syntaxKind']=='module' else 'declaration',
                'name':c['name'],'path':c['path'],'sourceConstructIds':[c['constructId']],
                'parentRecordIds':[],'relatedRecords':[],'evidenceIds':[],
                'status':'partial','sourceConstruct':deepcopy(c)}
        records[record_id]['evidenceIds']=sorted(set(records[record_id]['evidenceIds'])|set(mapping['evidenceIds']))
    by_construct={x['sourceConstruct']['constructId']:x['recordId'] for x in records.values()}
    for rec in records.values():
        parent=rec['sourceConstruct'].get('parentConstructId')
        if parent in by_construct:rec['parentRecordIds']=[by_construct[parent]]
    model['sourceRecords']=list(records.values())
    model['sourceCoverage']=[{'coverageId':'legacy-coverage:'+stable_id(document),
        'inputFingerprint':fingerprint,'configurationDigest':config,'view':'entity','target':{'kind':'all'},
        'facets':['attributes','relations','implementation','tests'],'conditions':{},'status':'not_acquired',
        'processedPaths':[],'unprocessedPaths':sorted({x['path'] for x in records.values()}),
        'diagnostics':[{'code':'UNCLASSIFIED_LEGACY','artifactId':artifact_id,'retryable':True}]}]
    model['acquisitionRuns']=[{'runId':'legacy-import:'+stable_id(document),'inputFingerprint':fingerprint,
        'configurationDigest':config,'status':'partial','tools':[],
        'sourceRecordIds':list(records),'evidenceIds':[x['evidenceId'] for x in model['evidence']],
        'artifactIds':[artifact_id]}]
    valid=validate_semantic_entity_model_v2(model)
    if not valid['valid']:raise ValueError('转换后的v2档案不合法：'+str(valid['diagnostics']))
    return model


def export_entity_v1(document: dict) -> dict:
    """导出可表达的v1投影并逐项报告信息损失，不删除v2原档案。"""
    from copy import deepcopy
    from c2s_semantic_contract.validation import validate_semantic_entity_model_v2, validate_semantic_entity_model
    if not validate_semantic_entity_model_v2(document)['valid']:raise ValueError('v2实体档案无效')
    old=deepcopy(document);old.update(version='1.0.0',profile='semantic-entity-model-1')
    losses=[]
    for field in ('sourceRecords','sourceCoverage','acquisitionRuns','artifacts'):
        if old[field]:losses.append({'code':'V1_UNREPRESENTABLE_COLLECTION','path':'/'+field,'count':len(old[field])})
        old.pop(field)
    for index,claim in enumerate(old['claims']):
        for field in ('origin','method','premiseIds','legacyPayloadArtifactId'):
            if field in claim:
                losses.append({'code':'V1_UNREPRESENTABLE_FIELD','path':f'/claims/{index}/{field}'})
                claim.pop(field)
    original=next((a['payload'] for a in document['artifacts'] if a['kind']=='legacy_payload'),None)
    if original is not None and 'sourceMappings' not in original and not old.get('sourceMappings'):
        old.pop('sourceMappings',None)
    if not validate_semantic_entity_model(old)['valid']:raise ValueError('v1投影引用或结构无效')
    return {'document':old,'losses':losses}


def backup_entity_archive(store, destination: Path) -> dict:
    """使用SQLite在线备份及逐表回读，不覆盖既有文件。"""
    import os
    from pathlib import Path
    import sqlite3
    import hashlib
    destination=Path(destination).resolve()
    if destination==store.path or destination.exists():raise ValueError('备份路径必须尚不存在且不同于原档案')
    destination.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(destination,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    try:
        with store._connect() as source, sqlite3.connect(destination) as target:
            source.execute('BEGIN')
            source.backup(target)
            if target.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('备份完整性检查失败')
            tables=[row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            for table in tables:
                name='"'+table.replace('"','""')+'"'
                left=source.execute('SELECT * FROM '+name).fetchall()
                right=target.execute('SELECT * FROM '+name).fetchall()
                if sorted(left,key=repr)!=sorted(right,key=repr):raise ValueError('备份逐表回读不一致')
        return {'status':'verified','path':str(destination),'tables':len(tables),
                'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()}
    except BaseException:
        destination.unlink(missing_ok=True)
        raise


def prepare_v2_backup(store) -> dict | None:
    """首次写入v2且存在v1实体档案时，先生成独立、验证过的备份。"""
    import sqlite3
    from uuid import uuid4
    if not store.path.is_file():return None
    with sqlite3.connect(store.path.as_uri()+'?mode=ro',uri=True) as connection:
        tables={r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'semantic_entity_archives' not in tables:return None
        if not connection.execute('SELECT 1 FROM semantic_entity_archives LIMIT 1').fetchone():return None
        if ('semantic_entity_v2_archives' in tables and
                connection.execute('SELECT 1 FROM semantic_entity_v2_archives LIMIT 1').fetchone()):return None
    destination=store.path.with_name(store.path.name+'.pre-v2-'+uuid4().hex+'.sqlite')
    return backup_entity_archive(store,destination)
