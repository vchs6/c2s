"""Command line entry point for request-driven semantic facts."""

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from .algorithm import (_index_python_functions, _index_rust_functions,
                        extract_python_algorithm, extract_rust_algorithm, validate_algorithms)
from .acquisition import scan_project
from .graph_tool_adapter import parse_code_review_graph_response
from .query import (normalize_request, query_project, query_result_from_dict, result_to_dict,
                    result_to_markdown)
from .store import QueryResultCache
from .semantic_store import (SemanticFactStore, commit_m1, read_m1, commit_bundle, read_bundle,
                             query_bundle, query_artifacts, read_query_report, remember_query_report)
from .capability_matrix import (detect_available_tools, host_environment, load_tool_matrix,
                                parse_selected_tool_output, select_tools)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="c2s-skill")
    parser.add_argument("query", choices=["query", "algorithm"])
    parser.add_argument("--root", required=True, type=Path)
    query_args = parser.add_mutually_exclusive_group(required=False)
    query_args.add_argument("--select", action="append", help="classes, members, functions, definitions, imports, constants, all-declarations")
    query_args.add_argument("--request", help="explicit English/Chinese request such as '有哪些类' or 'Command 的成员有哪些'")
    parser.add_argument("--source", help="source path for an algorithm request, relative to --root")
    parser.add_argument("--function", help="function name to lower into a partial algorithm description")
    parser.add_argument("--all-functions", action="store_true",
                        help="lower every discovered Python and Rust function in the project")
    parser.add_argument("--semantic-facts", action="store_true",
                        help="include a validated semantic fact bundle for a single algorithm request")
    parser.add_argument("--graph-output", type=Path,
                        help="read Code Review Graph query JSON stored outside the analyzed project")
    parser.add_argument("--graph-version", help="Code Review Graph version that produced --graph-output")
    parser.add_argument("--format", choices=["json", "markdown"], default=None)
    parser.add_argument("--output", type=Path, help="write the report outside the analyzed project")
    parser.add_argument("--cache", type=Path, help="optional SQLite query-result cache outside the analyzed project")
    parser.add_argument("--store", type=Path, help="SQLite semantic-fact repository outside the analyzed project")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        if args.output and args.output.resolve().is_relative_to(root):
            raise ValueError("output must be outside the analyzed project")
        if args.query == "query":
            if (args.source or args.function or args.all_functions or args.semantic_facts
                    or args.graph_output or args.graph_version):
                raise ValueError("algorithm options are only valid for algorithm requests")
            if (args.select is None) == (args.request is None):
                raise ValueError("query requires exactly one of --select or --request")
            if args.cache and args.store and args.cache.resolve() == args.store.resolve():
                raise ValueError("--cache and --store must use separate database files")
            # Cache hits do not retain the observed tool-version provenance
            # required for a semantic session.
            cache = QueryResultCache(args.cache) if args.cache and not args.store else None
            selectors = args.select if args.select else normalize_request(args.request)
            output_format = args.format or "markdown"
            repository = SemanticFactStore(args.store) if args.store else None
            if repository:
                from .inventory import source_fingerprint
                from .acquisition import analysis_profile_digest
                repository.validate_root(root)
                source_digest = source_fingerprint(root)
                profile_digest = analysis_profile_digest()
                hit = read_query_report(repository, root, "+".join(selectors), source_digest, profile_digest)
                if hit is not None:
                    cached_response = hit["response"]
                    cached_response["persistence"] = {"status": "cache_hit", "diagnostic": None}
                    if cached_response.get("semantic_store"):
                        cached_response["semantic_store"]["state"] = "already_stored"
                    if output_format == "json":
                        rendered = json.dumps(cached_response, ensure_ascii=False, indent=2) + "\n"
                    else:
                        cached_result = query_result_from_dict(cached_response)
                        rendered = result_to_markdown(cached_result)
                        if cached_response.get("semantic_fact_bundle"):
                            rendered += (f"\nSemantic facts: {len(cached_response['semantic_fact_bundle']['facts'])}; "
                                         f"store state: {cached_response['semantic_store']['state']}\n")
                    if args.output:
                        args.output.parent.mkdir(parents=True, exist_ok=True)
                        args.output.write_text(rendered, encoding="utf-8")
                    else:
                        sys.stdout.write(rendered)
                    return 0 if cached_response.get("complete") else 2
            result = query_project(root, selectors, cache)
            response = result_to_dict(result)
            semantic_receipt = semantic_read = semantic_validation = None
            if args.store:
                from c2s_semantic_contract.projection import project_query_to_semantic_model
                from c2s_semantic_contract.validation import semantic_model_catalogs, validate_model
                repository = SemanticFactStore(args.store)
                repository.validate_root(root)
                identity_domain = str(uuid5(NAMESPACE_URL, f"c2s-domain:{root}"))
                input_id = str(uuid5(NAMESPACE_URL, f"c2s-input:{root}:{result.source_digest}:{result.profile_digest}"))
                analysis_id = str(uuid5(NAMESPACE_URL, f"c2s-analysis:semantic-fact-model-1:{input_id}"))
                stored = read_bundle(repository, analysis_id)
                projection = project_query_to_semantic_model(result, identity_domain=identity_domain)
                semantic_validation = validate_model(projection["bundle"],
                    semantic_model_catalogs(), projection["sourceObservations"])
                if not semantic_validation["valid"]:
                    raise ValueError("projected M1 bundle failed semantic contract validation")
                from .capability_matrix import describe_tools_used
                session = {"analysisId": analysis_id, "inputId": input_id, "root": str(root),
                    "store": str(repository.path), "identityDomain": identity_domain,
                    "sourceCommit": None, "inputDigest": result.source_digest,
                    "host": {"os": platform.system().lower(), "arch": platform.machine(),
                             "pythonVersion": platform.python_version()},
                    "target": {"value": None, "basisEvidenceIds": [], "status": "unknown"},
                    "tools": describe_tools_used(result.tools_used, load_tool_matrix()),
                    "profile": "semantic-fact-model-1"}
                operation_id = str(uuid5(NAMESPACE_URL,
                    f"c2s-commit:{analysis_id}:{result.source_digest}:{','.join(selectors)}"))
                semantic_receipt = commit_bundle(repository, {"session": session, "operationId": operation_id,
                    "expectedGeneration": stored["generation"], "bundle": projection["bundle"],
                    "artifacts": projection["artifacts"], "sourceObservations": projection["sourceObservations"]})
                if semantic_receipt["state"] == "failed":
                    raise ValueError("semantic fact repository rejected the transaction")
                semantic_read = read_bundle(repository, analysis_id)
                response["semantic_fact_bundle"] = query_bundle(repository, analysis_id, "+".join(selectors))
                response["semantic_artifacts"] = query_artifacts(repository, analysis_id, "+".join(selectors))
                response["semantic_validation"] = semantic_validation
                response["semantic_store"] = semantic_receipt
                if output_format == "json":
                    remember_query_report(repository, root, "+".join(selectors), result.source_digest,
                        result.profile_digest, analysis_id, response)
            rendered = (json.dumps(response, ensure_ascii=False, indent=2) + "\n"
                        if output_format == "json" else result_to_markdown(result))
            if args.store and output_format == "markdown":
                rendered += f"\nSemantic facts: {len(semantic_read['bundle']['facts'])}; store state: {semantic_receipt['state']}\n"
            status = 0 if result.complete else 2
        else:
            if args.select or args.request or args.cache:
                raise ValueError("--select, --request and --cache are only valid for query requests")
            if args.store and not args.semantic_facts:
                raise ValueError("algorithm --store requires --semantic-facts")
            if args.all_functions:
                if args.semantic_facts or args.graph_output or args.graph_version:
                    raise ValueError("--semantic-facts currently requires one --source and --function request")
                if args.source or args.function:
                    raise ValueError("--all-functions cannot be combined with --source or --function")
                if args.format not in {None, "json"}:
                    raise ValueError("algorithm requests currently support JSON output only")
                scan = scan_project(root)
                function_facts = [fact for parsed in scan.files for fact in parsed.facts
                                  if fact.kind == "function"]
                algorithm_items = []
                project_gaps = []
                source_cache = {}
                syntax_cache = {}
                for fact in function_facts:
                    try:
                        if fact.path not in source_cache:
                            source_cache[fact.path] = (root / fact.path).read_bytes()
                        source_bytes = source_cache[fact.path]
                        if fact.path not in syntax_cache:
                            syntax_cache[fact.path] = (_index_python_functions(source_bytes)
                                                       if fact.path.endswith(".py")
                                                       else _index_rust_functions(source_bytes))
                        if fact.path.endswith(".py"):
                            tree, parents, functions = syntax_cache[fact.path]
                            function_node = functions.get(fact.start_byte)
                            if function_node is None:
                                raise ValueError("function declaration missing from Python syntax index")
                            extracted = extract_python_algorithm(source_bytes, fact.path, fact.name,
                                start_byte=fact.start_byte, _tree=tree, _parents=parents,
                                _function_node=function_node)
                        else:
                            root_node, functions = syntax_cache[fact.path]
                            function_node = functions.get(fact.start_byte)
                            if function_node is None:
                                raise ValueError("function declaration missing from Rust syntax index")
                            extracted = extract_rust_algorithm(source_bytes, fact.path, fact.name,
                                start_byte=fact.start_byte, _root_node=root_node,
                                _function_node=function_node)
                        diagnostics = validate_algorithms({"schema_version": extracted["schema_version"],
                                                           "algorithms": [extracted["algorithm"]]})
                        algorithm_items.append({"path": fact.path, "function": fact.name, "owner": fact.owner,
                                                "algorithm": extracted["algorithm"],
                                                "validation": {"scope": "structure_only",
                                                               "diagnostics": diagnostics}})
                    except (OSError, ValueError) as error:
                        project_gaps.append({"path": fact.path, "function": fact.name,
                                             "reason": f"ANALYSIS_FAILED:{error}"})
                for parsed in scan.files:
                    if not parsed.parse_complete:
                        project_gaps.append({"path": parsed.path, "reason": "PARSE_INCOMPLETE"})
                for entry in scan.inventory:
                    if entry.state != "readable" or (entry.kind == "file" and
                                                      Path(entry.path).suffix not in {".py", ".rs"}):
                        project_gaps.append({"path": entry.path, "reason": "UNHANDLED_PROJECT_PATH",
                                             "state": entry.state, "diagnostic": entry.diagnostic})
                rendered = json.dumps({"root": str(root), "source_digest": scan.source_digest,
                                       "complete": False,
                                       "claim_scope": "partial_static_syntax_projection",
                                       "coverage": {"discovered_functions": len(function_facts),
                                                    "analyzed_functions": len(algorithm_items),
                                                    "parsed_files": scan.parsed_files,
                                                    "source_files": scan.source_files,
                                                    "unhandled_paths": sum(1 for entry in scan.inventory
                                                        if entry.state != "readable" or (entry.kind == "file" and
                                                        Path(entry.path).suffix not in {".py", ".rs"})),
                                                    "whole_project_semantics_complete": False},
                                       "algorithms": algorithm_items, "gaps": project_gaps},
                                      ensure_ascii=False, indent=2) + "\n"
                status = 2 if project_gaps or function_facts or not scan.files else 0
                if not function_facts and not project_gaps:
                    status = 0
            else:
                if args.graph_version and not args.graph_output:
                    raise ValueError("--graph-version requires --graph-output")
                if args.graph_output and not args.semantic_facts:
                    raise ValueError("--graph-output requires --semantic-facts")
                if not args.source or not args.function:
                    raise ValueError("algorithm requires --source and --function, or --all-functions")
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
                gaps.extend({"category": "algorithm_body", **item}
                            for item in extracted["algorithm"]["omissions"])
                status = 0 if not diagnostics else 2
                response = {"root": str(root), "source_path": relative_path,
                            "source_digest": hashlib.sha256(source_bytes).hexdigest(),
                            "complete": False, "claim_scope": "partial_static_syntax_projection",
                            "algorithm": extracted["algorithm"],
                            "validation": {"scope": "structure_only", "diagnostics": diagnostics},
                            "gaps": gaps}
                if args.semantic_facts:
                    from c2s_semantic_contract import semantic_model_catalogs, validate_model
                    from c2s_semantic_contract.projection import project_algorithm_to_semantic_model
                    graph_facts = None
                    graph_selection = None
                    if args.graph_output:
                        graph_path = args.graph_output.resolve(strict=True)
                        if graph_path.is_relative_to(root):
                            raise ValueError("--graph-output must be outside the analyzed project")
                        matrix = load_tool_matrix()
                        graph_selection = select_tools(["calls.cross_file.candidates"], matrix,
                            available_tools=detect_available_tools(matrix), environment=host_environment())
                        graph_facts = parse_selected_tool_output(graph_selection, "code-review-graph",
                            json.loads(graph_path.read_text(encoding="utf-8")), root,
                            args.graph_version, matrix)
                    identity_domain = str(uuid5(NAMESPACE_URL, f"c2s-domain:{root}"))
                    projection = project_algorithm_to_semantic_model(extracted, root, graph_facts=graph_facts,
                                                                      identity_domain=identity_domain)
                    response["semantic_fact_bundle"] = projection["bundle"]
                    response["source_observations"] = projection["sourceObservations"]
                    response["artifacts"] = projection["artifacts"]
                    response["semantic_validation"] = validate_model(
                        projection["bundle"], semantic_model_catalogs(), projection["sourceObservations"])
                    if args.store:
                        repository = SemanticFactStore(args.store)
                        repository.validate_root(root)
                        algorithm_id = extracted["algorithm"]["algorithm_id"]
                        input_id = str(uuid5(NAMESPACE_URL, f"c2s-input:{root}:{response['source_digest']}:{algorithm_id}"))
                        analysis_id = str(uuid5(NAMESPACE_URL, f"c2s-analysis:semantic-fact-model-1:{input_id}"))
                        stored = read_bundle(repository, analysis_id)
                        session = {"analysisId": analysis_id, "inputId": input_id, "root": str(root),
                            "store": str(repository.path), "identityDomain": identity_domain,
                            "sourceCommit": None, "inputDigest": response["source_digest"],
                            "host": {"os": platform.system().lower(), "arch": platform.machine(),
                                     "pythonVersion": platform.python_version()},
                            "target": {"value": None, "basisEvidenceIds": [], "status": "unknown"},
                            "tools": [], "profile": "semantic-fact-model-1"}
                        operation_id = str(uuid5(NAMESPACE_URL, f"c2s-algorithm-commit:{analysis_id}:{algorithm_id}"))
                        receipt = commit_bundle(repository, {"session": session, "operationId": operation_id,
                            "expectedGeneration": stored["generation"], "bundle": projection["bundle"],
                            "artifacts": projection["artifacts"], "sourceObservations": projection["sourceObservations"]})
                        if receipt["state"] == "failed":
                            raise ValueError("semantic fact repository rejected the algorithm transaction")
                        response["semantic_fact_bundle"] = query_bundle(repository, analysis_id,
                            "algorithm:" + extracted["algorithm"]["algorithm_id"])
                        response["semantic_artifacts"] = query_artifacts(repository, analysis_id,
                            "algorithm:" + extracted["algorithm"]["algorithm_id"])
                        response["semantic_store"] = receipt
                    if graph_facts is not None:
                        response["graph_query"] = {"tool": graph_facts.tool, "pattern": graph_facts.pattern,
                            "selected_tool_ids": list(graph_selection.tools),
                            "target": graph_facts.target, "complete": graph_facts.complete,
                            "result_count": graph_facts.result_count,
                            "omitted_count": graph_facts.omitted_count,
                            "diagnostics": [{"code": item.code, "message": item.message, "path": item.path}
                                            for item in graph_facts.diagnostics]}
                        if not graph_facts.complete:
                            status = 2
                rendered = json.dumps(response, ensure_ascii=False, indent=2) + "\n"
                if not args.graph_output:
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
