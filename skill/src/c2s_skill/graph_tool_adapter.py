"""Adapters for structured output from optional project-graph analyzers."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any


@dataclass(frozen=True, slots=True)
class GraphToolDiagnostic:
    code: str
    message: str
    path: str | None = None


@dataclass(frozen=True, slots=True)
class GraphCallSite:
    caller_name: str
    caller_path: str
    caller_line: int
    callee_name: str
    callee_path: str | None
    callee_qualified_name: str | None
    resolution: str


@dataclass(frozen=True, slots=True)
class GraphQueryFacts:
    tool: str
    pattern: str
    target: str
    call_sites: tuple[GraphCallSite, ...]
    result_count: int | None
    omitted_count: int | None
    complete: bool
    diagnostics: tuple[GraphToolDiagnostic, ...]
    artifact_content: str
    artifact_sha256: str
    tool_version: str | None


def _project_path(value: Any, root: Path) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    candidate = Path(value)
    if candidate.is_absolute():
        try:
            candidate = candidate.resolve(strict=False).relative_to(root)
        except (OSError, ValueError):
            return None
    if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
        return None
    cursor = root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            return None
    try:
        resolved = cursor.resolve(strict=True)
        if resolved != root and root not in resolved.parents:
            return None
        if not resolved.is_file():
            return None
    except OSError:
        return None
    return PurePosixPath(*candidate.parts).as_posix()


def parse_code_review_graph_response(response: dict[str, Any], project_root: Path,
                                     tool_version: str | None = None) -> GraphQueryFacts:
    """Normalize Code Review Graph ``query_graph`` JSON without inflating coverage.

    Only callers/callees queries carry source call-site rows. The API's count and
    omitted fields are mandatory here because a capped list cannot prove that
    the requested relationship set is complete.
    """
    root = Path(project_root).resolve(strict=True)
    diagnostics: list[GraphToolDiagnostic] = []
    if not isinstance(response, dict):
        response = {}
    status = response.get("status")
    pattern = response.get("pattern")
    target = response.get("target")
    raw_results = response.get("results")
    result_count = response.get("result_count")
    omitted_count = response.get("results_omitted")
    if status != "ok":
        diagnostics.append(GraphToolDiagnostic("GRAPH_TOOL_FAILED", str(response.get("error", status))))
    if pattern not in {"callers_of", "callees_of"} or not isinstance(target, str) or not target:
        diagnostics.append(GraphToolDiagnostic("GRAPH_QUERY_UNSUPPORTED", "Expected a callers_of or callees_of query with a target."))
    if not isinstance(raw_results, list):
        diagnostics.append(GraphToolDiagnostic("GRAPH_RESULTS_INVALID", "Graph query results must be an array."))
        raw_results = []
    if type(result_count) is not int or result_count < 0 or type(omitted_count) is not int or omitted_count < 0:
        diagnostics.append(GraphToolDiagnostic("GRAPH_COUNTS_UNAVAILABLE", "Graph result and omission counts must be non-negative integers."))
        result_count = None
        omitted_count = None
    elif result_count != len(raw_results) + omitted_count:
        diagnostics.append(GraphToolDiagnostic("GRAPH_COUNT_MISMATCH", "Reported result count does not equal returned rows plus omitted rows."))
    if omitted_count:
        diagnostics.append(GraphToolDiagnostic("GRAPH_RESULTS_TRUNCATED", f"Graph query omitted {omitted_count} result rows."))

    call_sites: list[GraphCallSite] = []
    target_source_path = None
    if pattern == "callees_of" and isinstance(target, str) and "::" in target:
        target_source_path = _project_path(target.split("::", 1)[0], root)
    if pattern in {"callers_of", "callees_of"} and isinstance(target, str):
        for index, row in enumerate(raw_results):
            if not isinstance(row, dict):
                diagnostics.append(GraphToolDiagnostic("GRAPH_ROW_INVALID", f"Result row {index} is not an object."))
                continue
            result_path = _project_path(row.get("file_path"), root)
            call_site = row.get("call_site")
            if not isinstance(call_site, dict) or type(call_site.get("line")) is not int or call_site["line"] < 1:
                diagnostics.append(GraphToolDiagnostic("GRAPH_CALLSITE_UNLOCATED", f"Result row {index} has no valid one-based call-site line.", result_path))
                continue
            default_call_path = target_source_path if pattern == "callees_of" else result_path
            call_path = _project_path(call_site.get("file", default_call_path), root)
            if call_path is None:
                diagnostics.append(GraphToolDiagnostic("GRAPH_PATH_OUTSIDE_ROOT", f"Result row {index} has an unsafe call-site path."))
                continue
            if pattern == "callers_of" and result_path is None:
                diagnostics.append(GraphToolDiagnostic("GRAPH_PATH_OUTSIDE_ROOT", f"Result row {index} has no safe project-relative source path."))
                continue
            name = row.get("name")
            if not isinstance(name, str) or not name:
                diagnostics.append(GraphToolDiagnostic("GRAPH_SYMBOL_UNNAMED", f"Result row {index} has no symbol name.", result_path))
                continue
            resolution = row.get("target_resolution", "direct")
            if resolution not in {"direct", "unresolved"}:
                diagnostics.append(GraphToolDiagnostic("GRAPH_RESOLUTION_UNKNOWN", f"Result row {index} has an unknown resolution value.", result_path))
                continue
            if pattern == "callees_of" and resolution == "direct" and result_path is None:
                diagnostics.append(GraphToolDiagnostic("GRAPH_PATH_OUTSIDE_ROOT", f"Direct callee row {index} has no safe project-relative declaration path."))
                continue
            qualified_name = row.get("qualified_name")
            if not isinstance(qualified_name, str) or not qualified_name:
                qualified_name = None
            if pattern == "callees_of":
                call_sites.append(GraphCallSite(target, call_path, call_site["line"], name, result_path,
                                                qualified_name, resolution))
            else:
                call_sites.append(GraphCallSite(name, result_path, call_site["line"], target, None,
                                                None, resolution))

    complete = (not diagnostics and result_count is not None and omitted_count == 0
                and result_count == len(call_sites))
    if pattern == "callees_of" and any(item.callee_path is None and item.resolution == "direct" for item in call_sites):
        diagnostics.append(GraphToolDiagnostic("GRAPH_CALLEE_UNLOCATED", "At least one callee has no source location."))
        complete = False
    raw_edges = response.get("edges")
    if pattern in {"callers_of", "callees_of"}:
        if not isinstance(raw_edges, list) or len(raw_edges) != len(raw_results):
            diagnostics.append(GraphToolDiagnostic("GRAPH_EDGE_ROWS_MISMATCH",
                "Graph edge rows are absent or do not align one-to-one with result rows."))
    if not isinstance(tool_version, str) or not tool_version.strip():
        diagnostics.append(GraphToolDiagnostic("GRAPH_TOOL_VERSION_UNKNOWN",
            "The tool version was not supplied with this graph query response."))
    # The graph index is a derived snapshot. The public query response does not
    # bind every returned edge to the current source digest, so callers must
    # retain this as supplemental evidence and report freshness as unknown.
    diagnostics.append(GraphToolDiagnostic("GRAPH_INDEX_FRESHNESS_UNVERIFIED",
        "The response does not attest that its graph index matches the current project sources."))
    complete = False
    content = json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return GraphQueryFacts("code-review-graph", pattern if isinstance(pattern, str) else "",
                           target if isinstance(target, str) else "", tuple(call_sites),
                           result_count, omitted_count, complete, tuple(diagnostics), content, digest, tool_version)
