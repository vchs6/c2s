"""同一入口执行公开契约、维护脚本和Skill测试。"""
import os
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join(str(root / part) for part in ('src', 'skill/src'))
    for suite in ('tests', 'skill/tests'):
        result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', suite, '-v'], cwd=root, env=env)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
