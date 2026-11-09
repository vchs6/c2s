"""按请求取得并查询V2语义事实。"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from .store import QueryResultCache
from .semantic_store import SemanticEntityStore

DEFAULT_MODEL_PROFILE = "semantic-entity-model-2"

def _run_v2_cli(args, root):
    from .fact_query import execute_fact_query, render_fact_result
    from .fact_request import normalize_fact_request
    if args.query=="query" and (args.source or args.function or args.all_functions or args.semantic_facts):
        raise ValueError("这些算法选项只用于algorithm命令")
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
                 "detail":"self","expandDepth":8 if raw.startswith("expand:") else 0,"conditions":{"entityIdSelector":True}}
        elif raw in {"entities","all-entities","project"}:
            raw={"view":"entity","target":{"kind":"Project" if raw=="project" else "all"},
                 "facets":["organization","attributes"],"detail":"self" if raw=="project" else "list"}
    if raw is None:raise ValueError("需要--select或--request")
    if isinstance(raw,str) and raw.lstrip().startswith("{"):raw=json.loads(raw)
    if args.query=="entities" and isinstance(raw,dict):raw["view"]="entity"
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
    parser = argparse.ArgumentParser(prog="codesemantics")
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
    parser.add_argument("--model-profile", choices=["semantic-entity-model-2"], default=DEFAULT_MODEL_PROFILE, help="唯一支持V2实体档案和响应协议")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        if args.output and args.output.resolve().is_relative_to(root):
            raise ValueError("output must be outside the analyzed project")
        rendered, status = _run_v2_cli(args, root)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return status
    except (OSError, ValueError) as error:
        print(f"codesemantics: {error}", file=sys.stderr)
        return 64

if __name__ == "__main__":
    raise SystemExit(main())
