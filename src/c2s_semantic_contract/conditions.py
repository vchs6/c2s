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
