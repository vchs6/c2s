"""Bounded Boolean/enum condition reasoning for context overlap checks."""

from __future__ import annotations

from itertools import product
from math import prod


_ASSIGNMENT_BUDGET = 4096


def _validate_domains(domains: dict) -> str | None:
    if not isinstance(domains, dict):
        return "CONDITION_DOMAIN_INVALID"
    for key, values in domains.items():
        if not isinstance(key, str) or not key or not isinstance(values, list) or not values:
            return "CONDITION_DOMAIN_INVALID"
        if any(not isinstance(value, (str, bool)) for value in values):
            return "CONDITION_DOMAIN_INVALID"
        if len(values) != len(set(values)):
            return "CONDITION_DOMAIN_INVALID"
        if len({type(value) for value in values}) != 1:
            return "CONDITION_DOMAIN_INVALID"
    return None


def _validate_expression(expression: object, domains: dict) -> str | None:
    if not isinstance(expression, dict) or not isinstance(expression.get("kind"), str):
        return "CONDITION_UNSUPPORTED_FRAGMENT"
    kind = expression["kind"]
    if kind in {"true", "false"}:
        return None if set(expression) == {"kind"} else "CONDITION_UNSUPPORTED_FRAGMENT"
    if kind in {"eq", "neq"}:
        if set(expression) != {"kind", "key", "value"}:
            return "CONDITION_UNSUPPORTED_FRAGMENT"
        key = expression["key"]
        if not isinstance(key, str) or key not in domains:
            return "CONDITION_DOMAIN_UNKNOWN"
        value = expression["value"]
        if type(value) not in {type(item) for item in domains[key]} or value not in domains[key]:
            return "CONDITION_VALUE_OUTSIDE_DOMAIN"
        return None
    if kind in {"all", "any"}:
        if set(expression) != {"kind", "conditions"} or not isinstance(expression["conditions"], list):
            return "CONDITION_UNSUPPORTED_FRAGMENT"
        for child in expression["conditions"]:
            error = _validate_expression(child, domains)
            if error:
                return error
        return None
    if kind == "not":
        if set(expression) != {"kind", "condition"}:
            return "CONDITION_UNSUPPORTED_FRAGMENT"
        return _validate_expression(expression["condition"], domains)
    return "CONDITION_UNSUPPORTED_FRAGMENT"


def _evaluate(expression: dict, assignment: dict) -> bool:
    kind = expression["kind"]
    if kind == "true":
        return True
    if kind == "false":
        return False
    if kind == "eq":
        return assignment[expression["key"]] == expression["value"]
    if kind == "neq":
        return assignment[expression["key"]] != expression["value"]
    if kind == "all":
        return all(_evaluate(child, assignment) for child in expression["conditions"])
    if kind == "any":
        return any(_evaluate(child, assignment) for child in expression["conditions"])
    return not _evaluate(expression["condition"], assignment)


def condition_satisfiability(conditions: list[dict], domains: dict) -> dict:
    """Return sat with a witness, unsat after exhaustive evaluation, or undetermined."""
    domain_error = _validate_domains(domains)
    if domain_error:
        return {"status": "undetermined", "witness": None, "reason": domain_error}
    if not isinstance(conditions, list):
        return {"status": "undetermined", "witness": None, "reason": "CONDITION_UNSUPPORTED_FRAGMENT"}
    for condition in conditions:
        error = _validate_expression(condition, domains)
        if error:
            return {"status": "undetermined", "witness": None, "reason": error}
    combinations = prod(len(values) for values in domains.values())
    if combinations > _ASSIGNMENT_BUDGET:
        return {"status": "undetermined", "witness": None, "reason": "CONDITION_BUDGET_EXCEEDED"}
    keys = list(domains)
    for values in product(*(domains[key] for key in keys)):
        assignment = dict(zip(keys, values))
        if all(_evaluate(condition, assignment) for condition in conditions):
            return {"status": "sat", "witness": assignment, "reason": None}
    return {"status": "unsat", "witness": None, "reason": None}


def classify_claim_overlap(left: dict, right: dict, domains: dict) -> dict:
    """Classify whether two different values can apply in the same context."""
    if not isinstance(left, dict) or not isinstance(right, dict) or "value" not in left or "value" not in right:
        return {"status": "undetermined", "witness": None, "reason": "CLAIM_SHAPE_INVALID"}
    if left["value"] == right["value"]:
        return {"status": "compatible", "witness": None, "reason": None}
    truth = condition_satisfiability(
        [left.get("condition", {"kind": "true"}), right.get("condition", {"kind": "true"})], domains)
    if truth["status"] == "unsat":
        return {"status": "compatible", "witness": None, "reason": None}
    if truth["status"] == "sat":
        return {"status": "conflict", "witness": truth["witness"], "reason": None}
    return {"status": "potential_conflict", "witness": None, "reason": truth["reason"]}


def diagnose_conditional_cycles(edges: list[dict], domains: dict, *, cycle_budget: int = 4096) -> dict:
    """Enumerate simple directed cycles and jointly solve their edge conditions.

    The original edge records are returned unchanged. This diagnoses whether a
    cycle can be active; it does not decide whether a build rule is erroneous.
    """
    if not isinstance(edges, list) or not isinstance(cycle_budget, int) or cycle_budget < 1:
        return {"edges": edges, "cycles": [], "diagnostics": ["DEPENDENCY_GRAPH_INVALID"]}
    adjacency: dict[str, list[dict]] = {}
    vertices: set[str] = set()
    edge_ids: set[str] = set()
    for edge in edges:
        if (not isinstance(edge, dict) or not isinstance(edge.get("edgeId"), str)
                or not isinstance(edge.get("source"), str) or not isinstance(edge.get("target"), str)
                or edge["edgeId"] in edge_ids):
            return {"edges": edges, "cycles": [], "diagnostics": ["DEPENDENCY_GRAPH_INVALID"]}
        edge_ids.add(edge["edgeId"])
        vertices.update((edge["source"], edge["target"]))
        adjacency.setdefault(edge["source"], []).append(edge)

    cycles: list[dict] = []
    exceeded = False
    explored = 0
    exploration_budget = max(1024, cycle_budget * 100)
    for start in sorted(vertices):
        stack: list[tuple[str, set[str], list[dict]]] = [(start, {start}, [])]
        while stack:
            current, visited, path_edges = stack.pop()
            for edge in reversed(adjacency.get(current, [])):
                explored += 1
                if explored > exploration_budget:
                    exceeded = True
                    break
                target = edge["target"]
                if target == start:
                    if len(cycles) == cycle_budget:
                        exceeded = True
                        break
                    cycle_edges = [*path_edges, edge]
                    result = condition_satisfiability(
                        [item.get("condition", {"kind": "true"}) for item in cycle_edges], domains)
                    status = {"sat": "possible", "unsat": "infeasible", "undetermined": "undetermined"}[result["status"]]
                    cycles.append({"nodes": [start, *[item["target"] for item in cycle_edges]],
                                   "edgeIds": [item["edgeId"] for item in cycle_edges],
                                   "status": status, "witness": result["witness"],
                                   "reason": result["reason"]})
                elif target not in visited and target >= start:
                    stack.append((target, visited | {target}, [*path_edges, edge]))
            if exceeded:
                break
        if exceeded:
            break
    cycles.sort(key=lambda item: tuple(item["edgeIds"]))
    return {"edges": edges, "cycles": cycles,
            "diagnostics": ["DEPENDENCY_CYCLE_BUDGET_EXCEEDED"] if exceeded else []}
