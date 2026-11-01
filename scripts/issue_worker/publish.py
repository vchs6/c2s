"""Trusted publisher: never executes generated code and never force-pushes."""
import datetime
import os
import subprocess
from pathlib import Path
from .core import approval_token, fingerprint, validate_result
from .pipeline import check_patch, git, load_json, plan_digest, planning_paths, save_json, staged_paths


def verify_candidate(folder, context):
    verified = load_json(folder/'verified.json')
    if not verified:
        return {'status': 'blocked', 'reason': 'missing-agent-output'}, None
    verdict = validate_result(verified.get('result'), context['phase'], verified.get('checks') is True)
    if verdict['status'] == 'completed':
        review = load_json(folder/'review.json', {})
        if review.get('verdict') != 'approved':
            return {'status': 'blocked', 'reason': 'missing-or-rejected-review'}, verified
    return verdict, verified


def _publish(api, context, model_ok):
    root, folder = Path.cwd(), Path('.issue-runtime/agent')
    number, phase = context['issue']['number'], context['phase']
    current = api.request(f'/issues/{number}')
    if current['state'] != 'open' or fingerprint(current) != context['input_hash']:
        print('Issue changed or closed; discarded stale candidate; start the selected Issue manually again.')
        return
    if api.request('/git/ref/heads/main')['object']['sha'] != context['base_sha']:
        print('main changed; discarded stale candidate; start the selected Issue manually again.')
        return
    if phase == 'blocked':
        verdict = dict(status='blocked', reason=context['reason'])
    elif phase == 'smoke':
        from .runner import checks
        validations = checks()
        passed = all(item['code'] == 0 for item in validations)
        verdict = dict(status='completed' if passed else 'blocked', reason=None if passed else 'validation-failed')
        folder.mkdir(parents=True, exist_ok=True)
        save_json(folder/'smoke.json', dict(mode='deterministic-smoke', model_called=False, validations=validations))
    else:
        verdict, verified = verify_candidate(folder, context)
        if not model_ok:
            verdict = dict(status='blocked', reason='model-job-failed')
        if verdict['status'] != 'blocked':
            patch = folder/'changes.patch'
            if not patch.exists() or not patch.stat().st_size:
                verdict = dict(status='blocked', reason='empty-patch')
            else:
                subprocess.run(['git', 'apply', '--index', '--binary', str(patch)], check=True)
                if not check_patch(root, phase, number, change_name=context.get('change_name')):
                    # Baseline is a fresh publisher checkout; discard only this generated index/worktree.
                    git(root, 'reset', '--hard', context['base_sha'])
                    verdict = dict(status='blocked', reason='forbidden-path-or-mode')
    generated = staged_paths(root)
    # A feature plan must contain the complete planning contract, not just a report.
    if verdict['status'] == 'awaiting-decision' and context['kind'] in {'plan', 'feature', 'implement'}:
        proposals = [root/'openspec/changes'/context['change_name']/'proposal.md'] if context.get('change_name') else list(root.glob(f'openspec/changes/issue-{number}-*/proposal.md'))
        complete = any(p.is_file() and (p.parent/'design.md').is_file() and (p.parent/'tasks.md').is_file() and list((p.parent/'specs').rglob('spec.md')) for p in proposals)
        if not complete:
            git(root, 'reset', '--hard', context['base_sha'])
            generated = []
            verdict = dict(status='blocked', reason='incomplete-planning-artifacts')
    state = dict(change_name=context.get('change_name'), invocation=context.get('invocation'), implementation_approved=False, input_hash=context['input_hash'], phase=phase, kind=context['kind'],
                 last_retry_id=context.get('retry_id'), resume_phase=context.get('resume_phase'), **verdict,
                 run_url=f"https://github.com/{api.repo}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
                 updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    if phase == 'blocked' and context.get('resume_phase') == 'apply':
        prior = context.get('prior') or {}
        for key in ('plan_paths', 'plan_digest', 'approval_token'):
            if key in prior:
                state[key] = prior[key]
    if state['status'] == 'awaiting-decision':
        state['plan_paths'] = planning_paths(root, generated, (context.get('prior') or {}).get('plan_paths', []), context.get('change_name'))
        state['plan_digest'] = plan_digest(root, state['plan_paths'])
        state['approval_token'] = approval_token(state['input_hash'], state['plan_digest'])
    prior = context.get('prior') or {}
    if prior.get('input_hash') == state['input_hash'] and 'scheme_decision' in prior:
        state['scheme_decision'] = prior['scheme_decision']
    state['implementation_approved'] = False
    record = root/f'docs/development/reviews/issues/{number}/runs'/os.environ['GITHUB_RUN_ID']
    record.mkdir(parents=True, exist_ok=True)
    # Copy only fixed output names as data, never executable scripts or worker context.
    for name in ('round1-proposer.md', 'round1-challenger.md', 'round2-proposer.md', 'round2-challenger.md',
                 'judge.md', 'review.json', 'work.json', 'verified.json', 'smoke.json'):
        source = folder/name
        if source.is_file() and not source.is_symlink():
            (record/name).write_bytes(source.read_bytes())
    save_json(record/'outcome.json', state)
    save_json(root/f'docs/development/issues/{number}/state.json', state)
    git(root, 'add', '-A')
    git(root, 'config', 'user.name', 'c2s-issue-worker[bot]')
    git(root, 'config', 'user.email', 'c2s-issue-worker[bot]@users.noreply.github.com')
    git(root, 'commit', '-m', f"chore(issue-{number}): {phase} {state['status']}")
    # Recheck inputs immediately before ordinary fast-forward push.
    latest = api.request(f'/issues/{number}')
    if latest['state'] != 'open' or fingerprint(latest) != context['input_hash']:
        print('Issue changed before push; candidate discarded.')
        return
    git(root, 'push', 'origin', 'HEAD:main')
    api.feedback(number, state)


def publish(api, context, model_ok):
    if not context or context.get('phase') not in {'plan', 'smoke', 'blocked'}:
        raise ValueError('planning-only publisher context required')
    try:
        _publish(api, context, model_ok)
    except Exception:
        # main itself can be unwritable: persist the retry guard in the Issue, not that branch.
        state = dict(input_hash=context['input_hash'], phase=context['phase'], kind=context['kind'],
                     status='blocked', reason='publication-failed', last_retry_id=context.get('retry_id'),
                     run_url=f"https://github.com/{api.repo}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
                     updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        api.feedback(context['issue']['number'], state)
        raise
