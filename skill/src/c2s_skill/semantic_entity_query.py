"""按语义实体直接成员边界查询实体档案。"""

from __future__ import annotations

from collections import defaultdict
import re


_CHILD_PREDICATES = {"defines", "groups", "contains"}


def query_semantic_entities(model: dict, selector: str, *, max_depth: int = 8) -> dict:
    if model.get("profile") != "semantic-entity-model-1" or not isinstance(selector, str) or not selector:
        raise ValueError("需要有效的 semantic-entity-model-1 档案和非空选择器")
    if not 0 <= max_depth <= 32:
        raise ValueError("递归展开深度必须在0到32之间")
    entities = model.get("entities", [])
    selector = _normalize_selector(selector)
    by_identity = {_key(item["ref"]): item for item in entities}
    by_local_id: dict[str, list[dict]] = defaultdict(list)
    for entity in entities:
        by_local_id[entity["ref"]["identity"]["localId"]].append(entity)
    relations = model.get("relations", [])

    def members(parent: dict) -> list[dict]:
        parent_key = _key(parent["ref"])
        found: dict[str, dict] = {}
        for relation in relations:
            subject = relation["subject"]
            target = relation["target"]
            if not isinstance(target, dict) or "identity" not in target:
                continue
            if relation["predicate"] in _CHILD_PREDICATES and _key(subject) == parent_key:
                child = by_identity.get(_key(target))
                if child:
                    found[_key(child["ref"])] = child
            elif relation["predicate"] == "belongs_to" and _key(target) == parent_key:
                child = by_identity.get(_key(subject))
                if child:
                    found[_key(child["ref"])] = child
        return sorted(found.values(), key=lambda item: (item["name"].casefold(), _key(item["ref"])))

    def ref_summary(entity: dict) -> dict:
        return {"ref": entity["ref"], "name": entity["name"], "kind": entity["ref"]["kind"],
                "description": entity["description"]}

    def details(entity: dict) -> dict:
        ref_key = _key(entity["ref"])
        claims = [item for item in model.get("claims", []) if _key(item["subject"]) == ref_key]
        coverage = [item for item in model.get("coverage", [])
                    if isinstance(item.get("entity"), dict) and _key(item["entity"]) == ref_key]
        return {**entity, "claims": sorted(claims, key=lambda item: item["claimId"]),
                "coverage": sorted(coverage, key=lambda item: item["coverageId"])}

    if selector in {"entities", "project"}:
        projects = [item for item in entities if item["ref"]["kind"] == "Project"]
        if selector == "project" and len(projects) != 1:
            return {"status": "not_found" if not projects else "ambiguous", "selector": selector,
                    "gaps": [{"code": "PROJECT_ENTITY_UNRESOLVED"}]}
        selected = projects if selector == "project" else entities
        if selector == "project":
            selected = members(projects[0])
        return {"status": "obtained", "selector": selector, "scopeId": model["scopeId"],
                "members": [ref_summary(item) for item in selected], "gaps": []}

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
    return query_semantic_entities(model, selector, max_depth=request.get("maxDepth", 8))
