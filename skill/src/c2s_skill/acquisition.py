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

from tree_sitter import Language, Parser
import tree_sitter_python
import tree_sitter_rust
from .inventory import InventoryEntry, inventory_tree


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
class ParseResult:
    path: str
    language: str
    source_sha256: str
    facts: tuple[Fact, ...]
    syntax_node_count: int
    parse_complete: bool
    diagnostics: tuple[str, ...]


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


def source_fingerprint(root: Path) -> str:
    """Hash the complete visible project tree without following symlinks."""
    root = root.resolve(strict=True)
    digest = hashlib.sha256()
    for entry in inventory_tree(root, excluded_dirs=frozenset({".git"})):
        path = root / entry.path
        digest.update(entry.path.encode("utf-8"))
        digest.update(b"\0" + entry.kind.encode("ascii") + b"\0" + entry.state.encode("ascii") + b"\0")
        if entry.kind == "file":
            try:
                digest.update(hashlib.sha256(path.read_bytes()).hexdigest().encode("ascii"))
            except OSError as error:
                digest.update(f"READ_ERROR:{type(error).__name__}".encode("ascii"))
        elif entry.kind == "symlink":
            try:
                digest.update(os.readlink(path).encode("utf-8", errors="surrogateescape"))
            except OSError as error:
                digest.update(f"READLINK_ERROR:{type(error).__name__}".encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


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
    profile = {"analyzer": "c2s-semantic-facts/0.6.1", "python": platform.python_version(),
               "platform": platform.platform(), "parsers": dependencies, "cargo": cargo_version}
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
    elif kind == "algorithm_step" and owner:
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
    return facts


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
            syntax_nodes = sum(1 for _ in ast.walk(tree))
            complete = True
        except (SyntaxError, UnicodeDecodeError) as error:
            facts, syntax_nodes, complete = [], 0, False
            diagnostics.append(f"PARSE_ERROR:{type(error).__name__}:{getattr(error, 'lineno', '')}")
    elif language == "rust":
        parser = Parser(Language(tree_sitter_rust.language()))
        tree = parser.parse(source)
        facts, syntax_nodes, complete = _rust_facts(path, source, tree.root_node)
        if not complete:
            diagnostics.append("PARSE_ERROR:tree-sitter-error-node")
    else:
        raise ValueError(f"unsupported language: {language}")
    return ParseResult(path, language, hashlib.sha256(source).hexdigest(), tuple(facts),
                       syntax_nodes, complete, tuple(diagnostics))


def scan_project(root: Path) -> ProjectScan:
    """Parse every regular .py/.rs file below root, including tests and ignored paths."""
    root = root.resolve(strict=True)
    parsed: list[ParseResult] = []
    inventory = tuple(inventory_tree(root, excluded_dirs=frozenset({".git"})))
    for entry in inventory:
        relative = entry.path
        path = root / relative
        if entry.kind != "file" or path.suffix not in {".py", ".rs"}:
            continue
        language = "python" if path.suffix == ".py" else "rust"
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
    parsed = [replace(result, facts=tuple(_namespace_fact(fact, root) for fact in result.facts))
              for result in parsed]
    project_facts = [_namespace_fact(fact, root) for fact in project_facts]
    return ProjectScan(str(root), len(parsed), sum(result.parse_complete for result in parsed),
                       sum(len(result.facts) for result in parsed),
                       sum(result.syntax_node_count for result in parsed), tuple(parsed),
                       source_fingerprint(root), tuple(project_facts), inventory)
