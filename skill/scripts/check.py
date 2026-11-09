"""核验Skill运行环境和一次本地查询，不发送网络请求。"""
import json
import os
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode=True
import tempfile
from importlib.metadata import version
ROOT=Path(__file__).resolve().parents[1]
python=ROOT/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
if python.is_file() and Path(sys.prefix).resolve()!=(ROOT/'.venv').resolve():
    os.execv(str(python),[str(python),str(Path(__file__).resolve())])
if sys.version_info[:2]!=(3,12) or sys.version_info.releaselevel!='final':raise SystemExit('需要正式版Python3.12')
import ast,tomllib,sqlite3,tree_sitter,tree_sitter_rust
with tempfile.TemporaryDirectory(prefix='codesemantics-check-') as temp:
    source=Path(temp)/'source';source.mkdir();(source/'sample.py').write_text('def run():\n return 1\n')
    result=subprocess.run([sys.executable,str(ROOT/'scripts/codesemantics.py'),'query','--root',str(source),
                           '--select','modules','--store',str(Path(temp)/'facts.sqlite')],capture_output=True,text=True,timeout=30)
    if result.returncode:raise SystemExit('基础查询未通过：'+result.stderr)
    data=json.loads(result.stdout)
    if not data['complete'] or len(data['items'])!=1:raise SystemExit('基础查询结果不符')
print(json.dumps({'valid':True,'python':sys.version.split()[0],
    'dependencies':{name:version(name) for name in ('jsonschema','tree-sitter','tree-sitter-rust')},
    'sqlite':sqlite3.sqlite_version,'basicQuery':'通过'},ensure_ascii=False))
