"""Request normalization and bounded projections over a complete source scan."""

from dataclasses import dataclass, replace
from pathlib import Path
import sqlite3

from .acquisition import Fact, ProjectScan, analysis_profile_digest, cargo_workspace_facts, scan_project, source_fingerprint
from .inventory import InventoryEntry


SELECTORS = {
    "project": {"project_name", "language_declared"},
    "workspace-members": {"workspace_member"},
    "behavior-contracts": {"behavior_contract"},
    "algorithm-structure": {"algorithm_step"},
    "classes": {"class", "struct", "enum", "trait"},
    "members": {"field", "variant"},
    "functions": {"function"},
    "definitions": {"class", "struct", "enum", "trait", "field", "variant", "function", "constant", "constant_item", "static_item", "type_alias", "module", "impl"},
    "imports": {"import"},
    "constants": {"constant", "constant_item", "static_item"},
    "all-declarations": {"class", "struct", "enum", "trait", "field", "variant", "function", "constant", "constant_item", "static_item", "type_alias", "module", "impl", "import"},
    "all-supported-facts": {"project_name", "language_declared", "workspace_member", "behavior_contract", "algorithm_step",
                             "class", "struct", "enum", "trait", "field", "variant", "function",
                             "constant", "constant_item", "static_item", "type_alias", "module", "impl", "import"},
}


def normalize_request(request: str) -> list[str]:
    """Map explicit natural-language query forms; preserve unsupported text as a gap key."""
    text = request.strip()
    if not text:
        return ["unrecognized:"]
    if any(term in text.lower() for term in ("classes", "class list", "有哪些类", "所有类", "类清单")):
        return ["classes"]
    member = __import__("re").search(r"(.+?)(?:的成员(?:有哪些)?|成员有哪些|\bmembers\s+of\s+(.+))", text, __import__("re").I)
    if member:
        target = (member.group(1) or member.group(2)).strip(" ：:，,")
        if target:
            return [f"members:{target}"]
    function = __import__("re").search(r"(?:函数|function)\s+([A-Za-z_][\w.:]*)", text, __import__("re").I)
    if function:
        return [f"function:{function.group(1)}"]
    if any(term in text.lower() for term in ("functions", "函数列表", "有哪些函数")):
        return ["functions"]
    return [f"unrecognized:{text}"]


def validate_selectors(selectors: list[str]) -> list[str]:
    if not isinstance(selectors, list) or not selectors:
        raise ValueError("selectors must be a non-empty list")
    normalized = []
    for selector in selectors:
        if not isinstance(selector, str) or not selector.strip():
            raise ValueError("selectors must contain non-empty strings")
        selector = selector.strip()
        if selector in {"function:", "members:"}:
            raise ValueError(f"selector {selector!r} requires a target")
        normalized.append(selector)
    return normalized


def _inventory_gap_reason(entry: InventoryEntry) -> str:
    if entry.diagnostic:
        return entry.diagnostic
    if entry.state == "unfollowed":
        return "SYMLINK_NOT_FOLLOWED"
    if entry.state != "readable":
        return "PATH_UNREADABLE"
    if entry.kind == "file" and Path(entry.path).suffix not in {".py", ".rs"}:
        return "UNSUPPORTED_FILE_TYPE"
    return "UNSUPPORTED_PATH_TYPE"


@dataclass(frozen=True, slots=True)
class Gap:
    selector: str
    reason: str


@dataclass(frozen=True, slots=True)
class PersistenceResult:
    status: str
    diagnostic: str | None = None


@dataclass(frozen=True, slots=True)
class QueryResult:
    root: str
    requested: tuple[str, ...]
    facts: tuple[Fact, ...]
    gaps: tuple[Gap, ...]
    complete: bool
    source_files: int
    parsed_files: int
    source_digest: str
    inventory: tuple[InventoryEntry, ...]
    profile_digest: str
    persistence: PersistenceResult = PersistenceResult("not_requested")


