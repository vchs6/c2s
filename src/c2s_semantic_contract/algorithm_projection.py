"""现行算法结构的文本投影和来源清单核对；不生成旧事实档案。"""

def project_algorithm(document: dict, algorithm_ref: dict) -> dict:
    """Render one structured algorithm without adding behavior beyond its records."""
    algorithm_id = algorithm_ref.get("algorithm_id") if isinstance(algorithm_ref, dict) else None
    candidates = [item for item in document.get("algorithms", [])
                  if isinstance(item, dict) and item.get("algorithm_id") == algorithm_id]
    if len(candidates) != 1:
        raise ValueError("algorithm_ref must identify exactly one algorithm")
    algorithm = candidates[0]
    from c2s_skill.algorithm import validate_algorithms

    diagnostics = validate_algorithms({"schema_version": document.get("schema_version"),
                                       "algorithms": [algorithm]})
    if diagnostics:
        raise ValueError(f"algorithm contract is invalid: {diagnostics[0]['code']}")
    body = algorithm["body"]
    regions = {item["region_id"]: item for item in body["regions"]}

    def depth(region_id: str | None) -> int:
        result = 0
        visited = set()
        while region_id in regions and regions[region_id].get("parent_region_id") is not None:
            if region_id in visited:
                break
            visited.add(region_id)
            region_id = regions[region_id]["parent_region_id"]
            result += 1
        return result

    lines = [f"Algorithm: {algorithm['problem']}", f"Purpose: {algorithm['purpose']}"]
    mappings = []
    for step in body["steps"]:
        source = step.get("source")
        location = (f"{source['path']}:{source['start_byte']}-{source['end_byte']}"
                    if isinstance(source, dict) else "source unavailable")
        attributes = step.get("attributes", {})
        operation = attributes.get("operation") if isinstance(attributes, dict) else None
        suffix = f" — {operation}" if operation else ""
        if step.get("kind") == "opaque" and step.get("impact"):
            suffix += f" — {step['impact']}"
        line = "  " * depth(step.get("region_id")) + f"- [{step['kind']}] {step['step_id']} ({location}){suffix}"
        if step.get("kind") == "opaque" and step.get("unknowns"):
            line += f" [unknown: {', '.join(step['unknowns'])}]"
        lines.append(line)
        mappings.append({"stepId": step["step_id"], "startLine": len(lines), "endLine": len(lines)})
    for label, edge_kind in (("Control", "control_edges"), ("Data", "data_edges")):
        for edge in body[edge_kind]:
            if edge_kind == "control_edges":
                relation = f"{edge['kind']} / {edge['condition']['kind']}"
            else:
                relation = edge["role"]
            lines.append(f"{label}: {edge['from_step']} -> {edge['to_step']} ({relation})")
    gaps = list(algorithm.get("omissions", []))
    for item in algorithm["contract"]["coverage"]:
        if item["state"] != "complete":
            gaps.append({"category": item["category"], "reason": item.get("reason", item["state"])})
    for item in gaps:
        lines.append(f"Gap: {item.get('reason', item.get('category', 'unspecified'))}")
    return {"text": "\n".join(lines), "stepMappings": mappings, "gaps": gaps}

def check_source_coverage(document: dict, checklist: dict) -> dict:
    """Check a reviewed source checklist against body steps, effects or declared gaps.

    This function does not inspect source files or decide whether the checklist is
    exhaustive; it only validates the submitted human-reviewed mapping.
    """
    algorithm = next((item for item in document.get("algorithms", []) if isinstance(item, dict)), {})
    step_ids = {step.get("step_id") for step in algorithm.get("body", {}).get("steps", [])
                if isinstance(step, dict)}
    effect_count = len(algorithm.get("contract", {}).get("effects", []))
    raw_items = checklist.get("items") if isinstance(checklist, dict) else None
    items = raw_items if isinstance(raw_items, list) else []
    reviewed = isinstance(checklist, dict) and checklist.get("reviewed") is True
    uncovered = []
    declared_gaps = []
    if not items:
        uncovered.append({"itemId": None, "reason": "source checklist must contain at least one reviewed item"})
    if raw_items is not None and not isinstance(raw_items, list):
        uncovered.append({"itemId": None, "reason": "checklist items must be an array"})
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            uncovered.append({"itemId": None, "reason": "checklist item has invalid shape"})
            continue
        item_id = item.get("itemId")
        steps = item.get("stepIds", [])
        effects = item.get("effectIndices", [])
        gap_reason = item.get("gapReason")
        mapped = (isinstance(steps, list) and any(step_id in step_ids for step_id in steps)
                  or isinstance(effects, list) and any(type(index) is int and 0 <= index < effect_count
                                                       for index in effects))
        valid = bool(item_id and isinstance(item.get("description"), str) and
                     ((mapped and all(step_id in step_ids for step_id in steps)
                       and all(type(index) is int and 0 <= index < effect_count for index in effects))
                      or (not mapped and isinstance(gap_reason, str) and bool(gap_reason))))
        if not reviewed or not valid:
            uncovered.append({"itemId": item_id, "reason": "source checklist is unreviewed" if not reviewed
                              else "item has no valid Step/effect mapping or explicit gap"})
        if isinstance(gap_reason, str) and gap_reason:
            declared_gaps.append({"itemId": item_id, "reason": gap_reason})
    return {"reviewed": reviewed, "uncoveredItems": uncovered, "declaredGaps": declared_gaps}
