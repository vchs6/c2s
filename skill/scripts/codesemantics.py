"""从Skill自身位置运行查询，独立于调用者工作目录。"""
import os
from pathlib import Path
import sys
sys.dont_write_bytecode=True

ROOT=Path(__file__).resolve().parents[1]
environment=ROOT/'.venv'
python=environment/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
if python.is_file() and Path(sys.prefix).resolve()!=environment.resolve():
    os.execv(str(python),[str(python),str(Path(__file__).resolve()),*sys.argv[1:]])
sys.path[:0]=[str(ROOT/'runtime/src'),str(ROOT/'runtime/skill/src')]
try:
    from codesemantics.__main__ import main
except ImportError:
    raise SystemExit('运行依赖未就绪；请执行安装程序准备独立Python环境。')
if __name__=='__main__':raise SystemExit(main())
