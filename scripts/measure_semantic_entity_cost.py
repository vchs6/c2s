#!/usr/bin/env python3
"""实测旧源码事实查询与新语义实体档案的耗时、落盘和解析调用。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "skill" / "src"))

from c2s_skill.entity_construction import construct_and_query_semantic_entities
from c2s_skill.query import query_project
from c2s_skill.semantic_store import SemanticEntityStore
from c2s_skill.store import QueryResultCache


def measure(project: Path) -> dict:
    project = project.resolve(strict=True)
    old_scans = 0
    old_scan = __import__("c2s_skill.acquisition", fromlist=["scan_project"]).scan_project
    def count_old_scan(*args, **kwargs):
        nonlocal old_scans
        old_scans += 1
        return old_scan(*args, **kwargs)
    with tempfile.TemporaryDirectory() as directory:
        old_database = Path(directory) / "facts.sqlite"
        old_store = QueryResultCache(old_database)
        start = time.perf_counter()
        with patch("c2s_skill.query.scan_project", side_effect=count_old_scan):
            old_result = query_project(project, ["all-supported-facts"], store=old_store)
        old_seconds = time.perf_counter() - start
        old_bytes = old_database.stat().st_size

        new_scans = 0
        new_scan = old_scan
        def count_new_scan(*args, **kwargs):
            nonlocal new_scans
            new_scans += 1
            return new_scan(*args, **kwargs)
        database = Path(directory) / "entities.sqlite"
        store = SemanticEntityStore(database)
        start = time.perf_counter()
        with patch("c2s_skill.entity_construction.scan_project", side_effect=count_new_scan):
            new_result = construct_and_query_semantic_entities(project, store, "project")
        new_seconds = time.perf_counter() - start
        scope_id = new_result["entity"]["ref"]["identity"]["domainId"]
        archive = store.read(scope_id)
        model_bytes = len(json.dumps(archive, ensure_ascii=False, sort_keys=True).encode())
        database_bytes = database.stat().st_size
    return {"project": project.name,
        "old": {"seconds": round(old_seconds, 3), "scannerCalls": old_scans,
            "parsedFiles": old_result.parsed_files, "factCount": len(old_result.facts),
            "gapCount": len(old_result.gaps), "sqliteBytes": old_bytes},
        "entity": {"seconds": round(new_seconds, 3), "scannerCalls": new_scans,
            "entityCount": len(archive["entities"]), "attributeCount": sum(len(item["attributes"])
                for item in archive["entities"]), "relationCount": len(archive["relations"]),
            "sourceMappingCount": len(archive.get("sourceMappings", [])),
            "coverageCount": len(archive["coverage"]), "constructionGapCount": len(new_result["constructionDiagnostics"]),
            "serializedModelBytes": model_bytes, "sqliteBytes": database_bytes}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("projects", nargs="+", type=Path)
    args = parser.parse_args()
    results = [measure(project) for project in args.projects]
    lines = ["# 语义实体分析成本实测", "",
        "日期：2026-11-07。比较的是固定项目检出上的旧`all-supported-facts`源码事实查询与新`all-entities`语义实体档案构造。",
        "两者模型覆盖范围不同，因此不据此声称等价吞吐或成本收益。所有计时均为当前容器单次公开运行。",
        "未调用大语言模型；词元消耗记为未测/未使用，不虚构节省量。", ""]
    for result in results:
        lines.extend([f"## {result['project']}", "",
            f"旧路径：耗时 {result['old']['seconds']} 秒，解析器调用 {result['old']['scannerCalls']} 次，"
            f"解析文件 {result['old']['parsedFiles']} 个，事实 {result['old']['factCount']} 条，"
            f"缺口 {result['old']['gapCount']} 个，SQLite {result['old']['sqliteBytes']} 字节。",
            f"新路径：耗时 {result['entity']['seconds']} 秒，解析器调用 {result['entity']['scannerCalls']} 次，"
            f"实体 {result['entity']['entityCount']} 个、属性 {result['entity']['attributeCount']} 项、"
            f"关系 {result['entity']['relationCount']} 条、源码映射 {result['entity']['sourceMappingCount']} 条，"
            f"覆盖 {result['entity']['coverageCount']} 项、缺口 {result['entity']['constructionGapCount']} 个；"
            f"档案JSON {result['entity']['serializedModelBytes']} 字节，SQLite {result['entity']['sqliteBytes']} 字节。", ""])
    lines.extend(["## 解释", "",
        "旧路径返回语法/事实清单，新路径返回暂定语义实体、属性、关系、源码映射和证据；记录数量和缺口定义不相等。",
        "新路径的相同输入缓存命中另由`test_construct_store_query_reuses_unchanged_coverage_and_invalidates_changes`验证，"
        "本表新路径计时包含首次解析和SQLite落盘。", ""])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
