"""Manual planning entry; Issue events and approval comments never start work."""
import os
import re
import sys
from pathlib import Path
from .github import GitHub
from .pipeline import git, load_json, save_json, select_manual_issue


def main():
    command = sys.argv[1]
    if command == 'model':
        from .runner import run
        run()
        return
    if command == 'prepare':
        if os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch':
            raise ValueError('manual workflow_dispatch required')
        number = os.environ.get('C2S_ISSUE_NUMBER', '')
        operation = os.environ.get('C2S_OPERATION', 'plan')
        change_name = os.environ.get('C2S_CHANGE_NAME') or None
        if not re.fullmatch(r'[1-9][0-9]*', number):
            raise ValueError('manual positive issue number required')
        if operation not in {'plan', 'smoke'}:
            raise ValueError('manual planning-only operation required')
        if change_name and not re.fullmatch(r'[a-z][a-z0-9-]*', change_name):
            raise ValueError('invalid manual OpenSpec change name')
        api = GitHub()
        issue = api.request(f'/issues/{int(number)}')
        context = select_manual_issue(issue, api, Path.cwd(), os.environ.get('HAS_MODEL_KEY') == 'true',
            actor=os.environ.get('GITHUB_ACTOR'), operation=operation, change_name=change_name)
        context['base_sha'] = git(Path.cwd(), 'rev-parse', 'HEAD').decode().strip()
        save_json('.issue-runtime/control/context.json', context)
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write('selected=true\n')
            output.write('phase=' + context['phase'] + '\n')
            output.write('base_sha=' + context['base_sha'] + '\n')
    elif command == 'publish':
        from .publish import publish
        publish(GitHub(), load_json('.issue-runtime/control/context.json'), os.environ.get('MODEL_OK') == 'true')
    else:
        raise SystemExit('Expected prepare, model or publish')


if __name__ == '__main__':
    main()
