"""外部固定夹具：单元模式可明确跳过，强制集成模式不得缺失。"""
import os
from pathlib import Path

def require_real_project(case,path):
    path=Path(path)
    if not (path/'.git').exists():
        message='固定项目缺失，请先运行scripts/prepare_real_projects.py：'+str(path)
        if os.environ.get('C2S_REQUIRE_REAL_PROJECTS')=='1':case.fail(message)
        case.skipTest(message)
    return path
