"""按语义实体直接成员边界查询实体档案。"""

from __future__ import annotations

from collections import defaultdict
import json
import re


_CHILD_PREDICATES = {"defines", "groups", "contains"}


def prepare_semantic_entity_query(model: dict) -> dict:
    by_identity = {_key(item["ref"]): item for item in model.get("entities", [])}
    by_local_id: dict[str, list[dict]] = defaultdict(list)
    children: dict[tuple[str, str, str], dict[tuple[str, str, str], dict]] = defaultdict(dict)
    claims: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    relations: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    coverage: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    mappings: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    evidence: dict[str, dict] = {item["evidenceId"]: item for item in model.get("evidence", [])}
    for entity in model.get("entities", []):
        by_local_id[entity["ref"]["identity"]["localId"]].append(entity)
    for relation in model.get("relations", []):
        subject_key = _key(relation["subject"])
        relations[subject_key].append(relation)
        target = relation.get("target")
        if isinstance(target, dict) and "identity" in target:
            target_key = _key(target)
            relations[target_key].append(relation)
            if relation["predicate"] in _CHILD_PREDICATES:
                children[subject_key][target_key] = target
            elif relation["predicate"] == "belongs_to":
                children[target_key][subject_key] = relation["subject"]
    for claim in model.get("claims", []):
        claims[_key(claim["subject"])].append(claim)
    for item in model.get("coverage", []):
        if isinstance(item.get("entity"), dict):
            coverage[_key(item["entity"])].append(item)
    for item in model.get("sourceMappings", []):
        target = item.get("target")
        if isinstance(target, dict) and "identity" in target:
            mappings[_key(target)].append(item)
    return {"byIdentity": by_identity, "byLocalId": by_local_id, "children": children,
        "claims": claims, "relations": relations, "coverage": coverage,
        "mappings": mappings, "evidence": evidence}


def query_semantic_entities(model: dict, selector: str, *, max_depth: int = 8,
                            index: dict | None = None) -> dict:
    if model.get("profile") != "semantic-entity-model-1" or not isinstance(selector, str) or not selector:
        raise ValueError("需要有效的 semantic-entity-model-1 档案和非空选择器")
    if not 0 <= max_depth <= 32:
        raise ValueError("递归展开深度必须在0到32之间")
    entities = model.get("entities", [])
    selector = _normalize_selector(selector)
    index = index or prepare_semantic_entity_query(model)
    by_identity = index["byIdentity"]
    by_local_id = index["byLocalId"]
    def members(parent: dict) -> list[dict]:
        parent_key = _key(parent["ref"])
        found: dict[str, dict] = {}
        for child_key in index["children"].get(parent_key, {}):
            child = by_identity.get(child_key)
            if child:
                found[child_key] = child
        return sorted(found.values(), key=lambda item: (item["name"].casefold(), _key(item["ref"])))

    def ref_summary(entity: dict) -> dict:
        return {"ref": entity["ref"], "name": entity["name"], "kind": entity["ref"]["kind"],
                "description": entity["description"]}

    def details(entity: dict) -> dict:
        ref_key = _key(entity["ref"])
        claims = index["claims"].get(ref_key, [])
        relations_for_entity = index["relations"].get(ref_key, [])
        coverage = index["coverage"].get(ref_key, [])
        mappings = index["mappings"].get(ref_key, [])
        evidence_ids = {evidence_id for item in claims + relations_for_entity + coverage
                        for evidence_id in item.get("evidenceIds", [])}
        evidence_ids.update(evidence_id for item in entity["attributes"]
                            for evidence_id in item.get("evidenceIds", []))
        evidence_ids.update(evidence_id for item in mappings for evidence_id in item.get("evidenceIds", []))
        evidence = [index["evidence"][evidence_id] for evidence_id in evidence_ids
                    if evidence_id in index["evidence"]]
        return {**entity, "claims": sorted(claims, key=lambda item: item["claimId"]),
                "relations": sorted(relations_for_entity, key=lambda item: item["relationId"]),
                "sourceMappings": sorted(mappings, key=lambda item: item["mappingId"]),
                "coverage": sorted(coverage, key=lambda item: item["coverageId"]),
                "evidence": sorted(evidence, key=lambda item: item["evidenceId"])}

    if selector in {"entities", "project"}:
        projects = [item for item in entities if item["ref"]["kind"] == "Project"]
        if selector == "project" and len(projects) != 1:
            return {"status": "not_found" if not projects else "ambiguous", "selector": selector,
                    "gaps": [{"code": "PROJECT_ENTITY_UNRESOLVED"}]}
        selected = projects if selector == "project" else entities
        if selector == "project":
            selected = members(projects[0])
        result = {"status": "obtained", "selector": selector, "scopeId": model["scopeId"],
                  "members": [ref_summary(item) for item in selected], "gaps": []}
        if selector == "project":
            result["entity"] = details(projects[0])
        return result

    expand = selector.startswith("expand:")
    target = selector.removeprefix("expand:").removeprefix("entity:")
    candidates = by_local_id.get(target, [])
    if not candidates:
        candidates = [item for item in entities if item["name"] == target or target in item.get("aliases", [])]
    if not candidates:
        return {"status": "not_found", "selector": selector, "gaps": [{"code": "ENTITY_TARGET_NOT_FOUND"}]}
    if len(candidates) > 1:
        return {"status": "ambiguous", "selector": selector,
                "candidates": [ref_summary(item) for item in sorted(candidates, key=lambda value: _key(value["ref"]))],
                "gaps": [{"code": "ENTITY_TARGET_AMBIGUOUS"}]}
    entity = candidates[0]
    direct_members = members(entity)
    result = {"status": "obtained", "selector": selector, "entity": details(entity),
              "members": [ref_summary(item) for item in direct_members], "gaps": []}
    if expand:
        expanded = []
        visited = {_key(entity["ref"])}
        def visit(parent: dict, depth: int) -> None:
            if depth >= max_depth:
                if members(parent):
                    result["gaps"].append({"code": "EXPANSION_DEPTH_LIMIT", "entityRef": parent["ref"]})
                return
            for child in members(parent):
                child_key = _key(child["ref"])
                if child_key in visited:
                    result["gaps"].append({"code": "ENTITY_RELATION_CYCLE", "entityRef": child["ref"]})
                    continue
                expanded.append({"depth": depth + 1, "entity": details(child)})
                visited.add(child_key)
                visit(child, depth + 1)
        visit(entity, 0)
        result["expandedMembers"] = expanded
    return result


