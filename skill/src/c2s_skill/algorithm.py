"""Structural validation for language-neutral algorithm descriptions.

Validation checks the public shape and references; it does not prove that a
description is true of its source or that a pseudocode projection is equivalent.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator
from tree_sitter import Language, Parser
import tree_sitter_rust


_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "contracts" / "semantic-algorithm.schema.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
Draft202012Validator.check_schema(_SCHEMA)


def _diagnostic(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _source_offset(source: bytes, node: ast.AST) -> tuple[int, int]:
    lines = source.splitlines(keepends=True)
    start = sum(len(line) for line in lines[:node.lineno - 1]) + node.col_offset
    end = sum(len(line) for line in lines[:node.end_lineno - 1]) + node.end_col_offset
    return start, end


def _index_python_functions(source: bytes) -> tuple[ast.Module, dict[ast.AST, ast.AST], dict[int, ast.AST]]:
    tree = ast.parse(source)
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    functions = {_source_offset(source, node)[0]: node for node in ast.walk(tree)
                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) }
    return tree, parents, functions


def _index_rust_functions(source: bytes):
    parser = Parser(Language(tree_sitter_rust.language()))
    root = parser.parse(source).root_node
    functions = {}

    def visit(node) -> None:
        if node.type == "function_item":
            functions[node.start_byte] = node
        for child in node.named_children:
            visit(child)

    visit(root)
    return root, functions


def extract_python_algorithm(source: bytes, path: str, function_name: str,
                             start_byte: int | None = None, *, _tree=None,
                             _parents=None, _function_node=None) -> dict:
    """Build a source-located, explicitly partial algorithm record for one Python callable."""
    try:
        tree = _tree if _tree is not None else ast.parse(source, filename=path)
    except SyntaxError as error:
        raise ValueError(f"invalid Python syntax in {path}:{error.lineno}: {error.msg}") from error
    parents = _parents if _parents is not None else {
        child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}

    def qualified_name(node: ast.AST) -> str:
        names = [node.name]
        parent = parents.get(node)
        while parent is not None:
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.append(parent.name)
            parent = parents.get(parent)
        return ".".join(reversed(names))

    candidates = [_function_node] if _function_node is not None else [node for node in ast.walk(tree)
                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and
                  (node.name == function_name or qualified_name(node) == function_name) and
                  (start_byte is None or _source_offset(source, node)[0] == start_byte)]
    if not candidates:
        raise ValueError(f"Python function not found: {function_name}")
    if len(candidates) != 1:
        raise ValueError(f"Python function name is ambiguous: {function_name}")
    function = candidates[0]
    function_start, function_end = _source_offset(source, function)
    function_evidence = "src:" + hashlib.sha256(
        f"{path}\0{function_start}\0{function_end}".encode()).hexdigest()
    algorithm_id = "alg:" + hashlib.sha256(
        f"{path}\0{qualified_name(function)}\0{function_start}".encode()).hexdigest()
    implementation_id = "subject:" + hashlib.sha256(
        f"{path}\0{qualified_name(function)}\0{function_start}".encode()).hexdigest()
    regions = [{"region_id": "r0", "parent_region_id": None}]
    steps: list[dict] = []
    control_edges: list[dict] = []
    evidence_refs = {function_evidence}
    omissions = [{"reason": "Local read/write and value-flow relationships are not derived by this syntax slice.",
                  "impact": "Data dependencies between steps remain unknown."},
                 {"reason": "Implicit branch fallthrough and loop exit targets are not fully closed in this slice.",
                  "impact": "The control graph is a partial projection, not a complete CFG."},
                 {"reason": "Python for/while else blocks and try else/finally blocks are not yet lowered.",
                  "impact": "Some normal and cleanup paths are omitted from the structured body."}]
    omissions.append({"reason": "Closure capture and binding resolution are not analyzed.",
                      "impact": "Free-variable reads, writes and conditional binding targets remain unknown."})
    for candidate in ast.walk(function):
        if not isinstance(candidate, ast.Lambda):
            continue
        ancestor = parents.get(candidate)
        nested_scope = False
        while ancestor is not None and ancestor is not function:
            if isinstance(ancestor, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                nested_scope = True
                break
            ancestor = parents.get(ancestor)
        if not nested_scope:
            omissions.append({"reason": "Python lambda bodies are retained in source spans but are not lowered as separate callable algorithms.",
                              "impact": "Anonymous callable steps and their execution/capture semantics remain unresolved."})
            break
    if function.decorator_list:
        omissions.append({"reason": "Decorator expressions are retained as declaration metadata, not lowered into the function body.",
                          "impact": "Decorator evaluation and wrapper/callback replacement semantics remain unresolved."})
    outcomes = []
    nested_regions = 0
    next_step = 0

    def add_region(parent_region_id: str) -> str:
        nonlocal nested_regions
        nested_regions += 1
        region_id = f"r{nested_regions}"
        regions.append({"region_id": region_id, "parent_region_id": parent_region_id})
        return region_id

    def add_statement(node: ast.stmt, region_id: str) -> tuple[str, list[tuple[str, str, dict]]]:
        nonlocal next_step
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return "", []
        next_step += 1
        step_id = f"s{next_step}"
        start, end = _source_offset(source, node)
        evidence = "src:" + hashlib.sha256(f"{path}\0{start}\0{end}".encode()).hexdigest()
        evidence_refs.add(evidence)
        if isinstance(node, ast.If):
            kind = "select"
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            kind = "loop"
        elif isinstance(node, ast.Return):
            kind = "return"
            expression = source[_source_offset(source, node.value)[0]:_source_offset(source, node.value)[1]].decode() if node.value else "None"
            outcomes.append({"kind": "normal", "description": f"Returns {expression}",
                             "condition": {"kind": "unknown", "reason": "path feasibility is not analyzed"},
                             "evidence_refs": [evidence]})
        elif isinstance(node, ast.Raise):
            kind = "raise"
            expression = source[_source_offset(source, node.exc)[0]:_source_offset(source, node.exc)[1]].decode() if node.exc else "re-raise"
            outcomes.append({"kind": "error", "description": f"Raises {expression}",
                             "condition": {"kind": "unknown", "reason": "path feasibility is not analyzed"},
                             "evidence_refs": [evidence]})
        elif isinstance(node, ast.Try):
            kind = "handle"
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            kind = "resource"
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            kind = "call"
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
            kind = "assign"
        elif isinstance(node, ast.Pass):
            kind = "sequence"
        else:
            kind = "opaque"
        step = {"step_id": step_id, "kind": kind, "region_id": region_id,
                "evidence_refs": [evidence], "source": {"path": path, "start_byte": start, "end_byte": end}}
        if kind == "opaque":
            step.update({"impact": f"Python syntax kind {type(node).__name__} has no dedicated algorithm lowering.",
                         "unknowns": ["operation semantics", "control effects"],
                         "boundary": {"inputs": [], "outputs": [], "effects": ["unknown"]}})
        steps.append(step)
        branches: list[tuple[str, str, dict]] = []

        if isinstance(node, ast.If):
            condition_start, condition_end = _source_offset(source, node.test)
            condition = {"kind": "expression", "expression": source[condition_start:condition_end].decode()}
            true_region = add_region(region_id)
            true_first, _ = add_block(node.body, true_region)
            if true_first:
                control_edges.append({"from_step": step_id, "to_step": true_first, "kind": "branch_true", "condition": condition})
            if node.orelse:
                false_region = add_region(region_id)
                false_first, _ = add_block(node.orelse, false_region)
                if false_first:
                    control_edges.append({"from_step": step_id, "to_step": false_first, "kind": "branch_false",
                                          "condition": condition})
            else:
                branches.append((step_id, "branch_false", condition))
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            loop_region = add_region(region_id)
            body_first, body_last = add_block(node.body, loop_region)
            condition_node = node.test if isinstance(node, ast.While) else node.iter
            condition_start, condition_end = _source_offset(source, condition_node)
            condition = {"kind": "expression", "expression": source[condition_start:condition_end].decode()}
            if body_first:
                control_edges.append({"from_step": step_id, "to_step": body_first, "kind": "loop_body", "condition": condition})
            body_last_kind = next((step["kind"] for step in reversed(steps)
                                   if step["step_id"] == body_last), "")
            if body_last and body_last_kind not in {"return", "raise", "opaque"}:
                control_edges.append({"from_step": body_last, "to_step": step_id, "kind": "continue",
                                      "condition": {"kind": "unknown", "reason": "normal loop continuation"}})
            if node.orelse:
                else_region = add_region(region_id)
                else_first, _ = add_block(node.orelse, else_region)
                if else_first:
                    control_edges.append({"from_step": step_id, "to_step": else_first, "kind": "loop_exit",
                                          "condition": {"kind": "unknown", "reason": "loop exhaustion versus break is not resolved"}})
            else:
                branches.append((step_id, "loop_exit", condition))
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            with_region = add_region(region_id)
            first, _ = add_block(node.body, with_region)
            if first:
                control_edges.append({"from_step": step_id, "to_step": first, "kind": "next", "condition": {"kind": "true"}})
        elif isinstance(node, ast.Try):
            try_region = add_region(region_id)
            first, _ = add_block(node.body, try_region)
            if first:
                control_edges.append({"from_step": step_id, "to_step": first, "kind": "next", "condition": {"kind": "true"}})
            for handler in node.handlers:
                handler_region = add_region(region_id)
                handler_first, _ = add_block(handler.body, handler_region)
                if handler_first:
                    control_edges.append({"from_step": step_id, "to_step": handler_first, "kind": "exception",
                                          "condition": {"kind": "unknown", "reason": "exception dispatch is not resolved"}})
        return step_id, branches

    def add_block(body: list[ast.stmt], region_id: str) -> tuple[str, str]:
        first = ""
        previous = ""
        previous_kind = ""
        pending_edges: list[tuple[str, str, dict]] = []
        for statement in body:
            step_id, branches = add_statement(statement, region_id)
            if not step_id:
                continue
            if not first:
                first = step_id
            for source_step, kind, condition in pending_edges:
                control_edges.append({"from_step": source_step, "to_step": step_id,
                                      "kind": kind, "condition": condition})
            if previous and previous_kind not in {"return", "raise", "select", "loop", "handle"}:
                control_edges.append({"from_step": previous, "to_step": step_id, "kind": "next",
                                      "condition": {"kind": "true"}})
            previous = step_id
            previous_kind = next(step["kind"] for step in reversed(steps) if step["step_id"] == step_id)
            pending_edges = branches
        return first, previous

    add_block(function.body, "r0")
    args = function.args
    parameters = [*args.posonlyargs, *args.args]
    positional_defaults = [None] * (len(parameters) - len(args.defaults)) + list(args.defaults)
    parameters_and_defaults = list(zip(parameters, positional_defaults))
    if args.vararg:
        parameters_and_defaults.append((args.vararg, None))
    parameters_and_defaults.extend(zip(args.kwonlyargs, args.kw_defaults))
    if args.kwarg:
        parameters_and_defaults.append((args.kwarg, None))
    inputs = []
    for argument, default in parameters_and_defaults:
        start, end = _source_offset(source, argument)
        if default is not None:
            _, end = _source_offset(source, default)
        evidence = "src:" + hashlib.sha256(f"{path}\0{start}\0{end}".encode()).hexdigest()
        evidence_refs.add(evidence)
        raw = source[start:end].decode()
        inputs.append({"name": argument.arg, "description": f"Python parameter syntax: {raw}",
                       "evidence_refs": [evidence]})
    outputs = []
    if function.returns is not None:
        start, end = _source_offset(source, function.returns)
        evidence = "src:" + hashlib.sha256(f"{path}\0{start}\0{end}".encode()).hexdigest()
        evidence_refs.add(evidence)
        outputs.append({"name": "return", "description": f"Python return annotation: {source[start:end].decode()}",
                        "type_rule": "annotation syntax; not type-checked", "evidence_refs": [evidence]})
    coverage = [
        {"category": "inputs", "state": "complete", "evidence_refs": [function_evidence]},
        {"category": "outputs", "state": "unknown" if not outputs else "partial", "evidence_refs": [function_evidence],
         "reason": "Return values are path-dependent; missing return annotations are not inferred as types."},
        {"category": "preconditions", "state": "unknown", "evidence_refs": [function_evidence],
         "reason": "No formal precondition analysis is implemented."},
        {"category": "outcomes", "state": "partial", "evidence_refs": [function_evidence],
         "reason": "Only explicit return and raise syntax is enumerated; path feasibility is unknown."},
        {"category": "effects", "state": "unknown", "evidence_refs": [function_evidence],
         "reason": "Calls, aliases and runtime effects are not resolved."},
        {"category": "ordering", "state": "partial", "evidence_refs": [function_evidence],
         "reason": "Only direct statement order and selected control links are represented."},
    ]
    algorithm = {
        "algorithm_id": algorithm_id, "source_digest": hashlib.sha256(source).hexdigest(),
        "purpose": "current_implementation", "problem": qualified_name(function),
        "body": {"regions": regions, "steps": steps, "control_edges": control_edges, "data_edges": []},
        "contract": {"inputs": inputs, "outputs": outputs, "preconditions": [], "outcomes": outcomes,
                     "effects": [{"kind": "unknown", "description": "Runtime and indirect effects not analyzed",
                                  "condition": {"kind": "unknown", "reason": "calls and aliases unresolved"},
                                  "evidence_refs": [function_evidence]}],
                     "ordering_constraints": [], "coverage": coverage},
        "management": {"status": "unresolved", "project_subject_ids": []},
        "implementation_refs": [{"subject_id": implementation_id}],
        "evidence_refs": sorted(evidence_refs), "omissions": omissions,
    }
    return {"schema_version": "1.0.0", "algorithm": algorithm}


def extract_rust_algorithm(source: bytes, path: str, function_name: str,
                           start_byte: int | None = None, *, _root_node=None,
                           _function_node=None) -> dict:
    """Build a source-located, explicitly partial algorithm record for one Rust function."""
    root = _root_node
    if root is None:
        parser = Parser(Language(tree_sitter_rust.language()))
        root = parser.parse(source).root_node
    functions = [_function_node] if _function_node is not None else []

    def find_functions(node) -> None:
        if node.type == "function_item":
            name_node = node.child_by_field_name("name")
            if name_node and source[name_node.start_byte:name_node.end_byte].decode() == function_name and \
                    (start_byte is None or node.start_byte == start_byte):
                functions.append(node)
        for child in node.named_children:
            find_functions(child)

    if _function_node is None:
        find_functions(root)
    if not functions:
        raise ValueError(f"Rust function not found: {function_name}")
    if len(functions) != 1:
        raise ValueError(f"Rust function name is ambiguous: {function_name}")
    function = functions[0]
    if function.has_error:
        raise ValueError(f"Rust function has syntax errors: {function_name}")
    body_node = function.child_by_field_name("body")
    if body_node is None:
        raise ValueError(f"Rust function has no body: {function_name}")

    def evidence_for(node) -> str:
        return "src:" + hashlib.sha256(f"{path}\0{node.start_byte}\0{node.end_byte}".encode()).hexdigest()

    function_evidence = evidence_for(function)
    algorithm_id = "alg:" + hashlib.sha256(
        f"{path}\0{function_name}\0{function.start_byte}".encode()).hexdigest()
    implementation_id = "subject:" + hashlib.sha256(
        f"{path}\0{function_name}\0{function.start_byte}".encode()).hexdigest()
    regions = [{"region_id": "r0", "parent_region_id": None}]
    steps: list[dict] = []
    control_edges: list[dict] = []
    evidence_refs = {function_evidence}
    outcomes = []
    omissions = [{"reason": "Rust type checking, macro expansion, and call resolution are not run.",
                  "impact": "Types, indirect effects, generated code and callee outcomes remain unknown."},
                 {"reason": "Data dependencies and some exceptional/early-exit control transfers are not lowered.",
                  "impact": "The structured body is a syntax projection, not a complete CFG."},
                 {"reason": "Attributes such as cfg are not evaluated and conditional compilation is not selected.",
                  "impact": "The emitted syntax may not exist in every target configuration."}]
    closure_omission_added = False
    next_region = 0
    next_step = 0

    def add_region(parent_id: str) -> str:
        nonlocal next_region
        next_region += 1
        region_id = f"r{next_region}"
        regions.append({"region_id": region_id, "parent_region_id": parent_id})
        return region_id

    def text_of(node) -> str:
        return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    def contains_closure(node) -> bool:
        return node.type == "closure_expression" or any(contains_closure(child) for child in node.named_children)

    def condition_for(node) -> dict:
        return {"kind": "expression", "expression": text_of(node)} if node else {
            "kind": "unknown", "reason": "condition expression is not represented by this syntax node"}

    def add_node(original_node, region_id: str) -> tuple[str, list[tuple[str, str, dict]]]:
        nonlocal next_step
        node = original_node
        if node.type == "expression_statement" and node.named_children:
            node = node.named_children[0]
        nonlocal closure_omission_added
        if contains_closure(node) and not closure_omission_added:
            omissions.append({"reason": "Rust closure bodies are not lowered as separate callables, and capture mode/bindings are unresolved.",
                              "impact": "Deferred body execution and captured locations remain unknown."})
            closure_omission_added = True
        next_step += 1
        step_id = f"s{next_step}"
        evidence = evidence_for(node)
        evidence_refs.add(evidence)
        if node.type == "if_expression":
            kind = "select"
        elif node.type in {"loop_expression", "while_expression", "for_expression"}:
            kind = "loop"
        elif node.type == "let_declaration":
            kind = "bind"
        elif node.type == "call_expression":
            kind = "call"
        elif node.type in {"assignment_expression", "compound_assignment_expr"}:
            kind = "assign"
        elif node.type == "binary_expression":
            kind = "compute"
        elif node.type == "return_expression":
            kind = "return"
            outcomes.append({"kind": "normal", "description": f"Returns {text_of(node)}",
                             "condition": {"kind": "unknown", "reason": "path feasibility is not analyzed"},
                             "evidence_refs": [evidence]})
        elif node.type == "match_expression":
            kind = "select"
        elif node.type in {"macro_invocation", "break_expression", "continue_expression", "try_expression"}:
            kind = "opaque"
        elif node.type in {"integer_literal", "boolean_literal", "string_literal"}:
            if original_node.type == "expression_statement":
                kind = "compute"
            else:
                kind = "return"
                outcomes.append({"kind": "normal", "description": f"Implicit tail result {text_of(node)}",
                                 "condition": {"kind": "unknown", "reason": "tail-expression type is not checked"},
                                 "evidence_refs": [evidence]})
        else:
            kind = "opaque"
        step = {"step_id": step_id, "kind": kind, "region_id": region_id,
                "evidence_refs": [evidence],
                "source": {"path": path, "start_byte": node.start_byte, "end_byte": node.end_byte}}
        if kind == "compute":
            operator = (next((child.type for child in node.children if not child.is_named), "unknown")
                        if node.type == "binary_expression" else node.type)
            step["attributes"] = {"operation": operator, "type_rule": "unknown (not type-checked)",
                                  "evaluation_order": "unknown (language evaluation details not resolved)"}
        if kind == "opaque":
            step.update({"impact": ("Rust closure body and capture semantics are unresolved."
                                     if node.type == "closure_expression" else
                                     f"Rust syntax kind {node.type} requires unsupported semantic analysis."),
                         "unknowns": ["expanded operation", "control or call effect"],
                         "boundary": {"inputs": [], "outputs": [], "effects": ["unknown"]}})
        steps.append(step)
        pending: list[tuple[str, str, dict]] = []
        if node.type == "if_expression":
            condition_node = node.child_by_field_name("condition")
            condition = condition_for(condition_node)
            consequence = node.child_by_field_name("consequence")
            if consequence:
                branch_region = add_region(region_id)
                first, _ = add_block(consequence.named_children, branch_region)
                if first:
                    control_edges.append({"from_step": step_id, "to_step": first, "kind": "branch_true",
                                          "condition": condition})
            alternative = node.child_by_field_name("alternative")
            if alternative:
                branch_region = add_region(region_id)
                branch_nodes = alternative.named_children if alternative.type == "block" else [alternative]
                first, _ = add_block(branch_nodes, branch_region)
                if first:
                    control_edges.append({"from_step": step_id, "to_step": first, "kind": "branch_false",
                                          "condition": condition})
            else:
                pending.append((step_id, "branch_false", condition))
        elif node.type in {"loop_expression", "while_expression", "for_expression"}:
            body = node.child_by_field_name("body")
            if body:
                loop_region = add_region(region_id)
                first, last = add_block(body.named_children, loop_region)
                condition_node = node.child_by_field_name("condition") or node.child_by_field_name("value")
                condition = condition_for(condition_node)
                if first:
                    control_edges.append({"from_step": step_id, "to_step": first, "kind": "loop_body",
                                          "condition": condition})
                last_kind = next((step["kind"] for step in reversed(steps)
                                  if step["step_id"] == last), "")
                if last and last_kind not in {"return", "opaque"}:
                    control_edges.append({"from_step": last, "to_step": step_id, "kind": "continue",
                                          "condition": {"kind": "unknown", "reason": "normal loop continuation"}})
            condition_node = node.child_by_field_name("condition") or node.child_by_field_name("value")
            pending.append((step_id, "loop_exit", condition_for(condition_node)))
        elif node.type == "match_expression":
            value = node.child_by_field_name("value")
            match_block = next((child for child in node.named_children if child.type == "match_block"), None)
            if match_block:
                for arm in match_block.named_children:
                    if arm.type != "match_arm":
                        continue
                    arm_region = add_region(region_id)
                    children = arm.named_children
                    pattern = children[0] if children else None
                    result_node = children[-1] if children else None
                    arm_nodes = result_node.named_children if result_node and result_node.type == "block" else ([result_node] if result_node else [])
                    first, _ = add_block(arm_nodes, arm_region)
                    if first:
                        control_edges.append({"from_step": step_id, "to_step": first, "kind": "branch_true",
                                              "condition": condition_for(pattern or value)})
            omissions.append({"reason": "Rust match arm failure/guard sequencing is not fully lowered.",
                              "impact": "Only arm entry conditions are shown; exhaustiveness is not proven."})
        return step_id, pending

    def add_block(nodes: list, region_id: str) -> tuple[str, str]:
        first = ""
        previous = ""
        previous_kind = ""
        pending_edges: list[tuple[str, str, dict]] = []
        for index, node in enumerate(nodes):
            step_id, pending = add_node(node, region_id)
            if not first:
                first = step_id
            for source_step, edge_kind, condition in pending_edges:
                control_edges.append({"from_step": source_step, "to_step": step_id,
                                      "kind": edge_kind, "condition": condition})
            if previous and previous_kind not in {"return", "select", "loop", "opaque"}:
                control_edges.append({"from_step": previous, "to_step": step_id, "kind": "next",
                                      "condition": {"kind": "true"}})
            previous = step_id
            previous_kind = steps[-1]["kind"]
            pending_edges = pending
        return first, previous

    add_block(body_node.named_children, "r0")
    parameter_list = function.child_by_field_name("parameters")
    inputs = []
    if parameter_list:
        for parameter in parameter_list.named_children:
            if parameter.type not in {"parameter", "self_parameter"}:
                continue
            pattern = parameter.child_by_field_name("pattern")
            name = text_of(pattern) if pattern else "self"
            evidence = evidence_for(parameter)
            evidence_refs.add(evidence)
            inputs.append({"name": name, "description": f"Rust parameter syntax: {text_of(parameter)}",
                           "evidence_refs": [evidence]})
    return_type = function.child_by_field_name("return_type")
    outputs = []
    if return_type:
        evidence = evidence_for(return_type)
        evidence_refs.add(evidence)
        outputs.append({"name": "return", "description": f"Rust return type syntax: {text_of(return_type)}",
                        "type_rule": "annotation syntax; not type-checked", "evidence_refs": [evidence]})
    coverage = [
        {"category": "inputs", "state": "complete", "evidence_refs": [function_evidence]},
        {"category": "outputs", "state": "partial" if outputs else "unknown", "evidence_refs": [function_evidence],
         "reason": "Syntax signatures do not establish inferred return types or all result paths."},
        {"category": "preconditions", "state": "unknown", "evidence_refs": [function_evidence],
         "reason": "No precondition or refinement analysis is implemented."},
        {"category": "outcomes", "state": "partial", "evidence_refs": [function_evidence],
         "reason": "Only explicit returns and the block tail are represented; `?` and panic paths remain opaque."},
        {"category": "effects", "state": "unknown", "evidence_refs": [function_evidence],
         "reason": "Calls, macro expansions, aliasing and runtime effects are unresolved."},
        {"category": "ordering", "state": "partial", "evidence_refs": [function_evidence],
         "reason": "Only direct syntax sequencing and selected control links are represented."},
    ]
    algorithm = {
        "algorithm_id": algorithm_id, "source_digest": hashlib.sha256(source).hexdigest(),
        "purpose": "current_implementation", "problem": function_name,
        "body": {"regions": regions, "steps": steps, "control_edges": control_edges, "data_edges": []},
        "contract": {"inputs": inputs, "outputs": outputs, "preconditions": [], "outcomes": outcomes,
                     "effects": [{"kind": "unknown", "description": "Calls and runtime effects are unresolved",
                                  "condition": {"kind": "unknown", "reason": "no type/call analysis"},
                                  "evidence_refs": [function_evidence]}],
                     "ordering_constraints": [], "coverage": coverage},
        "management": {"status": "unresolved", "project_subject_ids": []},
        "implementation_refs": [{"subject_id": implementation_id}],
        "evidence_refs": sorted(evidence_refs), "omissions": omissions,
    }
    return {"schema_version": "1.0.0", "algorithm": algorithm}


def _algorithm_diagnostics(algorithm: dict, index: int) -> list[dict[str, str]]:
    diagnostics: list[dict[str, str]] = []
    base = f"algorithms[{index}]"
    management = algorithm.get("management")
    if isinstance(management, dict):
        status = management.get("status")
        project_ids = management.get("project_subject_ids", [])
        valid = ((status == "resolved" and len(project_ids) == 1)
                 or (status == "ambiguous" and len(project_ids) >= 2)
                 or (status == "unresolved" and len(project_ids) == 0))
        if not valid:
            diagnostics.append(_diagnostic("MANAGEMENT_PROJECT_CARDINALITY",
                                           f"{base}.management.project_subject_ids",
                                           "Project candidate count must match resolved/ambiguous/unresolved status"))
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


def render_pseudocode(algorithm: dict, source: bytes) -> dict:
    """Render a conservative readable view while retaining source evidence and gaps."""
    body = algorithm.get("body", {})
    regions = {item["region_id"]: item.get("parent_region_id") for item in body.get("regions", [])}

    def depth(region_id: str) -> int:
        result, seen = 0, set()
        while region_id in regions and regions[region_id] is not None and region_id not in seen:
            seen.add(region_id)
            result += 1
            region_id = regions[region_id]
        return result

    translations = {"select": "如果", "loop": "循环", "return": "返回", "raise": "抛出",
                    "handle": "处理异常", "resource": "管理资源", "call": "执行", "assign": "计算并赋值",
                    "bind": "定义", "compute": "计算", "sequence": "继续", "opaque": "未解析步骤"}
    lines = []
    references = set()
    steps = sorted(body.get("steps", []), key=lambda item: (
            item.get("source", {}).get("start_byte", 0), item.get("source", {}).get("end_byte", 0)))
    false_branch_targets = {edge.get("to_step") for edge in body.get("control_edges", [])
                            if edge.get("kind") == "branch_false"}
    for step in steps:
        if step.get("step_id") in false_branch_targets:
            lines.append("  " * max(0, depth(step.get("region_id", "r0")) - 1) + "否则")
        span = step.get("source", {})
        raw = source[span.get("start_byte", 0):span.get("end_byte", 0)].decode("utf-8", errors="replace")
        statement = next((line.strip() for line in raw.splitlines() if line.strip()), "")
        kind = step.get("kind", "opaque")
        if kind in {"select", "loop"}:
            statement = statement.splitlines()[0].strip()
            if kind == "select" and statement.startswith("match"):
                statement = "按值匹配 " + statement.removeprefix("match").strip()
                keyword = ""
            elif kind == "select":
                keyword = "if"
            elif statement.startswith("loop"):
                statement = "无限循环"
                keyword = ""
            else:
                keyword = "while" if statement.startswith("while") else "for"
            statement = re.sub(rf"^{keyword}\b\s*", "", statement)
            statement = re.sub(r"\s*\{\s*$", "", statement)
            statement = re.sub(r"\s*:\s*$", "", statement)
        elif kind == "return":
            statement = re.sub(r"^return\b", "", statement).strip().rstrip(";") or "无值"
        elif kind == "raise":
            statement = re.sub(r"^raise\b", "", statement).strip() or "当前异常"
        elif kind == "call":
            statement = re.sub(r";\s*$", "", statement)
        prefix = translations.get(kind, "未解析步骤")
        lines.append("  " * depth(step.get("region_id", "r0")) + f"{prefix} {statement}".rstrip())
        references.update(step.get("evidence_refs", []))
    return {"schema_version": "1.0.0", "format": "c2s-pseudocode-1", "function": algorithm.get("problem"),
            "text": "\n".join(lines), "complete": False,
            "evidence_refs": sorted(references), "omissions": list(algorithm.get("omissions", [])),
            "claim_scope": "source_mapped_partial_pseudocode"}
