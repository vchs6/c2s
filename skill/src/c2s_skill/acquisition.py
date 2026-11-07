"""Exhaustive syntax-backed declaration acquisition for Python and Rust."""

from __future__ import annotations

import ast
import hashlib
import os
import re
import json
import importlib.metadata
import platform
import tomllib
import shutil
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path

from .inventory import InventoryEntry, inventory_tree, source_fingerprint


@dataclass(frozen=True, slots=True)
class Fact:
    id: str
    kind: str
    name: str
    path: str
    start_byte: int
    end_byte: int
    layer: str
    claim_mode: str
    text: str
    owner: str | None = None
    subject_id: str = ""
    evidence_included: bool = True


@dataclass(frozen=True, slots=True)
class SourceConstruct:
    construct_id: str
    source_key: str
    language: str
    syntax_kind: str
    name: str
    path: str
    start_byte: int
    end_byte: int
    parent_id: str | None
    source_sha256: str
    parser_id: str
    parser_version: str
    opaque: bool
    text: str
    declared_type: str | None = None


@dataclass(frozen=True, slots=True)
class ParseResult:
    path: str
    language: str
    source_sha256: str
    facts: tuple[Fact, ...]
    syntax_node_count: int
    parse_complete: bool
    diagnostics: tuple[str, ...]
    constructs: tuple[SourceConstruct, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectScan:
    root: str
    source_files: int
    parsed_files: int
    fact_count: int
    syntax_node_count: int
    files: tuple[ParseResult, ...]
    source_digest: str
    project_facts: tuple[Fact, ...]
    inventory: tuple[InventoryEntry, ...]


def analysis_profile_digest() -> str:
    """Fingerprint parser/runtime/tool versions used to interpret cached facts."""
    cargo = os.environ.get("CARGO") or shutil.which("cargo")
    cargo_version = "unavailable"
    if cargo:
        try:
            cargo_version = subprocess.run([cargo, "--version"], capture_output=True,
                                           text=True, timeout=3, check=True).stdout.strip()
        except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired):
            cargo_version = "unavailable_or_failed"
    try:
        dependencies = {name: importlib.metadata.version(name)
                        for name in ("tree-sitter", "tree-sitter-python", "tree-sitter-rust")}
    except importlib.metadata.PackageNotFoundError as error:
        dependencies = {"missing": error.name or "unknown"}
    matrix_path = Path(__file__).resolve().parents[2] / "contracts" / "tool-capabilities.json"
    matrix_digest = hashlib.sha256(matrix_path.read_bytes()).hexdigest() if matrix_path.is_file() else "unavailable"
    profile = {"analyzer": "c2s-semantic-facts/0.7.0", "python": platform.python_version(),
               "platform": platform.platform(), "parsers": dependencies, "cargo": cargo_version,
               "tool_capability_matrix": matrix_digest}
    return hashlib.sha256(json.dumps(profile, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _make_fact(path: str, source: bytes, kind: str, name: str, start: int, end: int,
               owner: str | None = None) -> Fact:
    identity = f"{path}\0{kind}\0{name}\0{start}\0{end}".encode()
    if kind in {"project_name", "language_declared"}:
        layer = "E0"
    elif kind == "workspace_member":
        layer = "E1"
    elif kind == "behavior_contract":
        layer = "E3"
    elif kind in {"class", "function", "struct", "enum", "trait", "impl", "field", "variant", "module",
                  "import", "type_alias", "constant", "constant_item", "static_item"}:
        layer = "E2"
    else:
        layer = "E4"
    claim_mode = "declaration" if kind in {"project_name", "language_declared"} else "syntax"
    if kind == "workspace_member":
        claim_mode = "cargo_metadata"
    if kind == "behavior_contract":
        claim_mode = "documentation"
    if kind in {"function", "behavior_contract"}:
        subject_type = "function"
        subject_name = f"{owner}.{name}" if owner else name
    elif kind in {"algorithm_step", "local_binding"} and owner:
        subject_type, subject_name = "function", owner
    elif kind in {"project_name", "language_declared"}:
        subject_type, subject_name = "project", "root"
    elif kind == "workspace_member":
        subject_type, subject_name = "package", name
    else:
        subject_type = kind
        subject_name = f"{owner}.{name}" if owner else name
    subject_identity = hashlib.sha256(f"{path}\0{subject_type}\0{subject_name}".encode()).hexdigest()
    return Fact(hashlib.sha256(identity).hexdigest(), kind, name, path, start, end, layer,
                claim_mode, source[start:end].decode("utf-8", errors="replace"), owner, subject_identity)


def _namespace_fact(fact: Fact, project_root: Path) -> Fact:
    namespace = str(project_root.resolve(strict=True)).encode("utf-8")
    identity = hashlib.sha256(namespace + b"\0" + fact.id.encode("ascii")).hexdigest()
    subject_identity = hashlib.sha256(namespace + b"\0" + fact.subject_id.encode("ascii")).hexdigest()
    return replace(fact, id=identity, subject_id=subject_identity)


def _namespace_construct(construct: SourceConstruct, project_root: Path) -> SourceConstruct:
    namespace = str(project_root.resolve(strict=True)).encode("utf-8")
    return replace(construct,
        construct_id=hashlib.sha256(namespace + b"\0" + construct.construct_id.encode("ascii")).hexdigest(),
        source_key=hashlib.sha256(namespace + b"\0" + construct.source_key.encode("ascii")).hexdigest(),
        parent_id=(hashlib.sha256(namespace + b"\0" + construct.parent_id.encode("ascii")).hexdigest()
                   if construct.parent_id else None))


def cargo_workspace_facts(root: Path) -> tuple[list[Fact], str | None]:
    """Resolve workspace package membership with Cargo without resolving dependencies."""
    manifest = root / "Cargo.toml"
    if not manifest.is_file() or manifest.is_symlink():
        return [], "UNSUPPORTED_SOURCE:cargo-manifest-not-found"
    cargo = os.environ.get("CARGO") or shutil.which("cargo")
    if not cargo:
        return [], "TOOL_UNAVAILABLE:cargo"
    try:
        completed = subprocess.run(
            [cargo, "metadata", "--format-version", "1", "--no-deps", "--offline",
             "--manifest-path", str(manifest)],
            cwd=root, check=True, capture_output=True, text=True, timeout=20,
        )
        metadata = json.loads(completed.stdout)
        source = manifest.read_bytes()
        facts = []
        for package in metadata.get("packages", []):
            package_manifest = Path(package["manifest_path"])
            relative_manifest = package_manifest.relative_to(root).as_posix()
            facts.append(_namespace_fact(_make_fact("Cargo.toml", source, "workspace_member", package["name"],
                                                    0, len(source), relative_manifest), root))
        return facts, None
    except subprocess.TimeoutExpired:
        return [], "TOOL_FAILED:cargo-metadata-timeout"
    except (subprocess.CalledProcessError, OSError, ValueError, KeyError, TypeError):
        return [], "TOOL_FAILED:cargo-metadata"


def _python_facts(path: str, source: bytes, tree: ast.AST) -> list[Fact]:
    facts: list[Fact] = []
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}

    def scope_name(node, include_node: bool = False) -> str | None:
        current = node if include_node else parents.get(node)
        names = []
        while current is not None:
            if isinstance(current, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                names.append(current.name)
            current = parents.get(current)
        return ".".join(reversed(names)) or None

    algorithm_nodes = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith,
                       ast.Return, ast.Raise, ast.Call, ast.Await, ast.BoolOp, ast.Compare,
                       ast.BinOp, ast.UnaryOp, ast.NamedExpr, ast.Assert, ast.Match,
                       ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Delete, ast.Yield, ast.YieldFrom)

    def binding_nodes(target) -> list[ast.Name]:
        if isinstance(target, ast.Name):
            return [target]
        if isinstance(target, (ast.Tuple, ast.List)):
            return [node for element in target.elts for node in binding_nodes(element)]
        if isinstance(target, ast.Starred):
            return binding_nodes(target.value)
        return []

    def byte_span(node) -> tuple[int, int]:
        lines = source.splitlines(keepends=True)
        start = sum(len(line) for line in lines[:node.lineno - 1]) + node.col_offset
        end = sum(len(line) for line in lines[:node.end_lineno - 1]) + node.end_col_offset
        return start, end
    for node in ast.walk(tree):
        kind = None
        name = None
        if isinstance(node, ast.ClassDef): kind, name = "class", node.name
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)): kind, name = "function", node.name
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            kind = "import"
            name = ",".join(alias.name for alias in node.names)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if all(isinstance(t, (ast.Name, ast.Attribute)) for t in targets):
                kind = "field" if isinstance(parents.get(node), ast.ClassDef) else "constant"
                names = [getattr(t, "id", getattr(t, "attr", "")) for t in targets]
                name = ",".join(names)
        if kind and name:
            # AST columns are UTF-8 byte offsets, matching the public evidence contract.
            lines = source.splitlines(keepends=True)
            start = sum(len(line) for line in lines[:node.lineno - 1]) + node.col_offset
            end = sum(len(line) for line in lines[:node.end_lineno - 1]) + node.end_col_offset
            owner = scope_name(node)
            facts.append(_make_fact(path, source, kind, name, start, end, owner))
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                doc = first.value
                lines = source.splitlines(keepends=True)
                start = sum(len(line) for line in lines[:doc.lineno - 1]) + doc.col_offset
                end = sum(len(line) for line in lines[:doc.end_lineno - 1]) + doc.end_col_offset
                facts.append(_make_fact(path, source, "behavior_contract", node.name, start, end,
                                        scope_name(node)))
        if isinstance(node, algorithm_nodes):
            lines = source.splitlines(keepends=True)
            start = sum(len(line) for line in lines[:node.lineno - 1]) + node.col_offset
            end = sum(len(line) for line in lines[:node.end_lineno - 1]) + node.end_col_offset
            ancestor = parents.get(node)
            owner = None
            in_callable_body = True
            child = node
            while ancestor is not None:
                if isinstance(ancestor, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    body = ancestor.body
                    body_nodes = body if isinstance(body, list) else [body]
                    in_callable_body = child in body_nodes
                    if in_callable_body:
                        owner = scope_name(ancestor, include_node=True) if hasattr(ancestor, "name") else "<lambda>"
                    break
                child = ancestor
                ancestor = parents.get(ancestor)
            if in_callable_body:
                facts.append(_make_fact(path, source, "algorithm_step", type(node).__name__, start, end, owner))
                if owner and isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for target in targets:
                        for binding in binding_nodes(target):
                            binding_start, binding_end = byte_span(binding)
                            facts.append(_make_fact(path, source, "local_binding", binding.id,
                                                    binding_start, binding_end, owner))
                elif owner and isinstance(node, ast.NamedExpr):
                    for binding in binding_nodes(node.target):
                        binding_start, binding_end = byte_span(binding)
                        facts.append(_make_fact(path, source, "local_binding", binding.id,
                                                binding_start, binding_end, owner))
                elif owner and isinstance(node, (ast.For, ast.AsyncFor)):
                    for binding in binding_nodes(node.target):
                        binding_start, binding_end = byte_span(binding)
                        facts.append(_make_fact(path, source, "local_binding", binding.id,
                                                binding_start, binding_end, owner))
                elif owner and isinstance(node, (ast.With, ast.AsyncWith)):
                    for item in node.items:
                        if item.optional_vars:
                            for binding in binding_nodes(item.optional_vars):
                                binding_start, binding_end = byte_span(binding)
                                facts.append(_make_fact(path, source, "local_binding", binding.id,
                                                        binding_start, binding_end, owner))
                elif owner and isinstance(node, ast.Try):
                    for handler in node.handlers:
                        if handler.name:
                            handler_start, handler_end = byte_span(handler)
                            colon = source.find(b":", handler_start, handler_end)
                            alias = source.find(b"as", handler_start, colon)
                            name_bytes = handler.name.encode("utf-8")
                            binding_start = source.find(name_bytes, alias + 2, colon)
                            if colon >= 0 and alias >= 0 and binding_start >= 0:
                                facts.append(_make_fact(path, source, "local_binding", handler.name,
                                                        binding_start, binding_start + len(name_bytes), owner))
    return facts


def _construct_parser_version(language: str) -> tuple[str, str]:
    if language == "python":
        return "python-ast", platform.python_version()
    try:
        version = importlib.metadata.version("tree-sitter-rust")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    return "tree-sitter-rust", version


def _source_construct(path: str, source: bytes, language: str, syntax_kind: str,
                      name: str, start: int, end: int, parent_id: str | None,
                      parser_id: str, parser_version: str, *, opaque: bool = False,
                      declared_type: str | None = None) -> SourceConstruct:
    source_digest = hashlib.sha256(source).hexdigest()
    key = f"{language}:{path}:{syntax_kind}:{start}:{end}"
    construct_id = hashlib.sha256(key.encode("utf-8")).hexdigest()
    source_key = hashlib.sha256(f"{path}\0{syntax_kind}\0{start}".encode("utf-8")).hexdigest()
    return SourceConstruct(construct_id, source_key, language, syntax_kind, name, path,
                          start, end, parent_id, source_digest, parser_id, parser_version,
                          opaque, source[start:end].decode("utf-8", errors="replace"), declared_type)


def _python_source_constructs(path: str, source: bytes, tree: ast.AST) -> tuple[SourceConstruct, ...]:
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    enum_definitions = {node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
                        and any((base.id if isinstance(base, ast.Name) else
                                 base.attr if isinstance(base, ast.Attribute) else "")
                                in {"Enum", "IntEnum", "StrEnum", "Flag", "IntFlag"}
                                for base in node.bases)}
    parser_id, parser_version = _construct_parser_version("python")
    lines = source.splitlines(keepends=True)

    def byte_span(node) -> tuple[int, int]:
        return (sum(len(line) for line in lines[:node.lineno - 1]) + node.col_offset,
                sum(len(line) for line in lines[:node.end_lineno - 1]) + node.end_col_offset)

    candidates: list[tuple[ast.AST | None, str, str, int, int, bool, str | None]] = [
        (None, "module", Path(path).name, 0, len(source), False, None)]
    for node in ast.walk(tree):
        kind = None
        name = getattr(node, "name", type(node).__name__)
        if isinstance(node, ast.ClassDef):
            kind = "enum_declaration" if node in enum_definitions else "class_declaration"
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "function_declaration"
        elif isinstance(node, ast.Lambda):
            kind = "lambda_expression"
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(parents.get(node), ast.ClassDef):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, (ast.Tuple, ast.List)):
                    target_nodes = [item for item in target.elts if isinstance(item, ast.Name)]
                else:
                    target_nodes = [target]
                for target_node in target_nodes:
                    field_name = (target_node.id if isinstance(target_node, ast.Name) else
                                  target_node.attr if isinstance(target_node, ast.Attribute) else
                                  type(target_node).__name__)
                    if parents.get(node) in enum_definitions:
                        start, end = byte_span(node)
                        candidates.append((node, "enum_variant", field_name, start, end, False, None))
                    else:
                        start, end = byte_span(target_node)
                        annotation = ast.unparse(node.annotation) if isinstance(node, ast.AnnAssign) else None
                        candidates.append((target_node, "field_declaration", field_name, start, end,
                                           False, annotation))
            continue
        if kind:
            start, end = byte_span(node)
            candidates.append((node, kind, name, start, end, False, None))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for decorator in node.decorator_list:
                start, end = byte_span(decorator)
                candidates.append((decorator, "decorator_application", ast.unparse(decorator), start, end,
                                   False, None))
            for parameter in getattr(node, "type_params", ()):
                start, end = byte_span(parameter)
                candidates.append((parameter, "generic_parameter", getattr(parameter, "name", type(parameter).__name__),
                                   start, end, False, None))

    parent_lookup: dict[ast.AST, list[tuple[ast.AST | None, str, str, int, int, bool, str | None]]] = {}
    for candidate in candidates:
        node = candidate[0]
        if node is not None:
            parent_lookup.setdefault(node, []).append(candidate)
    construct_ids = {(candidate[0], candidate[1]): _source_construct(
        path, source, "python", candidate[1], candidate[2], candidate[3], candidate[4], None,
        parser_id, parser_version, opaque=candidate[5], declared_type=candidate[6]).construct_id
        for candidate in candidates}
    constructs = []
    for node, kind, name, start, end, opaque, declared_type in candidates:
        ancestor = parents.get(node) if node is not None else None
        parent_id = construct_ids[(None, "module")]
        while ancestor is not None:
            matches = parent_lookup.get(ancestor, [])
            if matches:
                parent_candidate = matches[0]
                parent_id = construct_ids[(ancestor, parent_candidate[1])]
                break
            ancestor = parents.get(ancestor)
        if node is None:
            parent_id = None
        constructs.append(_source_construct(path, source, "python", kind, name, start, end,
                                            parent_id, parser_id, parser_version, opaque=opaque,
                                            declared_type=declared_type))
    return tuple(constructs)


