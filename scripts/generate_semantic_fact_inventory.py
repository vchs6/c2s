"""Regenerate the pinned real-project semantic-fact inventory and function examples."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skill" / "src"))

from c2s_skill.acquisition import analysis_profile_digest, cargo_workspace_facts, scan_project  # noqa: E402
from c2s_skill.query import _inventory_gap_reason, query_from_scan  # noqa: E402


REAL_ROOT = ROOT / ".local" / "real-projects"
LOCAL_CARGO = ROOT / ".local" / "cargo" / "bin" / "cargo"
if LOCAL_CARGO.is_file():
    os.environ.setdefault("CARGO", str(LOCAL_CARGO))
    os.environ.setdefault("CARGO_HOME", str(ROOT / ".local" / "cargo"))
    os.environ.setdefault("RUSTUP_HOME", str(ROOT / ".local" / "rustup"))
REPORT = ROOT / "docs/development/reviews/semantic-facts/2026-11-06-exhaustive-inventory.json"
EXAMPLE = ROOT / "docs/development/reviews/semantic-facts/2026-11-06-two-function-facts.md"


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True,
                          text=True).stdout.strip()


def project_report(name: str) -> tuple[dict, object]:
    root = REAL_ROOT / name
    start = time.monotonic()
    expected = {"regex": "94ac45b2a6e7b1c30927feb5b66c5ded5b7ad447",
                "click": "2247b35ea1c47c727d7a06e51fa280e12a863ff6"}[name]
    actual = git(root, "rev-parse", "HEAD")
    if actual != expected or git(root, "status", "--porcelain"):
        raise RuntimeError(f"{name} must be clean at pinned commit {expected}; found {actual}")
    scan = scan_project(root)
    workspace, workspace_gap = cargo_workspace_facts(root) if (root / "Cargo.toml").is_file() else ([], None)
    result = query_from_scan(scan, ["all-supported-facts"], tuple(workspace), workspace_gap,
                             (root / "Cargo.toml").is_file(), analysis_profile_digest())
    facts = list(result.facts)
    ids = [fact.id for fact in facts]
    if scan.parsed_files != scan.source_files or any(not parsed.parse_complete for parsed in scan.files):
        raise RuntimeError(f"{name} source parse coverage is incomplete")
    if not result.complete or len(ids) != len(set(ids)):
        raise RuntimeError(f"{name} query is incomplete or contains duplicate fact IDs")
    declarations = [fact for fact in facts if fact.kind == "function"]
    targets = {(f"{fact.owner}.{fact.name}" if fact.owner else fact.name) for fact in declarations}
    selectors = [f"function:{target}" for target in sorted(targets)]
    subjects = {fact.subject_id for fact in declarations
                if fact.name in targets or f"{fact.owner}.{fact.name}" in targets}
    expected_function_facts = {fact.id for fact in facts if fact.subject_id in subjects and
                               fact.kind in {"function", "behavior_contract", "algorithm_step", "local_binding"}}
    function_result = query_from_scan(scan, selectors)
    if not function_result.complete or {fact.id for fact in function_result.facts} != expected_function_facts:
        raise RuntimeError(f"{name} per-function fact projection is incomplete")
    counts = Counter(f.kind for f in facts)
    layers = Counter(f.layer for f in facts)
    by_subject: dict[str, list] = defaultdict(list)
    for fact in facts:
        by_subject[fact.subject_id].append(fact)
    shared = [{"subject_id": subject, "fact_ids": [f.id for f in group],
               "kinds": sorted({f.kind for f in group})}
              for subject, group in sorted(by_subject.items()) if len(group) > 1]
    unhandled = [{"path": item.path, "kind": item.kind, "state": item.state,
                  "diagnostic": item.diagnostic, "reason": _inventory_gap_reason(item)}
                 for item in result.inventory if item.state != "readable" or
                 (item.kind == "file" and Path(item.path).suffix not in {".py", ".rs"})]
    parser_count = sum(len(parsed.facts) for parsed in scan.files)
    returned_ids = [fact.id for fact in facts]
    file_rows = [{"path": parsed.path, "language": parsed.language,
                  "source_sha256": parsed.source_sha256, "parse_complete": parsed.parse_complete,
                  "diagnostics": list(parsed.diagnostics), "fact_count": len(parsed.facts),
                  "fact_ids": [fact.id for fact in parsed.facts]}
                 for parsed in scan.files]
    detail = {
        "analysis_root": str(root.resolve()), "git_commit": git(root, "rev-parse", "HEAD"),
        "source_worktree_clean": not git(root, "status", "--porcelain"),
        "source_digest": scan.source_digest, "profile_digest": result.profile_digest,
        "query": "all-supported-facts", "complete": result.complete,
        "whole_project_semantics_complete": False,
        "source_files": scan.source_files, "parsed_files": scan.parsed_files,
        "syntax_node_count": scan.syntax_node_count, "parser_fact_count": parser_count,
        "function_declaration_count": len(declarations),
        "function_selector_count": len(selectors),
        "function_projection_fact_count": len(function_result.facts),
        "workspace_fact_count": len(workspace), "returned_fact_count": len(facts),
        "unique_returned_fact_ids": len(set(returned_ids)),
        "duplicate_fact_ids": len(returned_ids) - len(set(returned_ids)),
        "fact_kinds": dict(sorted(counts.items())),
        "fact_layers": {layer: layers[layer] for layer in ("E0", "E1", "E2", "E3", "E4")},
        "elapsed_seconds": round(time.monotonic() - start, 3), "files": file_rows,
        "workspace_facts": [fact.id for fact in workspace], "shared_subjects": shared,
        "inventory_entry_count": len(result.inventory), "unhandled_paths": unhandled,
        "gaps": [{"selector": gap.selector, "reason": gap.reason} for gap in result.gaps],
    }
    return detail, {"scan": scan, "facts": facts, "result": result}


def function_example(project: dict) -> str:
    scan = project["scan"]
    facts = project["facts"]
    path = "examples/naval/naval.py"
    source = (REAL_ROOT / "click" / path).read_bytes()
    functions = ("ship_move", "ship_shoot")
    lines = ["# 两个 Python 函数的代码级语义事实示例", "",
             "项目：Click 示例 `examples/naval/naval.py`。",
             f"固定提交：`{git(REAL_ROOT / 'click', 'rev-parse', 'HEAD')}`。",
             "查询：`all-supported-facts`，按共享 `subject_id` 投影目标函数。",
             "分析器：C2S semantic facts 0.6.2。静态 AST 证据，不代表运行时验证。", ""]
    for name in functions:
        declaration = next(f for f in facts if f.kind == "function" and f.path == path and f.name == name)
        related = [f for f in facts if f.subject_id == declaration.subject_id]
        lines.extend([f"## `{name}`", "", f"- 主体 ID：`{declaration.subject_id}`",
                      f"- 函数声明：E2，`{path}:{declaration.start_byte}-{declaration.end_byte}`；fact ID `{declaration.id}`。"])
        for fact in related:
            if fact.kind == "behavior_contract":
                lines.append(f"- 源码文档：E3，{fact.text}（fact ID `{fact.id}`）。")
        steps = [f for f in related if f.kind == "algorithm_step"]
        lines.append("- 函数体代码事实：")
        if steps:
            for fact in steps:
                line = source.count(b"\n", 0, fact.start_byte) + 1
                lines.append(f"  - E4 `{fact.name}`，第 {line} 行，fact ID `{fact.id}`：`{fact.text}`")
        else:
            lines.append("  - 无已提取的函数体步骤。")
        lines.append(f"- 本函数共 {len(related)} 条当前支持事实。")
        lines.append("")
    lines.extend(["边界：调用目标解析、变量/类型绑定、跨函数数据流、异常传播和运行时效果尚未完成；本报告只陈述语法树与源码文档中直接可见的事实。", ""])
    return "\n".join(lines)


def main() -> None:
    reports = {}
    projects = {}
    for name in ("regex", "click"):
        reports[name], projects[name] = project_report(name)
        print(f"{name}: {reports[name]['parsed_files']}/{reports[name]['source_files']} files, "
              f"{reports[name]['returned_fact_count']} facts, "
              f"{reports[name]['duplicate_fact_ids']} duplicate IDs")
    cargo_version = "unavailable"
    try:
        cargo_version = subprocess.run([os.environ.get("CARGO", "cargo"), "--version"],
                                       capture_output=True, text=True, check=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    payload = {"report_date": "2026-11-06",
               "scope": "all currently supported facts; not exhaustive E0-E4 project semantics",
               "toolchain": {"analyzer": "c2s-semantic-facts/0.6.2",
                             "python": f"Python {sys.version.split()[0]}", "cargo": cargo_version},
               "validation": {"inventory_generation": "passed; pinned clean inputs, all source files parsed, "
                                                       "all-supported query complete, unique fact IDs, "
                                                       "all function selectors return their expected subject facts",
                              "external_checks": "not run by this inventory generator",
                              "private_acceptance": "not_run"},
               "projects": reports}
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    EXAMPLE.write_text(function_example(projects["click"]), encoding="utf-8")


if __name__ == "__main__":
    main()
