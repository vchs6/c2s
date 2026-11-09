"""唯一V2查询执行入口。"""
from pathlib import Path

def query_project_v2(root: Path, request: dict | str, store=None, *, cache=None) -> dict:
    """公开v2入口，复用统一执行器而不复制获取或投影逻辑。"""
    from .fact_query import execute_fact_query
    return execute_fact_query(root,request,store,cache=cache)
