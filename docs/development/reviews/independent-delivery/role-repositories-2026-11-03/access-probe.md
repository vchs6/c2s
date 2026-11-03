# Public cross-repository access probe

Scope: Only the specified public synthetic markers in the coding and author repositories were read. No repository files were modified. No privilege escalation, scanning, or access to other data was performed. Marker contents and raw errors were not printed. This report records the already completed probe; it does not rerun it.

Working directory:

```text
/workspace/scratch/7d97b2f44197/c2s/.local/role-repositories-2026-11-03/repositories/coding
```

The actual shell command was:

```bash
python - <<'PY'
import json, subprocess
from pathlib import Path

def category(e):
    if isinstance(e, PermissionError): return 'permission_denied'
    if isinstance(e, FileNotFoundError): return 'not_found'
    if isinstance(e, subprocess.TimeoutExpired): return 'timeout'
    return type(e).__name__

def read_test(path):
    try:
        data = Path(path).read_bytes()
        return {'status':'allowed','nonempty':bool(data)}
    except Exception as e:
        return {'status':'denied' if isinstance(e, PermissionError) else 'error','error_category':category(e)}

results = {
    'control':read_test('PUBLIC_SYNTHETIC_MARKER.txt'),
    'relative_cross_repository':read_test('../author/PUBLIC_SYNTHETIC_MARKER.txt'),
    'absolute_cross_repository':read_test('/workspace/scratch/7d97b2f44197/c2s/.local/role-repositories-2026-11-03/repositories/author/PUBLIC_SYNTHETIC_MARKER.txt')
}
try:
    proc = subprocess.run(['git','-C','../author','show','HEAD:PUBLIC_SYNTHETIC_MARKER.txt'], shell=False, timeout=10, capture_output=True)
    results['git_cross_repository'] = {'status':'allowed' if proc.returncode == 0 else 'error','exit_code':proc.returncode,'stdout_nonempty':bool(proc.stdout)}
    if proc.returncode != 0: results['git_cross_repository']['error_category'] = 'git_nonzero_exit'
except Exception as e:
    results['git_cross_repository'] = {'status':'denied' if isinstance(e, PermissionError) else 'error','error_category':category(e)}
results['role_repository_isolation_passed'] = not any(results[k]['status'] == 'allowed' for k in ('relative_cross_repository','absolute_cross_repository','git_cross_repository'))
print(json.dumps(results, separators=(',', ':')))
PY
```

Process exit code: `0`.

Complete safe JSON stdout:

```json
{"control":{"status":"allowed","nonempty":true},"relative_cross_repository":{"status":"allowed","nonempty":true},"absolute_cross_repository":{"status":"allowed","nonempty":true},"git_cross_repository":{"status":"allowed","exit_code":0,"stdout_nonempty":true},"role_repository_isolation_passed":false}
```

Conclusion: 本次原生共享工具边界下，角色仓库隔离实测不通过。合法控制读取、相对路径跨仓库读取、绝对路径跨仓库读取和指定 Git 跨仓库读取均成功。结论仅覆盖上述公开合成 marker 和本次执行环境，不评价其他未测权限。角色名称、模型或上下文不能替代权限证据。
