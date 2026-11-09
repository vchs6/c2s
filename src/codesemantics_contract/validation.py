"""语义事实公开结构契约与引用不变量。"""
from __future__ import annotations
import json
import hashlib
from pathlib import Path
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
_ROOT = Path(__file__).resolve().parents[2]


_SEMANTIC_ENTITY_SCHEMA_PATH = _ROOT / "contracts" / "semantic-model" / "semantic-entity-model-2.schema.json"


_SEMANTIC_ENTITY_TYPES_PATH = _ROOT / "contracts" / "semantic-model" / "semantic-entity-types.json"


_SEMANTIC_ENTITY_PREDICATES_PATH = _ROOT / "contracts" / "semantic-model" / "semantic-entity-predicates.json"


_SEMANTIC_ENTITY_MANIFEST_PATH = _ROOT / "contracts" / "semantic-model" / "semantic-entity-v2-catalog-manifest.json"


_TRUSTED_SEMANTIC_ENTITY_MANIFEST_SHA256 = "a3daabf7b79eed782977286138f67380d7a63827d0522575bfa9110e25dc701c"


def _diagnostic(stage: str, rule_code: str, message: str, *, record_ref: str | None = None,
                field_path: str = "", severity: str = "error", related_refs: list[str] | None = None) -> dict:
    return {"stage": stage, "recordRef": record_ref, "fieldPath": field_path,
            "ruleCode": rule_code, "severity": severity, "relatedRefs": related_refs or [], "message": message}


def _canonical_digest(value: dict) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _core_semantic_entity_model_catalogs() -> dict:
    """Load the pinned entity types, relation predicates, and wire schema."""
    return {"types": json.loads(_SEMANTIC_ENTITY_TYPES_PATH.read_text(encoding="utf-8")),
            "predicates": json.loads(_SEMANTIC_ENTITY_PREDICATES_PATH.read_text(encoding="utf-8")),
            "schema": json.loads(_SEMANTIC_ENTITY_SCHEMA_PATH.read_text(encoding="utf-8"))}