def _key(ref: dict) -> tuple[str, str, str]:
    identity = ref["identity"]
    return identity["authority"], identity["domainId"], identity["localId"]


def _normalize_selector(selector: str) -> str:
    text = selector.strip()
    if text in {"项目", "项目实体", "项目实体清单"} or (
            "项目" in text and any(word in text for word in ("哪些", "清单", "成员", "实体"))):
        return "project"
    if text.startswith(("entity:", "expand:", "entities")):
        return text
    match = re.search(r"(?:实体|语义实体)(?:详情|属性|成员)?[：:\s]+(.+?)\s*(?:的?(?:属性|成员|详情|完整描述))?$", text)
    if match:
        return "entity:" + match.group(1).strip(" 的：:")
    match = re.search(r"(?:查询|查看|获取|显示)\s*(.+?)\s*(?:实体)?\s*(?:的)?(?:属性|成员|详情|完整描述)?$", text)
    if match and match.group(1).strip():
        return "entity:" + match.group(1).strip(" 的：:")
    return text


def query_entity_store(store, request: dict) -> dict:
    """Apply a structured request to the isolated entity archive store."""
    from jsonschema import Draft202012Validator
    from pathlib import Path
    schema_path = Path(__file__).resolve().parents[2] / "contracts" / "semantic-entity-query.schema.json"
    import json
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(request))
    if errors:
        raise ValueError("无效实体查询请求：" + "; ".join(error.message for error in errors))
    model = store.read(request["scopeId"])
    if model is None:
        return {"status": "not_found", "selector": request["selector"],
                "gaps": [{"code": "ENTITY_ARCHIVE_NOT_FOUND"}]}
    if request.get("expandChildren", False) and not request["selector"].startswith("expand:"):
        selector = "expand:" + request["selector"].removeprefix("entity:")
    else:
        selector = request["selector"]
    result = query_semantic_entities(model, selector, max_depth=request.get("maxDepth", 8))
    expected_fingerprint = request.get("inputFingerprint")
    expected_analyzer = request.get("analyzerVersion")
    stale_records = []
    def assess_freshness(container: dict) -> None:
        for coverage in container.get("coverage", []):
            reasons = []
            if expected_fingerprint is not None and coverage["inputFingerprint"] != expected_fingerprint:
                reasons.append("INPUT_FINGERPRINT_CHANGED")
            if expected_analyzer is not None and coverage["analyzerVersion"] != expected_analyzer:
                reasons.append("ANALYZER_VERSION_CHANGED")
            if reasons:
                coverage["freshness"] = "review_required"
                stale_records.append({"coverageId": coverage["coverageId"], "reasons": reasons})
    if result.get("entity"):
        assess_freshness(result["entity"])
    for item in result.get("expandedMembers", []):
        assess_freshness(item["entity"])
    for stale in stale_records:
        result["gaps"].append({"code": "COVERAGE_REVIEW_REQUIRED", **stale})
    return result


