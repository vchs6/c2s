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
        if len(parts) >= 4 and parts[:2] == ('openspec', 'changes') :
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


def check_patch(root, phase, number, change_name=None):
    if not allowed_paths(staged_paths(root), phase, number, change_name=change_name):
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


def select_manual_issue(issue, api, root, has_key, *, actor, operation='plan', change_name=None):
    """A manual invocation selects one item; comments never authorize implementation."""
    if operation not in {'plan', 'smoke'}:
        raise ValueError('manual planning-only operation required')
    if not actor or not has_write(api.permission(actor)):
        raise ValueError('manual invocation requires maintainer permission')
    if ('pull_request' in issue or issue.get('state') != 'open'
            or not human(issue.get('user', {}))
            or not has_write(api.permission(issue['user']['login']))):
        raise ValueError('manual issue must be open and maintainer-authorized')
    number = issue['number']
    if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
        raise ValueError('manual issue number must be positive')
    prior = load_json(Path(root)/f'docs/development/issues/{number}/state.json')
    name = change_name or (prior or {}).get('change_name') or f'issue-{number}-planning'
    if not re.fullmatch(r'[a-z][a-z0-9-]*', name):
        raise ValueError('invalid manual OpenSpec change name')
    phase = 'smoke' if operation == 'smoke' else 'plan'
    reason = None
    if phase == 'plan' and not has_key:
        phase, reason = 'blocked', 'missing-model-key'
    return dict(issue=issue, kind='smoke' if operation == 'smoke' else 'plan',
                phase=phase, reason=reason, resume_phase='plan' if reason else None,
                input_hash=fingerprint(issue), prior=prior, retry_id=(prior or {}).get('last_retry_id'),
                change_name=name, invocation='manual', implementation_approved=False)


def planning_paths(root, generated, prior_paths, change_name=None):
    paths = set(generated) | set(prior_paths)
    if change_name:
        if not re.fullmatch(r'[a-z][a-z0-9-]*', change_name):
            raise ValueError('invalid planning change name')
        root = Path(root).resolve()
        directory = root/'openspec/changes'/change_name
        if not directory.resolve().is_relative_to(root):
            raise ValueError('planning directory escapes repository')
        paths.update(str(p.relative_to(root)) for p in directory.rglob('*') if p.is_file() or p.is_symlink())
    return sorted(paths)


def planning_complete(directory):
    """Honor canonical OpenSpec skip_specs without inventing a product capability."""
    directory = Path(directory)
    if not all((directory/name).is_file() for name in ('proposal.md', 'design.md', 'tasks.md')):
        return False
    if any((directory/'specs').rglob('spec.md')):
        return True
    marker = directory/'.openspec.yaml'
    return marker.is_file() and bool(re.search(r'^skip_specs:[ \t]+true[ \t]*(?:#.*)?$', marker.read_text(), re.M))
