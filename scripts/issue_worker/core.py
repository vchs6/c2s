"""Deterministic Issue policy; no model or network authority."""
import hashlib
import json
import re
from pathlib import PurePosixPath


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def fingerprint(issue):
    return digest({key: issue.get(key) for key in ('number', 'title', 'body')})


def work_kind(issue):
    match = re.search(r'^### 工作类型\s*\n\s*(\w+)\s*(?:\n|$)', issue.get('body') or '', re.M)
    kind = match.group(1) if match else 'discuss'
    return kind if kind in {'plan', 'discuss', 'feature', 'implement', 'bug', 'smoke'} else 'discuss'


def has_write(permission):
    return permission in {'admin', 'maintain', 'write'}


def approval_token(input_hash, artifact_digest):
    return digest([input_hash, artifact_digest])[:24]


def choose_work(issue, state, *, has_key, retry_id=None, approved_tokens=(), artifact_digest=None):
    kind = work_kind(issue)
    phase = 'smoke' if kind == 'smoke' else 'apply' if kind == 'bug' else 'plan'
    same = state and state.get('input_hash') == fingerprint(issue)
    retry = retry_id is not None and (not state or retry_id != state.get('last_retry_id'))
    if same and not retry:
        if state.get('status') == 'awaiting-decision':
            if artifact_digest != state.get('plan_digest'):
                phase = 'plan'
            elif kind in {'feature', 'implement'} and state.get('approval_token') in approved_tokens:
                phase = 'apply'
            else:
                return None
        elif state.get('status') == 'blocked' and state.get('reason') == 'missing-model-key' and has_key:
            phase = state.get('resume_phase', phase)
            if phase == 'apply' and kind in {'feature', 'implement'}:
                if artifact_digest != state.get('plan_digest'):
                    phase = 'plan'
                elif state.get('approval_token') not in approved_tokens:
                    return None
        else:
            return None
    if phase != 'smoke' and not has_key:
        return {'phase': 'blocked', 'resume_phase': phase, 'reason': 'missing-model-key'}
    return {'phase': phase, 'reason': None}


def allowed_paths(paths, phase, number, change_name=None):
    if change_name is not None and not re.fullmatch(r"[a-z][a-z0-9-]*", change_name):
        return False
    for path in paths:
        parts = PurePosixPath(path).parts
        if not path or path.startswith('/') or '\\' in path or '..' in parts or '.git' in parts:
            return False
        if PurePosixPath(path).name in {'AGENTS.md', 'CLAUDE.md', 'GEMINI.md'}:
            return False
        # Executable project scripts are Python 3. Third-party tooling is never edited here.
        if PurePosixPath(path).suffix in {'.js', '.mjs', '.cjs', '.sh', '.bash', '.ps1'}:
            return False
        own = path.startswith(f'docs/development/reviews/issues/{number}/')
        change = (path.startswith(f'openspec/changes/{change_name}/') if change_name else path.startswith(f'openspec/changes/issue-{number}-')) and len(parts) >= 4
        product = phase == 'apply' and path.startswith(('src/', 'tests/', 'contracts/', 'docs/domain/'))
        if not (own or change or product):
            return False
    return True


def validate_result(result, phase, checks):
    if not checks:
        return {'status': 'blocked', 'reason': 'validation-failed'}
    if not isinstance(result, dict) or not isinstance(result.get('summary'), str):
        return {'status': 'blocked', 'reason': 'invalid-agent-result'}
    expected = 'awaiting-decision' if phase == 'plan' else 'completed'
    if result.get('status') not in {expected, 'blocked'}:
        return {'status': 'blocked', 'reason': 'invalid-agent-status'}
    return {'status': result['status'], 'reason': result.get('reason') or (None if result['status'] == expected else 'agent-blocked')}
