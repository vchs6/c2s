#!/usr/bin/env python3
"""Run supported project-discovery selectors and emit a validated M1 bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))
sys.path.insert(0, str(REPOSITORY_ROOT / "skill" / "src"))

from c2s_semantic_contract.projection import project_query_to_m1
from c2s_semantic_contract.validation import validate_model
from c2s_skill.query import query_project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="project root to analyze")
    parser.add_argument("--select", choices=("project", "workspace-members"), action="append",
                        help="M1 selector; may be repeated")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        selectors = args.select or ["project", "workspace-members"]
        query = query_project(root, selectors)
        projection = project_query_to_m1(query)
        catalog_dir = REPOSITORY_ROOT / "contracts" / "semantic-model"
        catalogs = {key: json.loads((catalog_dir / filename).read_text(encoding="utf-8"))
                    for key, filename in (("types", "types.json"), ("predicates", "predicates.json"))}
        validation = validate_model(projection["bundle"], catalogs, projection["sourceObservations"])
        response = {"query": {"root": str(root), "selectors": selectors,
                              "complete": query.complete, "gaps": [gap.__dict__ if hasattr(gap, "__dict__")
                                  else {"selector": gap.selector, "reason": gap.reason} for gap in query.gaps]},
                    "model": projection["bundle"], "attachments": projection["artifacts"],
                    "sourceObservations": projection["sourceObservations"], "validation": validation}
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 0 if validation["valid"] and query.complete and projection["bundle"]["coverage"][0]["complete"] else 2
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"error": type(error).__name__, "message": str(error)}, ensure_ascii=False),
              file=sys.stderr)
        return 64


if __name__ == "__main__":
    raise SystemExit(main())