def query_from_scan(scan: ProjectScan, selectors: list[str],
                    workspace_facts: tuple[Fact, ...] = (),
                    workspace_gap: str | None = None,
                    workspace_loaded: bool = False,
                    profile_digest: str | None = None) -> QueryResult:
    selectors = validate_selectors(selectors)
    wanted: set[str] = set()
    general_wanted: set[str] = set()
    gaps: list[Gap] = []
    for selector in selectors:
        if selector.startswith("function:") and selector.removeprefix("function:"):
            wanted.add("function")
            continue
        if selector.startswith("members:") and selector.removeprefix("members:"):
            wanted.update({"field", "variant", "function"})
            continue
        if selector not in SELECTORS:
            gaps.append(Gap(selector, "UNSUPPORTED_PREDICATE"))
        elif selector == "workspace-members":
            general_wanted.add("workspace_member")
            if not (Path(scan.root) / "Cargo.toml").is_file():
                gaps.append(Gap(selector, "UNSUPPORTED_SOURCE:workspace-declaration-not-found"))
            elif workspace_gap:
                gaps.append(Gap(selector, workspace_gap))
            elif not workspace_loaded:
                gaps.append(Gap(selector, "ACQUISITION_NOT_RUN:cargo-metadata"))
        else:
            wanted.update(SELECTORS[selector])
            general_wanted.update(SELECTORS[selector])
            if selector == "all-supported-facts" and (Path(scan.root) / "Cargo.toml").is_file():
                if workspace_gap:
                    gaps.append(Gap(selector, workspace_gap))
                elif not workspace_loaded:
                    gaps.append(Gap(selector, "ACQUISITION_NOT_RUN:cargo-metadata"))
    member_owners = {selector.removeprefix("members:") for selector in selectors if selector.startswith("members:")}
    function_names = {selector.removeprefix("function:") for selector in selectors if selector.startswith("function:")}
    available_facts = [fact for parsed in scan.files for fact in parsed.facts] + list(scan.project_facts) + list(workspace_facts)
    function_subjects = {fact.subject_id for fact in available_facts
                         if fact.kind == "function" and
                         (fact.name in function_names or f"{fact.owner}.{fact.name}" in function_names)}
    if "project" in selectors:
        present = {fact.kind for fact in available_facts if fact.kind in {"project_name", "language_declared"}}
        for kind in {"project_name", "language_declared"} - present:
            gaps.append(Gap("project", f"PROJECT_FACT_UNAVAILABLE:{kind}"))
    facts = tuple(sorted((fact for fact in available_facts
                          if fact.kind in general_wanted or
                          (fact.kind in {"field", "variant", "function"} and fact.owner in member_owners) or
                          (fact.kind == "function" and (fact.name in function_names or f"{fact.owner}.{fact.name}" in function_names)) or
                          (fact.kind in {"behavior_contract", "algorithm_step"} and
                           fact.subject_id in function_subjects)
                          ),
                         key=lambda fact: (fact.path, fact.start_byte, fact.kind, fact.id)))
    for selector in selectors:
        if selector.startswith("members:"):
            target = selector.removeprefix("members:")
            if not any(f.kind in {"class", "struct", "enum", "trait"} and f.name == target
                       for f in available_facts):
                gaps.append(Gap(selector, f"SUBJECT_NOT_FOUND:{selector}"))
        elif selector.startswith("function:"):
            target = selector.removeprefix("function:")
            if not any(f.kind == "function" and
                       (f.name == target or (f.owner and f"{f.owner}.{f.name}" == target))
                       for f in available_facts):
                gaps.append(Gap(selector, f"SUBJECT_NOT_FOUND:{selector}"))
    include_all_bodies = bool({"definitions", "all-supported-facts"} & set(selectors))
    list_scopes = {"classes", "functions", "all-declarations"}
    list_only = bool(list_scopes & set(selectors)) and not include_all_bodies
    target_definitions = {selector.removeprefix("function:") for selector in selectors
                          if selector.startswith("function:")}
    if list_only:
        projected = []
        for fact in facts:
            hide_body = fact.kind in {"class", "struct", "enum", "trait"} and "classes" in selectors
            hide_body = hide_body or (fact.kind == "function" and
                                      ("functions" in selectors or any(s.startswith("members:") for s in selectors)
                                       or "all-declarations" in selectors))
            if hide_body and fact.name not in target_definitions:
                projected.append(replace(fact, text="", evidence_included=False))
            else:
                projected.append(fact)
        facts = tuple(projected)
    failed = [parsed for parsed in scan.files if not parsed.parse_complete]
    if failed:
        gaps.extend(Gap(selectors[0], f"PARSE_INCOMPLETE:{parsed.path}") for parsed in failed)
    return QueryResult(scan.root, tuple(selectors), facts, tuple(gaps), not gaps, scan.source_files,
                       scan.parsed_files, scan.source_digest, scan.inventory,
                       profile_digest or analysis_profile_digest())


