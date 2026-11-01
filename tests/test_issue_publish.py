import os
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from scripts.issue_worker.publish import verify_candidate, publish
from scripts.issue_worker.pipeline import git, save_json
from scripts.issue_worker.core import fingerprint
from unittest.mock import patch


class PublisherTests(unittest.TestCase):
    def test_missing_agent_output_blocks(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(verify_candidate(Path(folder), dict(phase='plan', issue=dict(number=1)))[0]['status'], 'blocked')
    def test_failure_never_accepts_patch(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            save_json(root/'verified.json', dict(checks=False, result=dict(status='completed', summary='claimed')))
            self.assertEqual(verify_candidate(root, dict(phase='apply', issue=dict(number=1)))[0]['status'], 'blocked')
    def test_apply_requires_independent_review(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            save_json(root/'verified.json', dict(checks=True, result=dict(status='completed', summary='claimed')))
            self.assertEqual(verify_candidate(root, dict(phase='apply', issue=dict(number=1)))[0]['reason'], 'missing-or-rejected-review')


class PublicationIntegrationTests(unittest.TestCase):
    def fixture(self, root):
        def run(*args): return git(root, *args)
        run('init', '-q'); run('config', 'user.name', 'test'); run('config', 'user.email', 'test@example.com')
        (root/'base').write_text('base'); run('add', '.'); run('commit', '-qm', 'base')
        sha = run('rev-parse', 'HEAD').decode().strip()
        issue = dict(number=7, title='test', body='body', state='open')
        context = dict(issue=issue, phase='blocked', kind='feature', input_hash=fingerprint(issue), base_sha=sha, reason='missing-model-key', resume_phase='plan')
        class API:
            repo='owner/test'
            def __init__(self): self.states=[]
            def request(self, path): return {'object': {'sha': sha}} if path.startswith('/git/') else issue
            def feedback(self, number, state): self.states.append(state)
        return context, API()

    def test_push_failure_records_issue_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); context, api=self.fixture(root)
            git(root, 'remote', 'add', 'origin', str(root/'nonexistent.git'))
            before=Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(os.environ, GITHUB_RUN_ID='100'):
                    with self.assertRaises(Exception): publish(api, context, False)
            finally: os.chdir(before)
            self.assertEqual(api.states[-1]['status'], 'blocked')
            self.assertEqual(api.states[-1]['reason'], 'publication-failed')

    def test_successful_plan_uses_real_git_push(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'repo'; root.mkdir(); context, api=self.fixture(root)
            bare=Path(folder)/'remote.git'; subprocess.run(['git','init','--bare','-q',str(bare)],check=True)
            git(root, 'remote', 'add', 'origin', str(bare))
            report=root/'docs/development/reviews/issues/7/report.md'; report.parent.mkdir(parents=True); report.write_text('discussion evidence\n')
            git(root, 'add', '.')
            data=git(root,'diff','--cached','--binary'); git(root,'reset','--hard',context['base_sha'])
            agent=root/'.issue-runtime/agent'; agent.mkdir(parents=True)
            (agent/'changes.patch').write_bytes(data)
            save_json(agent/'verified.json',dict(checks=True,result=dict(status='awaiting-decision',summary='discussion')))
            context.update(phase='plan',kind='discuss')
            # Runtime is normally ignored by the real repository's .gitignore.
            (root/'.git/info/exclude').write_text('.issue-runtime/\n')
            before=Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(os.environ,GITHUB_RUN_ID='101'): publish(api,context,True)
            finally: os.chdir(before)
            state=json.loads((root/'docs/development/issues/7/state.json').read_text())
            self.assertEqual(state['status'],'awaiting-decision')
            self.assertEqual(len(state['approval_token']),24)
            remote_sha=subprocess.run(['git','--git-dir',str(bare),'rev-parse','main'],check=True,capture_output=True,text=True).stdout.strip()
            self.assertEqual(remote_sha,git(root,'rev-parse','HEAD').decode().strip())
