"""Evidence-gated semantic acquisition tool selection."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from itertools import combinations
import json
import os
from pathlib import Path
import platform
import importlib.metadata
import re
import subprocess
import shutil
from typing import Any, Iterable

_PARSERS = {"native_manifest", "source_python", "source_rust", "cargo_metadata", "code_review_graph", "codegraph"}


@dataclass(frozen=True, slots=True)
class ToolSelection:
    tools: tuple[str, ...]
    uncovered: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.uncovered


@dataclass(frozen=True, slots=True)
class ToolRun:
    scan: Any
    workspace_facts: tuple[Any, ...]
    workspace_gap: str | None
    tools: tuple[str, ...]

    @property
    def source_constructs(self) -> tuple[Any, ...]:
        """Return normalized source constructs emitted by the selected parsers."""
        return tuple(construct for parsed_file in getattr(self.scan, "files", ())
                     for construct in getattr(parsed_file, "constructs", ()))


def load_tool_matrix(path: Path | None = None) -> dict[str, Any]:
    """Load the checked-in registry of tools, parser contracts and evidence."""
    matrix_path = path or Path(__file__).resolve().parents[2] / "contracts" / "tool-capabilities.json"
    value = json.loads(matrix_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != 1 or not isinstance(value.get("tools"), list):
        raise ValueError("tool capability matrix has an unsupported shape")
    return value


def validate_matrix_evidence(matrix: dict[str, Any], repo_root: Path | None = None) -> None:
    """Validate lit entries against checkout evidence during CI/release checks.

    This is deliberately separate from runtime selection so installed wheels do
    not need to ship the source repository's tests and research documents.
    """
    root = (repo_root or Path(__file__).resolve().parents[3]).resolve()
    for tool in matrix.get("tools", []):
        if not isinstance(tool, dict) or tool.get("status") != "lit":
            continue
        validation = tool.get("validation")
        if not isinstance(validation, dict):
            raise ValueError(f"lit tool {tool.get('id')!r} has no validation evidence")
        for category in ("tests", "evidence"):
            references = validation.get(category)
            if not isinstance(references, list) or not references:
                raise ValueError(f"lit tool {tool.get('id')!r} has no {category} references")
            for item in references:
                path = Path(item) if isinstance(item, str) else Path(".")
                if (not isinstance(item, str) or path.is_absolute() or ".." in path.parts
                        or not (root / path).is_file()):
                    raise ValueError(f"lit tool {tool.get('id')!r} has invalid {category} reference: {item!r}")


def detect_available_tools(matrix: dict[str, Any]) -> set[str]:
    """Detect tool executables and parser modules without installing anything."""
    available = set()
    for tool in matrix.get("tools", []):
        if not isinstance(tool, dict) or not isinstance(tool.get("id"), str):
            continue
        runtime = tool.get("runtime", {})
        kind, name = runtime.get("kind"), runtime.get("name")
        if kind == "builtin-python" and isinstance(name, str):
            expected_python = runtime.get("python_version")
            found = (importlib.util.find_spec(name) is not None
                    and (expected_python is None or platform.python_version() == expected_python))
        elif kind in {"python-module", "optional-python-module"} and isinstance(name, str):
            try:
                found = importlib.util.find_spec(name) is not None
            except (ImportError, ModuleNotFoundError, ValueError):
                found = False
        elif kind == "executable" and isinstance(name, str):
            configured = os.environ.get(name.upper())
            executable = (configured if configured else
                          (None if name.upper() in os.environ else shutil.which(name)))
            found = False
            if executable:
                try:
                    result = subprocess.run([executable, "--version"], capture_output=True,
                                            text=True, timeout=3, check=True)
                    expected = runtime.get("version")
                    found = expected is None or bool(re.search(
                        rf"(?<![\w.]){re.escape(str(expected))}(?![\w.])",
                        result.stdout + result.stderr))
                except (subprocess.SubprocessError, OSError):
                    found = False
        else:
            found = False
        packages = runtime.get("packages", {})
        if found and isinstance(packages, dict):
            for distribution, expected_version in packages.items():
                try:
                    if importlib.metadata.version(distribution) != expected_version:
                        found = False
                        break
                except importlib.metadata.PackageNotFoundError:
                    found = False
                    break
        if found:
            available.add(tool["id"])
    return available


def describe_tools_used(tool_ids: Iterable[str], matrix: dict[str, Any]) -> list[dict[str, str]]:
    """Return observed versions for selected tools; never substitute a declared version."""
    by_id = {item["id"]: item for item in matrix.get("tools", []) if isinstance(item, dict)}
    records = []
    for tool_id in sorted(set(tool_ids)):
        tool = by_id.get(tool_id, {})
        runtime = tool.get("runtime", {})
        kind, name = runtime.get("kind"), runtime.get("name")
        version = None
        try:
            if kind == "builtin-python":
                version = platform.python_version()
            elif kind in {"python-module", "optional-python-module"}:
                packages = runtime.get("packages", {})
                if packages:
                    version = ", ".join(f"{package}=={importlib.metadata.version(package)}"
                                          for package in sorted(packages))
                elif name:
                    version = importlib.metadata.version(name.replace("_", "-"))
            elif kind == "executable" and name:
                configured = os.environ.get(name.upper())
                executable = configured if configured else shutil.which(name)
                if executable:
                    result = subprocess.run([executable, "--version"], capture_output=True,
                                            text=True, timeout=3, check=True)
                    version = (result.stdout or result.stderr).strip().splitlines()[0]
        except (importlib.metadata.PackageNotFoundError, subprocess.SubprocessError, OSError, IndexError):
            version = None
        records.append({"name": tool_id, "version": version or "unknown",
                        "status": "verified" if version else "unknown"})
    return records


def host_environment(target: str | None = None) -> dict[str, str]:
    return {"host_os": platform.system().lower(), "target": target or ""}


def needs_for_query(selectors: Iterable[str], source_languages: set[str],
                    has_cargo_manifest: bool) -> tuple[str, ...]:
    """Translate public selectors into matrix capability requirements."""
    needs: set[str] = set()
    for selector in selectors:
        if selector == "project":
            needs.add("project.manifest")
        elif selector == "workspace-members":
            if has_cargo_manifest:
                needs.add("workspace.rust.members")
        elif selector == "all-supported-facts":
            needs.add("project.manifest")
            if has_cargo_manifest:
                needs.add("workspace.rust.members")
            fact_groups = {"declarations", "definitions", "local_bindings", "algorithm_structure"}
            for language in source_languages:
                needs.update(f"source.{language}.{group}" for group in fact_groups)
        elif selector.startswith(("function:", "members:")):
            for language in source_languages:
                needs.add(f"source.{language}.definitions")
                needs.add(f"source.{language}.algorithm_structure")
        elif selector in {"classes", "functions", "all-declarations", "definitions", "imports", "constants"}:
            for language in source_languages:
                needs.add(f"source.{language}.declarations")
                if selector in {"definitions", "all-declarations"}:
                    needs.add(f"source.{language}.definitions")
        elif selector in {"local-bindings"}:
            for language in source_languages:
                needs.add(f"source.{language}.local_bindings")
        elif selector in {"behavior-contracts", "algorithm-structure"}:
            for language in source_languages:
                needs.add(f"source.{language}.algorithm_structure")
    return tuple(sorted(needs))


def execute_native_selection(root: Path, inventory: tuple[Any, ...],
                             selection: ToolSelection, matrix: dict[str, Any], *,
                             scan_runner=None, cargo_runner=None) -> ToolRun:
    """Run selected in-process parser adapters and selected Cargo metadata tool."""
    tools = {item["id"]: item for item in matrix["tools"]}
    parser_languages = {tools[item]["parser"].removeprefix("source_")
                        for item in selection.tools
                        if tools[item].get("parser") in {"source_python", "source_rust"}}
    from .acquisition import cargo_workspace_facts, scan_project
    scan = (scan_runner or scan_project)(root, source_languages=parser_languages, inventory=inventory)
    workspace_facts: list[Any] = []
    workspace_gap = None
    if "cargo-metadata" in selection.tools and (root / "Cargo.toml").is_file():
        workspace_facts, workspace_gap = (cargo_runner or cargo_workspace_facts)(root)
    return ToolRun(scan, tuple(workspace_facts), workspace_gap, selection.tools)


def parse_selected_tool_output(selection: ToolSelection, tool_id: str, response: dict,
                               project_root: Path, tool_version: str | None,
                               matrix: dict[str, Any] | None = None):
    """Dispatch structured output to the parser registered for a selected tool."""
    if tool_id not in selection.tools:
        raise ValueError(f"tool {tool_id!r} was not selected for this semantic request")
    registry = matrix or load_tool_matrix()
    tool = next((item for item in registry["tools"] if item.get("id") == tool_id), None)
    if tool is None:
        raise ValueError(f"selected tool {tool_id!r} is missing from the capability matrix")
    if tool.get("parser") == "codegraph":
        from .codegraph_adapter import parse_codegraph_response
        return parse_codegraph_response({"toolVersion": tool_version,
            "payload": response.get("payload", response)}, project_root,
            response.get("queryKind", "query"))
    if tool.get("parser") == "code_review_graph":
        from .graph_tool_adapter import parse_code_review_graph_response
        return parse_code_review_graph_response(response, project_root, tool_version)
    raise ValueError(f"tool {tool_id!r} does not have a structured-output parser")


def _is_lit(tool: Any, available: set[str], environment: dict[str, str]) -> bool:
    if not isinstance(tool, dict) or not isinstance(tool.get("id"), str):
        return False
    validation = tool.get("validation")
    if (tool["id"] not in available or tool.get("status") != "lit"
            or tool.get("parser") not in _PARSERS
            or not isinstance(validation, dict)
            or not validation.get("tests") or not validation.get("evidence")):
        return False
    for category in ("tests", "evidence"):
        references = validation.get(category)
        if (not isinstance(references, list) or not references
                or any(not isinstance(item, str) or not item for item in references)):
            return False
    host = tool.get("host_os", "any")
    if host != "any" and host != environment.get("host_os"):
        return False
    target = tool.get("target")
    if target is not None and target != environment.get("target"):
        return False
    return True


def select_tools(needs: Iterable[str], matrix: dict[str, Any], *,
                 available_tools: set[str] | None = None,
                 environment: dict[str, str] | None = None) -> ToolSelection:
    """Choose the smallest deterministic lit tool set covering semantic needs.

    Candidate or unavailable tools do not contribute coverage. Equal-size sets
    are resolved lexicographically, making planning stable between runs.
    """
    requested = tuple(sorted(set(needs)))
    if not all(isinstance(item, str) and item for item in requested):
        raise ValueError("semantic needs must be non-empty strings")
    tools = matrix.get("tools") if isinstance(matrix, dict) else None
    if not isinstance(tools, list):
        raise ValueError("tool capability matrix must contain a tools array")
    available = available_tools if available_tools is not None else {
        tool.get("id") for tool in tools if isinstance(tool, dict) and isinstance(tool.get("id"), str)}
    env = environment or {}
    eligible = []
    seen_ids = set()
    for tool in tools:
        if not isinstance(tool, dict) or not isinstance(tool.get("id"), str):
            raise ValueError("each tool entry must have a string id")
        if tool["id"] in seen_ids:
            raise ValueError(f"duplicate tool id: {tool['id']}")
        seen_ids.add(tool["id"])
        provides = tool.get("provides", [])
        if not isinstance(provides, list) or not all(isinstance(x, str) and x for x in provides):
            raise ValueError(f"tool {tool['id']} has invalid provides")
        if _is_lit(tool, available, env):
            eligible.append((tool["id"], frozenset(provides)))

    if not requested:
        return ToolSelection((), ())
    requested_set = frozenset(requested)
    best: tuple[str, ...] | None = None
    best_coverage = frozenset()
    # Capability matrices are deliberately small. Enumerating by cardinality
    # guarantees a minimum-cardinality combination rather than greedy overpick.
    eligible.sort(key=lambda item: item[0])
    for count in range(1, len(eligible) + 1):
        for group in combinations(eligible, count):
            covered = frozenset().union(*(capabilities for _, capabilities in group))
            if requested_set <= covered:
                best = tuple(tool_id for tool_id, _ in group)
                break
            if (len(covered & requested_set) > len(best_coverage & requested_set)
                    or (len(covered & requested_set) == len(best_coverage & requested_set)
                        and tuple(tool_id for tool_id, _ in group) < (best or ()) )):
                best = tuple(tool_id for tool_id, _ in group)
                best_coverage = covered
        if best is not None:
            # A full cover is globally minimum at this cardinality. Partial
            # covers keep the best available tools running while exposing gaps.
            if requested_set <= frozenset().union(*(caps for tool_id, caps in eligible
                                                     if tool_id in best)):
                break
    covered = frozenset().union(*(caps for tool_id, caps in eligible if tool_id in best)) if best else frozenset()
    uncovered = tuple(sorted(requested_set - covered))
    return ToolSelection(best or (), uncovered)