def query_project(root: Path, selectors: list[str], store=None) -> QueryResult:
    selectors = validate_selectors(selectors)
    root = root.resolve(strict=True)
    if store is not None:
        store.validate_root(root)
    profile_digest = analysis_profile_digest()
    if store is not None:
        digest = source_fingerprint(root)
        try:
            cached = store.load(root, selectors, digest, profile_digest)
        except (sqlite3.Error, OSError, ValueError, KeyError, TypeError) as error:
            cached = None
            persistence_read_error = type(error).__name__
        else:
            persistence_read_error = None
        if cached is not None:
            return replace(cached, persistence=PersistenceResult("cache_hit"))
    scan = scan_project(root)
    if store is not None and source_fingerprint(root) != scan.source_digest:
        raise ValueError("project sources changed during analysis; retry the request")
    needs_workspace = any(selector in {"workspace-members", "all-supported-facts"} for selector in selectors)
    workspace_facts: list[Fact] = []
    workspace_gap = None
    workspace_loaded = False
    if needs_workspace and (root / "Cargo.toml").is_file():
        workspace_loaded = True
        workspace_facts, workspace_gap = cargo_workspace_facts(root)
    result = query_from_scan(scan, selectors, tuple(workspace_facts), workspace_gap,
                             workspace_loaded, profile_digest)
    if store is not None:
        recovered = replace(result, persistence=PersistenceResult(
            "saved_after_read_failure" if persistence_read_error else "saved", persistence_read_error))
        try:
            store.save(recovered, recovered.source_digest)
        except (sqlite3.Error, OSError, ValueError, KeyError, TypeError) as error:
            status = "read_write_failed" if persistence_read_error else "write_failed"
            result = replace(result, persistence=PersistenceResult(status, type(error).__name__))
        else:
            result = recovered
    return result


def result_to_dict(result: QueryResult) -> dict:
    return {
        "root": result.root,
        "requested": list(result.requested),
        "complete": result.complete,
        "coverage": {"source_files": result.source_files, "parsed_files": result.parsed_files,
                     "claim_scope": "syntax_and_explicit_manifest_declarations",
                     "whole_project_semantics_complete": False,
                     "inventory_entries": len(result.inventory),
                     "unhandled_paths": [{"path": entry.path, "kind": entry.kind,
                                          "state": entry.state, "diagnostic": entry.diagnostic,
                                          "reason": _inventory_gap_reason(entry)}
                                         for entry in result.inventory
                                         if entry.state != "readable" or (entry.kind == "file" and
                                             Path(entry.path).suffix not in {".py", ".rs"})]},
        "inventory": [{"path": entry.path, "kind": entry.kind, "size_bytes": entry.size_bytes,
                       "state": entry.state, "diagnostic": entry.diagnostic}
                      for entry in result.inventory],
        "source_digest": result.source_digest,
        "profile_digest": result.profile_digest,
        "persistence": {"status": result.persistence.status,
                        "diagnostic": result.persistence.diagnostic},
        "facts": [fact.__dict__ if hasattr(fact, "__dict__") else {
            "id": fact.id, "kind": fact.kind, "name": fact.name, "path": fact.path,
            "start_byte": fact.start_byte, "end_byte": fact.end_byte, "layer": fact.layer,
            "claim_mode": fact.claim_mode, "text": fact.text,
            "owner": fact.owner, "subject_id": fact.subject_id,
            "evidence_included": fact.evidence_included,
        } for fact in result.facts],
        "gaps": [{"selector": gap.selector, "reason": gap.reason} for gap in result.gaps],
    }


def result_to_markdown(result: QueryResult) -> str:
    unhandled = [entry for entry in result.inventory
                 if entry.state != "readable" or (entry.kind == "file" and
                    Path(entry.path).suffix not in {".py", ".rs"})]
    lines = [f"# Semantic facts: {', '.join(result.requested)}", "",
             f"Coverage: {result.parsed_files}/{result.source_files} source files parsed; "
             f"{len(result.inventory)} inventory entries, {len(unhandled)} unhandled paths; "
             f"selected syntax projection complete={str(result.complete).lower()}; full project semantics=false",
             f"Persistence: {result.persistence.status}"
             + (f" ({result.persistence.diagnostic})" if result.persistence.diagnostic else ""), "",
             "## Facts", ""]
    for fact in result.facts:
        lines.append(f"- `{fact.kind}` **{fact.name}** — id `{fact.id}`, subject `{fact.subject_id}`, "
                     f"`{fact.path}:{fact.start_byte}-{fact.end_byte}` ({fact.claim_mode})")
        if fact.evidence_included:
            lines.extend(f"> {line}" if line else ">" for line in fact.text.splitlines())
        else:
            lines.append("> Source body omitted for this top-level projection.")
    if not result.facts:
        lines.append("No matching facts acquired.")
    lines.extend(["", "## Gaps", ""])
    lines.extend(f"- `{gap.selector}`: {gap.reason}" for gap in result.gaps)
    if not result.gaps:
        lines.append("None.")
    lines.extend(["", "## Unhandled inventory paths", ""])
    lines.extend(f"- `{entry.path}` ({entry.kind}, {entry.state}, {_inventory_gap_reason(entry)})"
                 for entry in unhandled)
    if not unhandled:
        lines.append("None.")
    return "\n".join(lines) + "\n"
