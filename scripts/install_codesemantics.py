"""部署codesemantics标准Skill及独立运行环境。"""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
base=Path(__file__).resolve().parent
sys.path[:0]=[str(base/'scripts'),str(base)]
from codesemantics_release import main_install
if __name__=='__main__':raise SystemExit(main_install())
