"""Usage: python3 -m scripts.issue_worker prepare|model|publish."""
import os
import sys
from pathlib import Path
from .github import GitHub
from .pipeline import git, load_json, save_json, select_issue


def main():
    command = sys.argv[1]
    if command == 'model':
        from .runner import run
        run()
        return
    api = GitHub()
    if command == 'prepare':
        issues = api.pages('/issues?state=open&sort=created&direction=asc')
        # Reconcile feedback after a successful state commit even if prior label/comment API failed.
        for issue in issues:
            state = load_json(Path(f"docs/development/issues/{issue['number']}/state.json"))
            if state and 'pull_request' not in issue:
                from .core import fingerprint
                if state['input_hash'] == fingerprint(issue):
                    from .pipeline import effective_state
                    latest = effective_state(state, api.comments(issue['number']))
                    api.feedback(issue['number'], latest)
        context = select_issue(issues, api, Path.cwd(), os.environ.get('HAS_MODEL_KEY') == 'true')
        if context:
            context['base_sha'] = git(Path.cwd(), 'rev-parse', 'HEAD').decode().strip()
            save_json('.issue-runtime/control/context.json', context)
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write('selected=' + ('true' if context else 'false') + '\n')
            output.write('phase=' + (context['phase'] if context else 'none') + '\n')
            output.write('base_sha=' + (context['base_sha'] if context else '') + '\n')
    elif command == 'publish':
        from .publish import publish
        publish(api, load_json('.issue-runtime/control/context.json'), os.environ.get('MODEL_OK') == 'true')
    else:
        raise SystemExit('Expected prepare, model or publish')


if __name__ == '__main__': main()