def _rust_source_constructs(path: str, source: bytes, root) -> tuple[SourceConstruct, ...]:
    parser_id, parser_version = _construct_parser_version("rust")
    syntax_kinds = {"struct_item": "struct_declaration", "enum_item": "enum_declaration",
                    "trait_item": "trait_declaration", "function_item": "function_declaration",
                    "type_item": "type_alias_declaration", "mod_item": "module_declaration",
                    "const_item": "constant_declaration", "static_item": "static_declaration",
                    "use_declaration": "import_declaration", "impl_item": "implementation_block",
                    "field_declaration": "field_declaration", "enum_variant": "enum_variant",
                    "macro_definition": "macro_definition", "macro_invocation": "macro_invocation",
                    "attribute_item": "attribute_application", "type_parameters": "generic_parameter_list",
                    "type_parameter": "generic_parameter", "closure_expression": "closure_expression"}
    raw: list[tuple[object, str, str, int, int, bool, str | None]] = []
    for node in _walk_syntax(root):
        if node.type in syntax_kinds:
            name_node = node.child_by_field_name("name")
            name = (source[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                    if name_node is not None else node.type)
            type_node = node.child_by_field_name("type") if node.type == "field_declaration" else None
            declared_type = (source[type_node.start_byte:type_node.end_byte].decode("utf-8", errors="replace")
                             if type_node is not None else None)
            raw.append((node, syntax_kinds[node.type], name, node.start_byte, node.end_byte, False, declared_type))
        elif node.type == "ERROR" or node.is_missing:
            raw.append((node, "opaque_error", node.type, node.start_byte, node.end_byte, True, None))

    by_node = {item[0]: item for item in raw}
    ids = {item[0]: _source_construct(path, source, "rust", item[1], item[2], item[3], item[4],
                                        None, parser_id, parser_version, opaque=item[5],
                                        declared_type=item[6]).construct_id
           for item in raw}
    constructs = [_source_construct(path, source, "rust", "module", path, 0, len(source), None,
                                    parser_id, parser_version)]
    module_id = constructs[0].construct_id
    for node, kind, name, start, end, opaque, declared_type in raw:
        parent = node.parent
        parent_id = module_id
        while parent is not None:
            if parent in by_node:
                parent_id = ids[parent]
                break
            parent = parent.parent
        constructs.append(_source_construct(path, source, "rust", kind, name, start, end,
                                            parent_id, parser_id, parser_version, opaque=opaque,
                                            declared_type=declared_type))
    return tuple(constructs)


def _walk_syntax(root):
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(reversed(node.children))


def _rust_facts(path: str, source: bytes, root) -> tuple[list[Fact], int, bool]:
    facts: list[Fact] = []
    syntax_nodes = 0
    parse_complete = True
    item_kinds = {
        "struct_item": "struct", "enum_item": "enum", "trait_item": "trait",
        "function_item": "function", "type_item": "type_alias", "mod_item": "module",
        "const_item": "constant_item", "static_item": "static_item", "use_declaration": "import",
        "impl_item": "impl",
    }
    algorithm_nodes = {"if_expression", "match_expression", "loop_expression", "while_expression",
                       "for_expression", "call_expression", "macro_invocation", "return_expression",
                       "break_expression", "assignment_expression", "binary_expression", "await_expression",
                       "let_declaration"}

    def binding_nodes(pattern) -> list:
        if pattern.type == "identifier":
            if source[pattern.start_byte:pattern.end_byte] == b"_":
                return []
            return [pattern]
        if pattern.type in {"tuple_pattern", "slice_pattern"}:
            return [node for child in pattern.named_children for node in binding_nodes(child)]
        if pattern.type in {"tuple_struct_pattern", "struct_pattern"}:
            return [node for child in pattern.named_children[1:] for node in binding_nodes(child)]
        if pattern.type == "field_pattern":
            nodes = []
            for child in pattern.named_children:
                if child.type == "shorthand_field_identifier":
                    nodes.append(child)
                elif child.type != "field_identifier":
                    nodes.extend(binding_nodes(child))
            return nodes
        if pattern.type == "or_pattern":
            return binding_nodes(pattern.named_children[0]) if pattern.named_children else []
        if pattern.type in {"mut_pattern", "reference_pattern", "captured_pattern"}:
            return [node for child in pattern.named_children for node in binding_nodes(child)]
        return []

    def walk(node, owner_name: str | None = None) -> None:
        nonlocal syntax_nodes, parse_complete
        syntax_nodes += 1
        if node.type == "ERROR" or node.is_missing:
            parse_complete = False
        if node.type in item_kinds:
            name_node = node.child_by_field_name("name")
            name = source[name_node.start_byte:name_node.end_byte].decode() if name_node else node.type
            facts.append(_make_fact(path, source, item_kinds[node.type], name, node.start_byte, node.end_byte,
                                    owner_name if node.type == "function_item" else None))
            if node.type in {"struct_item", "enum_item", "trait_item"}:
                owner_name = name
            elif node.type == "impl_item":
                target = node.child_by_field_name("type")
                if target:
                    owner_name = source[target.start_byte:target.end_byte].decode()
        if node.type == "let_declaration":
            pattern = node.child_by_field_name("pattern")
            if pattern:
                for binding in binding_nodes(pattern):
                    name = source[binding.start_byte:binding.end_byte].decode()
                    facts.append(_make_fact(path, source, "local_binding", name,
                                            binding.start_byte, binding.end_byte, owner_name))
        elif node.type == "field_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = source[name_node.start_byte:name_node.end_byte].decode()
                facts.append(_make_fact(path, source, "field", name, node.start_byte, node.end_byte, owner_name))
        elif node.type == "enum_variant":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = source[name_node.start_byte:name_node.end_byte].decode()
                facts.append(_make_fact(path, source, "variant", name, node.start_byte, node.end_byte, owner_name))
        if node.type in algorithm_nodes:
            facts.append(_make_fact(path, source, "algorithm_step", node.type,
                                    node.start_byte, node.end_byte, owner_name))
        pending_doc: tuple[int, int] | None = None
        for child in node.children:
            if child.type == "line_comment":
                comment = source[child.start_byte:child.end_byte]
                if comment.startswith(b"///"):
                    pending_doc = (child.start_byte, child.end_byte)
                elif not comment.startswith(b"//!"):
                    pending_doc = None
            elif child.type == "function_item" and pending_doc:
                name_node = child.child_by_field_name("name")
                if name_node:
                    function_name = source[name_node.start_byte:name_node.end_byte].decode()
                    facts.append(_make_fact(path, source, "behavior_contract", function_name,
                                            pending_doc[0], pending_doc[1], owner_name))
                pending_doc = None
            elif child.is_named and child.type not in {"attribute_item", "line_comment"}:
                pending_doc = None
            child_owner = owner_name
            if node.type == "function_item":
                function_node = node.child_by_field_name("name")
                if function_node:
                    function_name = source[function_node.start_byte:function_node.end_byte].decode()
                    child_owner = f"{owner_name}.{function_name}" if owner_name else function_name
            if node.type == "impl_item" and child.type == "type_identifier":
                child_owner = source[child.start_byte:child.end_byte].decode()
            walk(child, child_owner)

    walk(root)
    return facts, syntax_nodes, parse_complete


def parse_source(path: str, source: bytes, language: str) -> ParseResult:
    """Parse one source file and emit stable, evidence-backed declaration facts."""
    diagnostics: list[str] = []
    if language == "python":
        try:
            tree = ast.parse(source, filename=path)
            facts = _python_facts(path, source, tree)
            constructs = _python_source_constructs(path, source, tree)
            syntax_nodes = sum(1 for _ in ast.walk(tree))
            complete = True
        except (SyntaxError, UnicodeDecodeError) as error:
            facts, syntax_nodes, complete = [], 0, False
            parser_id, parser_version = _construct_parser_version("python")
            constructs = (_source_construct(path, source, "python", "opaque_file", Path(path).name,
                                            0, len(source), None, parser_id, parser_version, opaque=True),)
            diagnostics.append(f"PARSE_ERROR:{type(error).__name__}:{getattr(error, 'lineno', '')}")
    elif language == "rust":
        from tree_sitter import Language, Parser
        import tree_sitter_rust
        parser = Parser(Language(tree_sitter_rust.language()))
        tree = parser.parse(source)
        facts, syntax_nodes, complete = _rust_facts(path, source, tree.root_node)
        constructs = _rust_source_constructs(path, source, tree.root_node)
        if not complete:
            diagnostics.append("PARSE_ERROR:tree-sitter-error-node")
    else:
        raise ValueError(f"unsupported language: {language}")
    return ParseResult(path, language, hashlib.sha256(source).hexdigest(), tuple(facts),
                       syntax_nodes, complete, tuple(diagnostics), constructs)


def scan_project(root: Path, source_languages: set[str] | None = None,
                 inventory: tuple | None = None) -> ProjectScan:
    """Parse selected regular source languages and inventory all project paths."""
    root = root.resolve(strict=True)
    parsed: list[ParseResult] = []
    inventory = tuple(inventory if inventory is not None
                       else inventory_tree(root, excluded_dirs=frozenset({".git"})))
    for entry in inventory:
        relative = entry.path
        path = root / relative
        if entry.kind != "file" or path.suffix not in {".py", ".rs"}:
            continue
        language = "python" if path.suffix == ".py" else "rust"
        if source_languages is not None and language not in source_languages:
            continue
        try:
            parsed.append(parse_source(relative, path.read_bytes(), language))
        except OSError as error:
            parsed.append(ParseResult(relative, language, "", (), 0, False,
                                      (f"READ_ERROR:{type(error).__name__}",)))
    project_facts: list[Fact] = []
    for manifest_name, ecosystem in (("pyproject.toml", "python"), ("Cargo.toml", "rust")):
        manifest = root / manifest_name
        if not manifest.is_file() or manifest.is_symlink():
            continue
        source = manifest.read_bytes()
        document = tomllib.loads(source.decode("utf-8"))
        table = document.get("project", {}) if ecosystem == "python" else document.get("package", {})
        key = "name"
        if isinstance(table.get(key), str):
            match = re.search(rb"(?m)^\s*name\s*=\s*(['\"])(.*?)\1\s*(?:#.*)?$", source)
            if match:
                project_facts.append(_make_fact(manifest_name, source, "project_name", table[key], match.start(), match.end()))
        if ecosystem == "rust" and table.get("name"):
            project_facts.append(_make_fact(manifest_name, source, "language_declared", "Rust", 0, len(source)))
        elif ecosystem == "python" and (table.get("requires-python") or any(
                isinstance(value, str) and value.startswith("Programming Language :: Python ::")
                for value in table.get("classifiers", []))):
            match = re.search(rb"(?m)^\s*(?:requires-python|classifiers)\s*=.*$", source)
            if match:
                project_facts.append(_make_fact(manifest_name, source, "language_declared", "Python", match.start(), match.end()))
    parsed = [replace(result,
                      facts=tuple(_namespace_fact(fact, root) for fact in result.facts),
                      constructs=tuple(_namespace_construct(item, root) for item in result.constructs))
              for result in parsed]
    project_facts = [_namespace_fact(fact, root) for fact in project_facts]
    return ProjectScan(str(root), len(parsed), sum(result.parse_complete for result in parsed),
                       sum(len(result.facts) for result in parsed),
                       sum(result.syntax_node_count for result in parsed), tuple(parsed),
                       source_fingerprint(root), tuple(project_facts), inventory)
