"""Queue selection and patch checks shared by runner and trusted publisher."""
import json
import re
import subprocess
from pathlib import Path
from .core import allowed_paths, choose_work, digest, fingerprint, has_write, work_kind


def git(root, *args, **kwargs):
    return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True, **kwargs).stdout


def load_json(path, default=None):
    return json.loads(Path(path).read_text()) if Path(path).exists() else default


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def plan_digest(root, paths):
    values = {}
    root = Path(root).resolve()
    manifest = set(paths)
    for name in paths:
        parts = Path(name).parts
        if len(parts) >= 4 and parts[:2] == ('openspec', 'changes') and parts[2].startswith('issue-'):
            directory = root.joinpath(*parts[:3])
            manifest.update(str(p.relative_to(root)) for p in directory.rglob('*') if p.is_file() or p.is_symlink())
    for name in sorted(manifest):
        path = root / name
        if not path.resolve().is_relative_to(root) or path.is_symlink():
            raise ValueError('Invalid plan path')
        values[name] = digest(path.read_text()) if path.is_file() else None
    return digest(values)


def human(user):
    return user.get('type') != 'Bot' and not user.get('login', '').endswith('[bot]')


def select_issue(issues, api, root, has_key):
    for issue in sorted(issues, key=lambda item: item['number']):
        if 'pull_request' in issue or not human(issue['user']) or not has_write(api.permission(issue['user']['login'])):
            continue
        number = issue['number']
        comments = api.comments(number)
        state = effective_state(load_json(root / f'docs/development/issues/{number}/state.json'), comments)
        tokens, retry_id = [], None
        if state:
            for comment in comments:
                body = comment.get('body', '').strip()
                if not re.fullmatch(r'/c2s (?:approve [a-f0-9]{24}|retry)', body):
                    continue
                if not human(comment['user']) or not has_write(api.permission(comment['user']['login'])):
                    continue
                if body == '/c2s retry':
                    retry_id = max(retry_id or 0, comment['id'])
                else:
                    tokens.append(body.split()[-1])
        artifact_digest = plan_digest(root, state.get('plan_paths', [])) if state else None
        work = choose_work(issue, state, has_key=has_key, retry_id=retry_id, approved_tokens=tokens, artifact_digest=artifact_digest)
        if work:
            return dict(work, issue=issue, kind=work_kind(issue), input_hash=fingerprint(issue), prior=state, retry_id=retry_id)
    return None


def staged_paths(root):
    return git(root, 'diff', '--cached', '--name-only', '--no-renames', '-z').decode().strip('\0').split('\0') if git(root, 'diff', '--cached', '--name-only', '--no-renames', '-z') else []


def check_patch(root, phase, number):
    if not allowed_paths(staged_paths(root), phase, number):
        return False
    # Reject executable modes, symlinks and submodules in generated output.
    for line in git(root, 'diff', '--cached', '--raw', '--no-abbrev').decode().splitlines():
        fields = line.split()
        if fields[1] not in {'100644', '000000'}:
            return False
    return True

def effective_state(state, comments):
    # If main rejects a push, a bot comment remains writable and prevents paid retry loops.
    for comment in comments:
        if comment.get('user', {}).get('login') != 'github-actions[bot]':
            continue
        match = re.search(r'<!-- c2s-state: (.+?) -->', comment.get('body', ''))
        if not match:
            continue
        try:
            fallback = json.loads(match.group(1))
        except (ValueError, TypeError):
            continue
        if fallback.get('status') == 'blocked' and fallback.get('reason') == 'publication-failed':
            if not state or fallback.get('updated_at', '') > state.get('updated_at', ''):
                state = fallback
    return state
