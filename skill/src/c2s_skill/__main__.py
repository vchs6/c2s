"""Command line entry point for request-driven semantic facts."""

import argparse
import json
import sys
from pathlib import Path

from .query import normalize_request, query_project, result_to_dict, result_to_markdown
from .store import FactStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="c2s-skill")
    parser.add_argument("query", choices=["query"])
    parser.add_argument("--root", required=True, type=Path)
    query_args = parser.add_mutually_exclusive_group(required=True)
    query_args.add_argument("--select", action="append", help="classes, members, functions, definitions, imports, constants, all-declarations")
    query_args.add_argument("--request", help="explicit English/Chinese request such as '有哪些类' or 'Command 的成员有哪些'")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--output", type=Path, help="write the report outside the analyzed project")
    parser.add_argument("--store", type=Path, help="SQLite fact cache outside the analyzed project")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        if args.output and args.output.resolve().is_relative_to(root):
            raise ValueError("output must be outside the analyzed project")
        store = FactStore(args.store) if args.store else None
        selectors = args.select if args.select else normalize_request(args.request)
        result = query_project(root, selectors, store)
        rendered = json.dumps(result_to_dict(result), ensure_ascii=False, indent=2) + "\n" if args.format == "json" else result_to_markdown(result)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return 0 if result.complete else 2
    except (OSError, ValueError) as error:
        print(f"c2s-skill: {error}", file=sys.stderr)
        return 64


if __name__ == "__main__":
    raise SystemExit(main())
