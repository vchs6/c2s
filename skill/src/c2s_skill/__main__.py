"""Command line entry point for request-driven semantic facts."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .algorithm import extract_python_algorithm, extract_rust_algorithm, validate_algorithms
from .query import normalize_request, query_project, result_to_dict, result_to_markdown
from .store import FactStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="c2s-skill")
    parser.add_argument("query", choices=["query", "algorithm"])
    parser.add_argument("--root", required=True, type=Path)
    query_args = parser.add_mutually_exclusive_group(required=False)
    query_args.add_argument("--select", action="append", help="classes, members, functions, definitions, imports, constants, all-declarations")
    query_args.add_argument("--request", help="explicit English/Chinese request such as '有哪些类' or 'Command 的成员有哪些'")
    parser.add_argument("--source", help="source path for an algorithm request, relative to --root")
    parser.add_argument("--function", help="function name to lower into a partial algorithm description")
    parser.add_argument("--format", choices=["json", "markdown"], default=None)
    parser.add_argument("--output", type=Path, help="write the report outside the analyzed project")
    parser.add_argument("--store", type=Path, help="SQLite fact cache outside the analyzed project")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        if args.output and args.output.resolve().is_relative_to(root):
            raise ValueError("output must be outside the analyzed project")
        if args.query == "query":
            if args.source or args.function:
                raise ValueError("--source and --function are only valid for algorithm requests")
            if (args.select is None) == (args.request is None):
                raise ValueError("query requires exactly one of --select or --request")
            store = FactStore(args.store) if args.store else None
            selectors = args.select if args.select else normalize_request(args.request)
            result = query_project(root, selectors, store)
            output_format = args.format or "markdown"
            rendered = (json.dumps(result_to_dict(result), ensure_ascii=False, indent=2) + "\n"
                        if output_format == "json" else result_to_markdown(result))
            status = 0 if result.complete else 2
        else:
            if args.select or args.request or args.store:
                raise ValueError("--select, --request and --store are only valid for query requests")
            if not args.source or not args.function:
                raise ValueError("algorithm requires --source and --function")
            output_format = args.format or "json"
            if output_format != "json":
                raise ValueError("algorithm requests currently support JSON output only")
            candidate = root / args.source
            cursor = candidate
            while cursor != root and root in cursor.parents:
                if cursor.is_symlink():
                    raise ValueError("algorithm source path must not traverse symlinks")
                cursor = cursor.parent
            source_path = candidate.resolve(strict=True)
            if not source_path.is_relative_to(root) or not source_path.is_file():
                raise ValueError("algorithm source must be a file inside the analyzed project")
            source_bytes = source_path.read_bytes()
            relative_path = source_path.relative_to(root).as_posix()
            if source_path.suffix == ".py":
                extracted = extract_python_algorithm(source_bytes, relative_path, args.function)
            elif source_path.suffix == ".rs":
                extracted = extract_rust_algorithm(source_bytes, relative_path, args.function)
            else:
                raise ValueError("algorithm source must have a .py or .rs extension")
            diagnostics = validate_algorithms({"schema_version": extracted["schema_version"],
                                               "algorithms": [extracted["algorithm"]]})
            coverage = extracted["algorithm"]["contract"]["coverage"]
            gaps = [{"category": item["category"], "state": item["state"], "reason": item.get("reason")}
                    for item in coverage if item["state"] != "complete"]
            gaps.extend({"category": "algorithm_body", **item} for item in extracted["algorithm"]["omissions"])
            rendered = json.dumps({"root": str(root), "source_path": relative_path,
                                   "source_digest": hashlib.sha256(source_bytes).hexdigest(),
                                   "complete": False, "claim_scope": "partial_static_syntax_projection",
                                   "algorithm": extracted["algorithm"],
                                   "validation": {"scope": "structure_only", "diagnostics": diagnostics},
                                   "gaps": gaps}, ensure_ascii=False, indent=2) + "\n"
            status = 0 if not diagnostics else 2
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return status
    except (OSError, ValueError) as error:
        print(f"c2s-skill: {error}", file=sys.stderr)
        return 64


if __name__ == "__main__":
    raise SystemExit(main())