def render_entity_query(result: dict, output_format: str = "json") -> str:
    """Render one query result as deterministic JSON or a complete Markdown view."""
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2)
    if output_format != "markdown":
        raise ValueError("output_format must be 'json' or 'markdown'")
    lines = [f"状态：{result['status']}", f"选择器：{result.get('selector', '')}"]
    if result.get("entity"):
        entity = result["entity"]
        lines.extend(["", f"# {entity['name']}（{entity['ref']['kind']}）", entity.get("description", ""),
            f"实体身份：{json.dumps(entity['ref']['identity'], ensure_ascii=False, sort_keys=True)}",
            f"源码映射键：{json.dumps(entity['sourceKeys'], ensure_ascii=False)}"])
        for attribute in entity.get("attributes", []):
            value_range = attribute["valueRange"]
            lines.extend(["", f"## 属性：{attribute['name']}", f"属性标识：{attribute['attributeId']}",
                f"语义类型：{attribute['semanticType']}",
                f"实现类型：{attribute.get('implementationType', '未提供')}",
                f"值域：{json.dumps(value_range, ensure_ascii=False, sort_keys=True)}",
                f"基数：{attribute['cardinality']}",
                f"约束：{json.dumps(attribute['constraints'], ensure_ascii=False)}",
                f"证据：{json.dumps(attribute['evidenceIds'], ensure_ascii=False)}",
                f"主张状态：{attribute.get('claimStatus', '未声明')}"])
        for claim in entity.get("claims", []):
            lines.extend(["", f"## 主张：{claim['predicate']}",
                f"值：{json.dumps(claim['value'], ensure_ascii=False, sort_keys=True)}",
                f"状态：{claim['claimStatus']}",
                f"证据：{json.dumps(claim['evidenceIds'], ensure_ascii=False)}"])
        for coverage in entity.get("coverage", []):
            lines.extend(["", f"## 覆盖：{coverage['selector']}", f"状态：{coverage['status']}",
                f"呈现：{coverage.get('presentationStatus', '未声明')}",
                f"新鲜度：{coverage.get('freshness', '未声明')}",
                f"输入指纹：{coverage['inputFingerprint']}",
                f"分析器版本：{coverage['analyzerVersion']}"])
        for relation in entity.get("relations", []):
            lines.extend(["", f"## 关系：{relation['predicate']}", f"关系标识：{relation['relationId']}",
                f"主体：{json.dumps(relation['subject'], ensure_ascii=False, sort_keys=True)}",
                f"目标：{json.dumps(relation['target'], ensure_ascii=False, sort_keys=True)}",
                f"证据：{json.dumps(relation['evidenceIds'], ensure_ascii=False)}"])
        for mapping in entity.get("sourceMappings", []):
            source = mapping["sourceConstruct"]
            lines.extend(["", f"## 源码映射：{mapping['mappingId']}",
                f"构造：{source['syntaxKind']} {source['name']}", f"角色：{mapping['role']}",
                f"映射状态：{mapping['mappingStatus']}",
                f"定位：{source['path']}:{source['startByte']}-{source['endByte']}",
                f"证据：{json.dumps(mapping['evidenceIds'], ensure_ascii=False)}"])
        for evidence in entity.get("evidence", []):
            lines.extend(["", f"## 证据：{evidence['evidenceId']}",
                json.dumps(evidence, ensure_ascii=False, sort_keys=True)])
    if result.get("members"):
        lines.extend(["", "## 直接子实体"])
        lines.extend(f"- {item['name']}（{item['kind']}）：{item.get('description', '')}；引用 {item['ref']['identity']['localId']}"
                     for item in result["members"])
    if result.get("expandedMembers"):
        lines.extend(["", "## 已展开子实体"])
        lines.extend(f"- 深度 {item['depth']}：{item['entity']['name']}（{item['entity']['ref']['kind']}），"
                     f"属性 {len(item['entity'].get('attributes', []))} 项"
                     for item in result["expandedMembers"])
    if result.get("candidates"):
        lines.extend(["", "## 候选目标"])
        lines.extend(f"- {item['name']}（{item['kind']}）" for item in result["candidates"])
    if result.get("gaps"):
        lines.extend(["", "## 缺口"])
        lines.extend(f"- {item['code']}" for item in result["gaps"])
    return "\n".join(lines)