def _validate_semantic_entity_catalogs() -> tuple[dict | None, list[dict]]:
    try:
        catalogs = _core_semantic_entity_model_catalogs()
        manifest = json.loads(_SEMANTIC_ENTITY_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return None, [_diagnostic("catalog", "ENTITY_CATALOG_INVALID",
                                  f"语义实体目录无法读取：{type(error).__name__}。")]
    expected_files = {_SEMANTIC_ENTITY_TYPES_PATH.name: catalogs["types"],
                      _SEMANTIC_ENTITY_PREDICATES_PATH.name: catalogs["predicates"],
                      _SEMANTIC_ENTITY_SCHEMA_PATH.name: catalogs["schema"]}
    expected_digests = {name: _canonical_digest(value) for name, value in expected_files.items()}
    if (_canonical_digest(manifest) != _TRUSTED_SEMANTIC_ENTITY_MANIFEST_SHA256
            or manifest.get("version") != "2.0.0" or manifest.get("profile") != "semantic-entity-model-2"
            or manifest.get("digests") != expected_digests):
        return None, [_diagnostic("catalog", "ENTITY_CATALOG_DIGEST_MISMATCH",
                                  "语义实体目录清单与版本化目录内容不一致。")]
    try:
        Draft202012Validator.check_schema(catalogs["schema"])
    except SchemaError as error:
        return None, [_diagnostic("catalog", "ENTITY_SCHEMA_INVALID",
                                  f"语义实体结构模式无效：{type(error).__name__}。")]
    kinds = [item.get("typeId") for item in catalogs["types"].get("types", [])]
    predicates = [item.get("predicateId") for item in catalogs["predicates"].get("predicates", [])]
    schema_kinds = catalogs["schema"].get("$defs", {}).get("entityRef", {}).get("properties", {}).get("kind", {}).get("enum", [])
    schema_predicates = catalogs["schema"].get("$defs", {}).get("relation", {}).get("properties", {}).get("predicate", {}).get("enum", [])
    if (len(set(kinds)) != len(kinds) or len(set(predicates)) != len(predicates)
            or set(kinds) != set(schema_kinds) or set(predicates) != set(schema_predicates)):
        return None, [_diagnostic("catalog", "ENTITY_CATALOG_SCHEMA_MISMATCH",
                                  "类型或关系目录与结构模式枚举不一致。")]
    kind_set = set(kinds)
    for predicate in catalogs["predicates"]["predicates"]:
        if (not predicate.get("subjectKinds") or not set(predicate["subjectKinds"]) <= kind_set
                or not set(predicate.get("targetKinds", [])) <= kind_set):
            return None, [_diagnostic("catalog", "ENTITY_PREDICATE_KIND_INVALID",
                                      "关系谓词引用了未知实体类型或没有合法主体类型。")]
    return catalogs, []


def _core_validate_semantic_entity_model(document: dict) -> dict:
    """Validate entity-profile structure, identity, evidence and local references."""
    result = {"valid": False, "stages": {"structure": "not_run", "references": "not_run",
                                          "invariants": "not_run"}, "diagnostics": []}
    catalogs, catalog_errors = _validate_semantic_entity_catalogs()
    if catalog_errors:
        result["stages"]["structure"] = "fail"
        result["diagnostics"] = catalog_errors
        return result
    schema = catalogs["schema"]
    errors = sorted(Draft202012Validator(schema).iter_errors(document),
                    key=lambda error: list(error.absolute_path))
    if errors:
        result["stages"]["structure"] = "fail"
        result["diagnostics"] = [_diagnostic("structure", "ENTITY_CONTRACT_INVALID", error.message,
            field_path="/" + "/".join(map(str, error.absolute_path))) for error in errors]
        return result
    result["stages"]["structure"] = "pass"

    def identity(ref: dict) -> tuple[str, str, str]:
        item = ref["identity"]
        return item["authority"], item["domainId"], item["localId"]

    def add_reference_error(code: str, message: str, path: str, record: str | None = None) -> None:
        diagnostics.append(_diagnostic("references", code, message, field_path=path, record_ref=record))

    diagnostics: list[dict] = []
    entities: dict[tuple[str, str, str], tuple[str, str]] = {}
    for index, entity in enumerate(document["entities"]):
        ref = entity["ref"]
        key = identity(ref)
        previous = entities.get(key)
        if key[1] != document["scopeId"]:
            add_reference_error("ENTITY_SCOPE_MISMATCH", "实体身份域必须与档案分析范围一致。",
                                f"/entities/{index}/ref/identity/domainId", f"entity:{index}")
        if previous is not None:
            code = "ENTITY_IDENTITY_KIND_CONFLICT" if previous[0] != ref["kind"] else "ENTITY_IDENTITY_DUPLICATE"
            add_reference_error(code, "同一身份不得重复登记或具有不同实体类型。",
                                f"/entities/{index}/ref", f"entity:{index}")
        else:
            entities[key] = (ref["kind"], f"entity:{index}")

    def check_ref_kind(ref: dict, path: str, record: str) -> None:
        registered = entities.get(identity(ref))
        if registered is not None and registered[0] != ref["kind"]:
            add_reference_error("ENTITY_REF_KIND_MISMATCH", "引用声明的类型与已登记实体类型不一致。",
                                path, record)

    claim_ids: set[str] = set()
    for index, claim in enumerate(document["claims"]):
        claim_id = claim["claimId"]
        if claim_id in claim_ids:
            add_reference_error("ENTITY_CLAIM_ID_DUPLICATE", "主张标识必须唯一。",
                                f"/claims/{index}/claimId", f"claim:{claim_id}")
        claim_ids.add(claim_id)
        if identity(claim["subject"]) not in entities:
            add_reference_error("ENTITY_CLAIM_SUBJECT_MISSING", "主张主体未登记。",
                                f"/claims/{index}/subject", f"claim:{claim_id}")
        check_ref_kind(claim["subject"], f"/claims/{index}/subject", f"claim:{claim_id}")

    evidence_ids = [item["evidenceId"] for item in document["evidence"]]
    evidence_set = set(evidence_ids)
    if len(evidence_set) != len(evidence_ids):
        add_reference_error("ENTITY_EVIDENCE_ID_DUPLICATE", "证据标识必须唯一。", "/evidence")
    for index, evidence in enumerate(document["evidence"]):
        if "startByte" in evidence and evidence["endByte"] < evidence["startByte"]:
            diagnostics.append(_diagnostic("invariants", "ENTITY_EVIDENCE_RANGE_INVALID",
                "证据结束字节位置必须大于或等于起始位置。",
                record_ref=f"evidence:{evidence['evidenceId']}",
                field_path=f"/evidence/{index}/endByte"))

    def check_evidence(ids: list[str], path: str, record: str) -> None:
        for evidence_id in ids:
            if evidence_id not in evidence_set:
                add_reference_error("ENTITY_EVIDENCE_MISSING", "引用的证据未登记。",
                                    path, record)

    for index, claim in enumerate(document["claims"]):
        check_evidence(claim["evidenceIds"], f"/claims/{index}/evidenceIds",
                       f"claim:{claim['claimId']}")

    attribute_ids: set[tuple[tuple[str, str, str], str]] = set()
    for index, entity in enumerate(document["entities"]):
        owner = identity(entity["ref"])
        for attribute_index, attribute in enumerate(entity["attributes"]):
            key = (owner, attribute["attributeId"])
            if key in attribute_ids:
                add_reference_error("ENTITY_ATTRIBUTE_ID_DUPLICATE", "同一实体内属性标识必须唯一。",
                                    f"/entities/{index}/attributes/{attribute_index}/attributeId")
            attribute_ids.add(key)
            value_range = attribute["valueRange"]
            range_evidence = value_range.get("evidenceIds", [])
            check_evidence(attribute["evidenceIds"] + range_evidence,
                           f"/entities/{index}/attributes/{attribute_index}/evidenceIds",
                           f"attribute:{attribute['attributeId']}")
            if value_range["kind"] != "unknown" and not range_evidence:
                add_reference_error("ENTITY_VALUE_RANGE_EVIDENCE_MISSING",
                    "已声明的值域必须关联至少一项证据。",
                    f"/entities/{index}/attributes/{attribute_index}/valueRange/evidenceIds",
                    f"attribute:{attribute['attributeId']}")
            target = value_range.get("target")
            if target is not None and identity(target) not in entities:
                add_reference_error("ENTITY_VALUE_RANGE_TARGET_MISSING", "值域引用目标未登记。",
                    f"/entities/{index}/attributes/{attribute_index}/valueRange/target")
            elif target is not None:
                check_ref_kind(target, f"/entities/{index}/attributes/{attribute_index}/valueRange/target",
                               f"attribute:{attribute['attributeId']}")

    relation_ids: set[str] = set()
    predicates_by_id = {item["predicateId"]: item for item in catalogs["predicates"]["predicates"]}
    for index, relation in enumerate(document["relations"]):
        relation_id = relation["relationId"]
        if relation_id in relation_ids:
            add_reference_error("ENTITY_RELATION_ID_DUPLICATE", "关系标识必须唯一。",
                                f"/relations/{index}/relationId")
        relation_ids.add(relation_id)
        if identity(relation["subject"]) not in entities:
            add_reference_error("ENTITY_RELATION_ENDPOINT_MISSING", "关系主体未登记。",
                                f"/relations/{index}/subject", f"relation:{relation_id}")
        check_ref_kind(relation["subject"], f"/relations/{index}/subject", f"relation:{relation_id}")
        target = relation["target"]
        target_missing = (identity(target) not in entities if "identity" in target
                          else target["claimId"] not in claim_ids)
        if target_missing:
            add_reference_error("ENTITY_RELATION_ENDPOINT_MISSING", "关系目标实体或事实主张未登记。",
                                f"/relations/{index}/target", f"relation:{relation_id}")
        elif "identity" in target:
            check_ref_kind(target, f"/relations/{index}/target", f"relation:{relation_id}")
        predicate = predicates_by_id[relation["predicate"]]
        subject_kind = entities.get(identity(relation["subject"]), (None,))[0]
        target_kind = (entities.get(identity(target), (None,))[0] if "identity" in target
                       else "FactClaim")
        if (subject_kind not in predicate["subjectKinds"]
                or (target_kind != "FactClaim" and target_kind not in predicate.get("targetKinds", []))):
            add_reference_error("ENTITY_RELATION_KIND_INVALID", "关系谓词不允许此主体和目标类型。",
                                f"/relations/{index}", f"relation:{relation_id}")
        check_evidence(relation["evidenceIds"], f"/relations/{index}/evidenceIds", f"relation:{relation_id}")

    mapping_ids: set[str] = set()
    for index, mapping in enumerate(document.get("sourceMappings", [])):
        mapping_id = mapping["mappingId"]
        if mapping_id in mapping_ids:
            add_reference_error("ENTITY_MAPPING_ID_DUPLICATE", "源码映射标识必须唯一。",
                                f"/sourceMappings/{index}/mappingId")
        mapping_ids.add(mapping_id)
        target = mapping.get("target")
        if target is not None:
            if "identity" in target:
                if identity(target) not in entities:
                    add_reference_error("ENTITY_MAPPING_TARGET_MISSING", "源码映射实体目标未登记。",
                                        f"/sourceMappings/{index}/target")
                else:
                    check_ref_kind(target, f"/sourceMappings/{index}/target", f"mapping:{mapping_id}")
            elif target["claimId"] not in claim_ids:
                add_reference_error("ENTITY_MAPPING_TARGET_MISSING", "源码映射主张目标未登记。",
                                    f"/sourceMappings/{index}/target")
        construct = mapping["sourceConstruct"]
        path_parts = Path(construct["path"]).parts
        if Path(construct["path"]).is_absolute() or ".." in path_parts:
            add_reference_error("ENTITY_MAPPING_PATH_INVALID", "源码构造路径必须位于项目分析范围内。",
                                f"/sourceMappings/{index}/sourceConstruct/path")
        if construct["endByte"] < construct["startByte"]:
            add_reference_error("ENTITY_MAPPING_RANGE_INVALID", "源码构造结束位置不能早于起始位置。",
                                f"/sourceMappings/{index}/sourceConstruct/endByte")
        check_evidence(mapping["evidenceIds"], f"/sourceMappings/{index}/evidenceIds", f"mapping:{mapping_id}")

    candidate_ids: set[str] = set()
    for index, candidate in enumerate(document["continuityCandidates"]):
        candidate_id = candidate["candidateId"]
        if candidate_id in candidate_ids:
            add_reference_error("ENTITY_CONTINUITY_ID_DUPLICATE", "连续性候选标识必须唯一。",
                                f"/continuityCandidates/{index}/candidateId")
        candidate_ids.add(candidate_id)
        if identity(candidate["previous"]) == identity(candidate["current"]):
            add_reference_error("ENTITY_CONTINUITY_SELF_LINK", "连续性候选必须区分来源身份。",
                                f"/continuityCandidates/{index}")
        if identity(candidate["current"]) not in entities:
            add_reference_error("ENTITY_CONTINUITY_CURRENT_MISSING", "连续性候选的当前实体未登记。",
                                f"/continuityCandidates/{index}/current")
        else:
            check_ref_kind(candidate["current"], f"/continuityCandidates/{index}/current",
                           f"continuity:{candidate_id}")
        check_evidence(candidate.get("evidenceIds", []),
                       f"/continuityCandidates/{index}/evidenceIds", f"continuity:{candidate_id}")

    coverage_ids: set[str] = set()
    for index, coverage in enumerate(document["coverage"]):
        coverage_id = coverage["coverageId"]
        if coverage_id in coverage_ids:
            add_reference_error("ENTITY_COVERAGE_ID_DUPLICATE", "覆盖标识必须唯一。",
                                f"/coverage/{index}/coverageId")
        coverage_ids.add(coverage_id)
        if identity(coverage["entity"]) not in entities:
            add_reference_error("ENTITY_COVERAGE_ENTITY_MISSING", "覆盖目标实体未登记。",
                                f"/coverage/{index}/entity", f"coverage:{coverage_id}")
        else:
            check_ref_kind(coverage["entity"], f"/coverage/{index}/entity", f"coverage:{coverage_id}")

    result["stages"]["references"] = "fail" if diagnostics else "pass"
    result["stages"]["invariants"] = "fail" if diagnostics else "pass"
    result["diagnostics"] = diagnostics
    result["valid"] = not diagnostics
    return result


def validate_semantic_entity_model_v2(document: object) -> dict:
    """校验v2载荷及跨来源、主张、证据和实体引用，不执行项目工具。"""
    schema_path = Path(__file__).resolve().parents[2] / 'contracts/semantic-model/semantic-entity-model-2.schema.json'
    schema = json.loads(schema_path.read_text(encoding='utf-8'))
    errors = [{'code': 'V2_STRUCTURE', 'path': list(e.path), 'message': e.message}
              for e in Draft202012Validator(schema).iter_errors(document)]
    if errors:
        return {'valid': False, 'diagnostics': errors}
    core_result = _core_validate_semantic_entity_model(document)
    errors.extend(core_result['diagnostics'])
    def fail(code, message):
        errors.append({'code': code, 'message': message})
    def unique(collection, key):
        values = [item[key] for item in document[collection]]
        if len(values) != len(set(values)):
            fail('V2_DUPLICATE_ID', collection)
        return set(values)
    sources = unique('sourceRecords', 'recordId')
    evidence = unique('evidence', 'evidenceId')
    claims = unique('claims', 'claimId')
    artifacts = unique('artifacts', 'artifactId')
    unique('sourceCoverage', 'coverageId')
    unique('acquisitionRuns', 'runId')
    for record in document['sourceRecords']:
        path = record['path'].replace('\\', '/')
        if path.startswith('/') or '..' in path.split('/') or ':' in path:
            fail('V2_SOURCE_PATH', path)
        refs = set(record['parentRecordIds']) | {x['recordId'] for x in record['relatedRecords']}
        if refs - sources or set(record['evidenceIds']) - evidence:
            fail('V2_SOURCE_REFERENCE', record['recordId'])
    algorithm_schema=json.loads((_ROOT/'skill/contracts/semantic-algorithm.schema.json').read_text())
    algorithm_validator=Draft202012Validator(algorithm_schema)
    def check_evidence_refs(value,path):
        if isinstance(value,dict):
            for key,child in value.items():
                child_path=path+'/'+key
                if key in {'evidence_refs','evidenceIds','evidenceRefs'}:
                    if not isinstance(child,list):
                        errors.append({'code':'V2_ALGORITHM_EVIDENCE_REFERENCE','path':child_path,'message':'证据引用必须是数组'})
                        continue
                    for index,eid in enumerate(child):
                        if not isinstance(eid,str) or eid not in evidence:
                            errors.append({'code':'V2_ALGORITHM_EVIDENCE_REFERENCE','path':child_path+'/'+str(index),
                                           'message':'算法或伪代码引用了未登记证据'})
                elif key=='evidenceId' and isinstance(child,str) and child not in evidence:
                    errors.append({'code':'V2_ALGORITHM_EVIDENCE_REFERENCE','path':child_path,'message':'未登记的算法证据'})
                else:check_evidence_refs(child,child_path)
        elif isinstance(value,list):
            for index,child in enumerate(value):check_evidence_refs(child,path+'/'+str(index))
    def check_implementation(value,path):
        if 'algorithm' in value:
            wrapped={'schema_version':'1.0.0','algorithms':[value['algorithm']]}
            for error in algorithm_validator.iter_errors(wrapped):
                errors.append({'code':'V2_ALGORITHM_STRUCTURE','path':path+'/algorithm','message':error.message})
            check_evidence_refs(value['algorithm'],path+'/algorithm')
        if 'pseudocode' in value:check_evidence_refs(value['pseudocode'],path+'/pseudocode')
    for index,record in enumerate(document['sourceRecords']):
        check_implementation(record,'/sourceRecords/'+str(index))
    for index,mapping in enumerate(document.get('sourceMappings',[])):
        if 'implementationView' in mapping:check_implementation(mapping['implementationView'],'/sourceMappings/'+str(index)+'/implementationView')
    for claim in document['claims']:
        if claim['origin'] == 'derived_analysis' and set(claim['premiseIds']) - (sources | evidence | claims):
            fail('V2_PREMISE_REFERENCE', claim['claimId'])
        if claim['origin'] == 'artifact_observation' and claim['artifactId'] not in artifacts:
            fail('MODEL_ARTIFACT_REFERENCE', claim['claimId'])
    for run in document['acquisitionRuns']:
        if set(run['sourceRecordIds']) - sources or set(run['evidenceIds']) - evidence or set(run['artifactIds']) - artifacts:
            fail('V2_RUN_REFERENCE', run['runId'])
    return {'valid': not errors, 'diagnostics': errors}
