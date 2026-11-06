"""Structural validation for language-neutral algorithm descriptions.

Validation checks the public shape and references; it does not prove that a
description is true of its source or that a pseudocode projection is equivalent.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator


_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "contracts" / "semantic-algorithm.schema.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
Draft202012Validator.check_schema(_SCHEMA)


def _diagnostic(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _algorithm_diagnostics(algorithm: dict, index: int) -> list[dict[str, str]]:
    diagnostics: list[dict[str, str]] = []
    base = f"algorithms[{index}]"
    body = algorithm.get("body")
    if not isinstance(body, dict):
        return diagnostics
    regions = body.get("regions", [])
    steps = body.get("steps", [])
    if not isinstance(regions, list) or not isinstance(steps, list):
        return diagnostics

    contract = algorithm.get("contract")
    if isinstance(contract, dict):
        categories = {"inputs", "outputs", "preconditions", "outcomes", "effects", "ordering"}
        coverage = contract.get("coverage", [])
        seen_categories: set[str] = set()
        if isinstance(coverage, list):
            for coverage_index, item in enumerate(coverage):
                if not isinstance(item, dict) or not isinstance(item.get("category"), str):
                    continue
                category = item["category"]
                if category in seen_categories:
                    diagnostics.append(_diagnostic("CONTRACT_COVERAGE_DUPLICATE",
                                                    f"{base}.contract.coverage[{coverage_index}].category", category))
                seen_categories.add(category)
            for category in categories - seen_categories:
                diagnostics.append(_diagnostic("CONTRACT_COVERAGE_INCOMPLETE", f"{base}.contract.coverage", category))

    region_ids = [region.get("region_id") for region in regions
                  if isinstance(region, dict) and isinstance(region.get("region_id"), str)]
    step_ids = [step.get("step_id") for step in steps
                if isinstance(step, dict) and isinstance(step.get("step_id"), str)]
    for region_id, count in Counter(region_ids).items():
        if count > 1:
            diagnostics.append(_diagnostic("DUPLICATE_REGION_ID", f"{base}.body.regions", str(region_id)))
    for step_id, count in Counter(step_ids).items():
        if count > 1:
            diagnostics.append(_diagnostic("DUPLICATE_STEP_ID", f"{base}.body.steps", str(step_id)))

    region_set = set(region_ids)
    step_set = set(step_ids)
    parent_by_id = {}
    for region_index, region in enumerate(regions):
        if not isinstance(region, dict):
            continue
        region_id = region.get("region_id")
        parent_id = region.get("parent_region_id")
        if not isinstance(region_id, str):
            continue
        parent_by_id[region_id] = parent_id
        if parent_id is not None and (not isinstance(parent_id, str) or parent_id not in region_set):
            diagnostics.append(_diagnostic("DANGLING_REGION_PARENT", f"{base}.body.regions[{region_index}].parent_region_id", str(parent_id)))
    for region_id in parent_by_id:
        seen = set()
        current = region_id
        while current in parent_by_id and parent_by_id[current] is not None:
            if current in seen:
                diagnostics.append(_diagnostic("REGION_PARENT_CYCLE", f"{base}.body.regions", str(region_id)))
                break
            seen.add(current)
            parent = parent_by_id[current]
            if not isinstance(parent, str):
                break
            current = parent

    for step_index, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        path = f"{base}.body.steps[{step_index}]"
        region_id = step.get("region_id")
        if region_id is not None and (not isinstance(region_id, str) or region_id not in region_set):
            diagnostics.append(_diagnostic("DANGLING_STEP_REGION", f"{path}.region_id", str(region_id)))
        if step.get("kind") == "opaque":
            source = step.get("source")
            boundary = step.get("boundary")
            valid = (isinstance(source, dict) and bool(source.get("path")) and
                     isinstance(source.get("start_byte"), int) and
                     isinstance(source.get("end_byte"), int) and
                     source["start_byte"] <= source["end_byte"] and
                     bool(step.get("impact")) and bool(step.get("unknowns")) and
                     isinstance(boundary, dict) and bool(boundary.get("effects")))
            if not valid:
                diagnostics.append(_diagnostic("OPAQUE_BOUNDARY_REQUIRED", path,
                                                "opaque steps need source, impact, unknowns and input/output/effect boundary"))
        if step.get("kind") == "compute":
            attributes = step.get("attributes")
            if not isinstance(attributes, dict) or not all(
                    isinstance(attributes.get(key), str) and attributes[key]
                    for key in ("operation", "type_rule", "evaluation_order")):
                diagnostics.append(_diagnostic("COMPUTE_SEMANTICS_REQUIRED", f"{path}.attributes",
                                                "compute steps must preserve operation, type rule and evaluation order, including explicit unknowns"))
        source = step.get("source")
        if isinstance(source, dict) and source.get("start_byte", 0) > source.get("end_byte", -1):
            diagnostics.append(_diagnostic("INVALID_SOURCE_SPAN", f"{path}.source", "end_byte precedes start_byte"))

    for edge_kind in ("control_edges", "data_edges"):
        edges = body.get(edge_kind, [])
        if not isinstance(edges, list):
            continue
        for edge_index, edge in enumerate(edges):
            if not isinstance(edge, dict):
                continue
            for endpoint in ("from_step", "to_step"):
                target = edge.get(endpoint)
                if not isinstance(target, str) or target not in step_set:
                    code = "DANGLING_CONTROL_EDGE" if edge_kind == "control_edges" else "DANGLING_DATA_EDGE"
                    diagnostics.append(_diagnostic(code, f"{base}.body.{edge_kind}[{edge_index}].{endpoint}",
                                                    str(target)))
    return diagnostics


def validate_algorithms(document: object) -> list[dict[str, str]]:
    """Return structural and reference diagnostics for an algorithm bundle.

    An empty list means the bundle conforms to this structural contract only.
    It does not imply source coverage, behavior correctness or runtime validation.
    """
    diagnostics = [
        _diagnostic("SCHEMA_INVALID", "/" + "/".join(map(str, error.absolute_path)), error.message)
        for error in Draft202012Validator(_SCHEMA).iter_errors(document)
    ]
    if not isinstance(document, dict) or not isinstance(document.get("algorithms"), list):
        return sorted(diagnostics, key=lambda item: (item["path"], item["code"], item["message"]))
    algorithms = document["algorithms"]
    seen_ids: set[str] = set()
    for index, algorithm in enumerate(algorithms):
        if not isinstance(algorithm, dict):
            continue
        diagnostics.extend(_algorithm_diagnostics(algorithm, index))
        algorithm_id = algorithm.get("algorithm_id")
        if not isinstance(algorithm_id, str):
            continue
        if algorithm_id in seen_ids:
            diagnostics.append(_diagnostic("DUPLICATE_ALGORITHM_ID", f"algorithms[{index}].algorithm_id", algorithm_id))
        seen_ids.add(algorithm_id)
    return sorted(diagnostics, key=lambda item: (item["path"], item["code"], item["message"]))
