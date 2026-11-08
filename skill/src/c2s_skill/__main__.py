"""Command line entry point for request-driven semantic facts."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from .algorithm import (_index_python_functions, _index_rust_functions,
                        extract_python_algorithm, extract_rust_algorithm, render_pseudocode,
                        validate_algorithms)
from .acquisition import scan_project
from .graph_tool_adapter import parse_code_review_graph_response
from .query import (normalize_request, query_project, result_to_dict,
                    result_to_markdown)
from .store import QueryResultCache
from .semantic_store import SemanticEntityStore
from .capability_matrix import (detect_available_tools, host_environment, load_tool_matrix,
                                parse_selected_tool_output, select_tools)


def _persist_semantic_entity_archive(root: Path, database: Path, implementation_view: dict | None = None,
                                     source_path: str | None = None, function_name: str | None = None,
                                     workspace_facts: tuple = (), workspace_gap: str | None = None,
                                     workspace_requested: bool = False) -> dict:
    from c2s_semantic_contract.validation import validate_semantic_entity_model
    from .entity_construction import construct_and_query_semantic_entities

    store = SemanticEntityStore(database)
    query = construct_and_query_semantic_entities(root, store, "entities")
    if workspace_requested:
        from .entity_construction import add_workspace_observations
        model = store.read(query["scopeId"])
        base_coverage = next((item for item in model["coverage"] if item["selector"] == "all-entities"), None)
        if base_coverage is None:
            from .acquisition import analysis_profile_digest
            from .inventory import source_fingerprint
            analyzer_version = analysis_profile_digest()
            input_fingerprint = "sha256:" + hashlib.sha256(
                f"{source_fingerprint(root)}\0{analyzer_version}".encode()).hexdigest()
        else:
            analyzer_version = base_coverage["analyzerVersion"]
            input_fingerprint = base_coverage["inputFingerprint"]
        diagnostics = add_workspace_observations(root, store, model, workspace_facts, workspace_gap,
                                                  input_fingerprint, analyzer_version)
        prior_diagnostics = store.read_diagnostics(query["scopeId"], input_fingerprint)
        diagnostics_by_key = {json.dumps(item, ensure_ascii=False, sort_keys=True): item
                              for item in [*prior_diagnostics, *diagnostics]}
        store.write(model, list(diagnostics_by_key.values()))
    if implementation_view is not None:
        model = store.read(query["scopeId"])
        matching = [item for item in model["sourceMappings"]
                    if item.get("target", {}).get("kind") == "ComputationEntity"
                    and item["sourceConstruct"]["path"] == source_path
                    and item["sourceConstruct"]["name"] == function_name]
        if not matching:
            raise ValueError("algorithm result has no matching computation-entity source mapping")
        payload = json.dumps(implementation_view, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        view_digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        artifact = implementation_view.get("graphToolResult")
        evidence_id = "evidence:algorithm:" + view_digest
        view = {"algorithm": implementation_view["algorithm"],
                "pseudocode": implementation_view["pseudocode"],
                "semanticFactBundle": implementation_view["semanticFactBundle"],
                "sourceObservations": implementation_view["sourceObservations"],
                "artifacts": implementation_view["artifacts"], "graphToolResult": artifact,
                "completeness": "partial_static_syntax_projection"}
        algorithm_evidence = implementation_view["semanticFactBundle"].get("evidence", [])
        known_evidence = {item["evidenceId"] for item in model["evidence"]}
        for evidence in algorithm_evidence:
            evidence_id = evidence["evidenceId"]
            entity_evidence = {"evidenceId": evidence_id,
                "source": evidence.get("source") or "algorithm_projection",
                "description": f"算法投影证据：{evidence.get('path') or evidence.get('toolName') or evidence_id}"}
            for field in ("path", "sha256", "startByte", "endByte", "method", "toolName", "toolVersion"):
                if evidence.get(field) is not None:
                    entity_evidence[field] = evidence[field]
            if evidence_id not in known_evidence:
                model["evidence"].append(entity_evidence)
                known_evidence.add(evidence_id)
        for mapping in matching:
            mapping["mappingId"] = "mapping:algorithm:" + hashlib.sha256(
                f"{mapping['mappingId']}\0{view_digest}".encode("utf-8")).hexdigest()
            mapping["role"] = "algorithm_view"
            mapping["implementationView"] = view
            mapping["evidenceIds"] = sorted(set(mapping.get("evidenceIds", []))
                                               | {item["evidenceId"] for item in algorithm_evidence})
            if artifact is not None:
                mapping["evidenceIds"] = sorted(set(mapping.get("evidenceIds", [])) | {evidence_id})
        if artifact is not None and not any(item["evidenceId"] == evidence_id for item in model["evidence"]):
            model["evidence"].append({"evidenceId": evidence_id, "source": "code-review-graph",
                "description": "本次算法请求使用的外部调用图原始JSON；freshness由查询诊断限定。",
                "method": "structured_tool_output", "toolName": "code-review-graph",
                "toolVersion": implementation_view.get("graphToolVersion") or "unknown"})
        store.write(model)
    model = store.read(query["scopeId"])
    validation = validate_semantic_entity_model(model) if model else {"valid": False, "diagnostics": []}
    if not validation["valid"]:
        raise ValueError("persisted semantic entity archive failed contract validation")
    return {"semantic_entity_query": query,
            "semantic_entity_validation": validation,
            "semantic_entity_store": {"profile": model["profile"], "scopeId": model["scopeId"],
                "state": "stored" if query["constructionStatus"] == "constructed" else "already_stored"}}


DEFAULT_MODEL_PROFILE = "semantic-entity-model-1"


def _run_v2_cli(args, root):
    from .fact_query import execute_fact_query, render_fact_result
    from .fact_request import normalize_fact_request
    if args.select and len(args.select)!=1:
        raise ValueError("v2要求一个规范请求；多描述面请用JSON请求facets")
    raw=args.request or (args.select[0] if args.select else None)
    if args.query=="algorithm":
        if not args.all_functions and not (args.source and args.function):
            raise ValueError("单函数算法需要--source和--function")
        if args.all_functions and (args.source or args.function):
            raise ValueError("全函数请求不能同时指定单函数")
        raw={"view":"entity" if args.semantic_facts else "source",
             "target":{"kind":"ComputationEntity" if args.semantic_facts else "function"},
             "facets":["implementation","algorithm"],"detail":"self"}
        if args.source:raw["target"]["path"]=args.source
        if args.function:raw["target"]["name"]=args.function
    elif args.query=="entities":
        if not raw:raise ValueError("entities需要--select或结构化--request")
        if isinstance(raw,str) and raw.startswith(("entity:","expand:")):
            raw={"view":"entity","target":{"kind":"all","name":raw.split(":",1)[1]},
                 "detail":"self","expandDepth":8 if raw.startswith("expand:") else 0}
        elif raw in {"entities","all-entities","project"}:
            raw={"view":"entity","target":{"kind":"Project" if raw=="project" else "all"},
                 "facets":["organization","attributes"],"detail":"self" if raw=="project" else "list"}
    if raw is None:raise ValueError("需要--select或--request")
    if isinstance(raw,str) and raw.lstrip().startswith("{"):raw=json.loads(raw)
    request=normalize_fact_request(raw)
    if args.query=="entities":
        request["view"]="entity";request=normalize_fact_request(request)
    if args.cache and args.store and args.cache.resolve()==args.store.resolve():
        raise ValueError("缓存和事实档案必须使用不同文件")
    runner=None
    if args.graph_output:
        if args.graph_output.resolve().is_relative_to(root):raise ValueError("图输出应位于分析项目外")
        raw_graph=json.loads(args.graph_output.read_text(encoding="utf-8"))
        request["facets"]=sorted(set(request["facets"])|{"relations"})
        request["conditions"]["graphOutputDigest"]=hashlib.sha256(args.graph_output.read_bytes()).hexdigest()
        request["conditions"]["graphVersion"]=args.graph_version or "unknown"
        runner=lambda tool_id,q:{"response":raw_graph,"toolVersion":args.graph_version}
    result=execute_fact_query(root,request,SemanticEntityStore(args.store) if args.store else None,
                              cache=QueryResultCache(args.cache) if args.cache else None,tool_runner=runner)
    good=result.get("complete",False) and result["persistence"]["status"]!="failed"
    return render_fact_result(result,args.format or "json"),0 if good else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="c2s-skill")
    parser.add_argument("query", choices=["query", "algorithm", "entities"])
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
    parser.add_argument("--store", type=Path, help="SQLite archive outside the analyzed project (profile depends on command)")
    parser.add_argument("--model-profile", choices=["semantic-entity-model-1", "semantic-entity-model-2"], default=DEFAULT_MODEL_PROFILE, help="选择实体档案和响应协议；v1用于兼容")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        if args.output and args.output.resolve().is_relative_to(root):
            raise ValueError("output must be outside the analyzed project")
        if args.model_profile == "semantic-entity-model-2":
            rendered, status = _run_v2_cli(args, root)
        elif args.query == "entities":
            if not args.select or len(args.select) != 1 or args.request:
                raise ValueError("entities requires exactly one --select selector")
            if not args.store:
                raise ValueError("entities requires --store outside the analyzed project")
            if args.cache or args.source or args.function or args.all_functions or args.semantic_facts or args.graph_output or args.graph_version:
                raise ValueError("legacy query and algorithm options are not valid for entities")
            from .entity_construction import construct_and_query_semantic_entities
            from .semantic_entity_query import render_entity_query
            entity_store = SemanticEntityStore(args.store)
            response = construct_and_query_semantic_entities(root, entity_store, args.select[0])
            rendered = render_entity_query(response, args.format or "markdown") + "\n"
            status = 0 if response.get("status") == "obtained" else 2
        elif args.query == "query":
            if (args.source or args.function or args.all_functions or args.semantic_facts
                    or args.graph_output or args.graph_version):
                raise ValueError("algorithm options are only valid for algorithm requests")
            if (args.select is None) == (args.request is None):
                raise ValueError("query requires exactly one of --select or --request")
            if args.cache and args.store and args.cache.resolve() == args.store.resolve():
                raise ValueError("--cache and --store must use separate database files")
            # Cache hits do not retain the observed tool-version provenance
            # required for a semantic session.
            cache = QueryResultCache(args.cache) if args.cache else None
            selectors = args.select if args.select else normalize_request(args.request)
            output_format = args.format or "markdown"
            result = query_project(root, selectors, cache)
            response = result_to_dict(result)
            function_facts = [fact for fact in result.facts if fact.kind == "function" and
                              any(selector.startswith("function:") and selector.removeprefix("function:")
                                  in {fact.name, f"{fact.owner}.{fact.name}"} for selector in selectors)]
            if function_facts:
                pseudocode_views = []
                for fact in function_facts:
                    try:
                        source_bytes = (root / fact.path).read_bytes()
                        if fact.path.endswith(".py"):
                            extracted = extract_python_algorithm(source_bytes, fact.path, fact.name,
                                                                 start_byte=fact.start_byte)
                        else:
                            extracted = extract_rust_algorithm(source_bytes, fact.path, fact.name,
                                                               start_byte=fact.start_byte)
                        pseudocode_views.append({**render_pseudocode(extracted["algorithm"], source_bytes),
                            "path": fact.path, "function": fact.name, "owner": fact.owner})
                    except (OSError, ValueError) as error:
                        pseudocode_views.append({"path": fact.path, "function": fact.name,
                            "error": f"ANALYSIS_FAILED:{error}", "complete": False})
                response["pseudocode"] = pseudocode_views
            if args.store:
                workspace_requested = ("workspace-members" in selectors or
                    ("all-supported-facts" in selectors and (root / "Cargo.toml").is_file()))
                workspace_gap = next((item.reason for item in result.gaps
                    if item.selector in {"workspace-members", "all-supported-facts"}
                    and ("cargo" in item.reason.lower() or "workspace" in item.reason.lower())), None)
                workspace_facts = tuple(item for item in result.facts if item.kind == "workspace_member")
                response.update(_persist_semantic_entity_archive(root, args.store,
                    workspace_facts=workspace_facts, workspace_gap=workspace_gap,
                    workspace_requested=workspace_requested))
            rendered = (json.dumps(response, ensure_ascii=False, indent=2) + "\n"
                        if output_format == "json" else result_to_markdown(result))
            if output_format == "markdown" and response.get("pseudocode"):
                rendered += "\n## 函数伪代码\n"
                for pseudocode in response["pseudocode"]:
                    rendered += f"\n### {pseudocode['function']}（{pseudocode['path']}）\n\n```text\n"
                    rendered += pseudocode.get("text", pseudocode.get("error", "无法构造伪代码"))
                    rendered += "\n```\n\n伪代码为部分静态投影，缺口和来源证据见结构化结果。\n"
            if args.store and output_format == "markdown":
                rendered += f"\nSemantic entities: {len(response['semantic_entity_query']['members'])}; "
                rendered += f"store state: {response['semantic_entity_store']['state']}\n"
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
                            "pseudocode": render_pseudocode(extracted["algorithm"], source_bytes),
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
                        response.update(_persist_semantic_entity_archive(root, args.store,
                            {"algorithm": extracted["algorithm"],
                             "pseudocode": render_pseudocode(extracted["algorithm"], source_bytes),
                             "semanticFactBundle": projection["bundle"],
                             "sourceObservations": projection["sourceObservations"],
                             "artifacts": projection["artifacts"],
                             "graphToolResult": json.loads(graph_facts.artifact_content) if graph_facts else None,
                             "graphToolVersion": graph_facts.tool_version if graph_facts else None},
                            relative_path, args.function))
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
