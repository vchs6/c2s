import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from scripts.issue_worker.pipeline import select_issue, plan_digest, staged_paths, check_patch, effective_state
from scripts.issue_worker.core import fingerprint


class API:
    def __init__(self, role='write', comments=()): self.role, self.notes = role, comments
    def permission(self, login): return self.role
    def comments(self, number): return self.notes


class PipelineTests(unittest.TestCase):
    def test_scan_skips_pr_bot_and_readonly_and_keeps_backlog(self):
        issue = dict(number=3, title='task', body='', user=dict(login='human', type='User'))
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(select_issue([dict(issue, pull_request={})], API(), Path(folder), True))
            self.assertIsNone(select_issue([dict(issue, user=dict(login='bot', type='Bot'))], API(), Path(folder), True))
            self.assertIsNone(select_issue([issue], API('read'), Path(folder), True))
            self.assertEqual(select_issue([issue], API(), Path(folder), True)['issue']['number'], 3)
    def test_unauthorized_comment_cannot_approve(self):
        issue = dict(number=3, title='task', body='### 工作类型\n\nfeature', user=dict(login='human', type='User'))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state_path = root/'docs/development/issues/3/state.json'; state_path.parent.mkdir(parents=True)
            from scripts.issue_worker.core import approval_token
            token = approval_token(fingerprint(issue), plan_digest(root, []))
            state_path.write_text(json.dumps(dict(input_hash=fingerprint(issue), status='awaiting-decision', phase='plan', plan_paths=[], plan_digest=plan_digest(root, []), approval_token=token)))
            class RestrictedAPI(API):
                def permission(self, login): return 'write' if login == 'human' else 'read'
            comments = [dict(id=2, body='/c2s approve '+token, user=dict(login='stranger', type='User'))]
            self.assertIsNone(select_issue([issue], RestrictedAPI(comments=comments), root, True))
    def test_plan_digest_detects_missing_and_edited_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'plan.md').write_text('before')
            before=plan_digest(root, ['plan.md']); (root/'plan.md').write_text('after')
            self.assertNotEqual(before, plan_digest(root, ['plan.md']))
            (root/'plan.md').unlink()
            self.assertNotEqual(before, plan_digest(root, ['plan.md']))
    def test_real_git_patch_detects_symlink_and_forbidden_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            def git(*args): return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True)
            git('init','-q'); git('config','user.email','test@example.com'); git('config','user.name','test')
            (root/'seed').write_text('seed'); git('add','.'); git('commit','-qm','seed')
            (root/'src').mkdir(); (root/'src/a.py').write_text('pass\n'); git('add','.')
            self.assertEqual(staged_paths(root), ['src/a.py'])
            self.assertTrue(check_patch(root, 'apply', 3))
            (root/'src/link.py').symlink_to('../seed'); git('add','.')
            self.assertFalse(check_patch(root, 'apply', 3))
            git('reset','-q'); (root/'AGENTS.md').write_text('tamper'); git('add','AGENTS.md')
            self.assertFalse(check_patch(root, 'apply', 3))

    def test_rename_cannot_remove_trusted_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            def git(*args): return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True)
            git('init', '-q'); git('config', 'user.email', 'test@example.com'); git('config', 'user.name', 'test')
            (root/'scripts').mkdir(); (root/'scripts/trusted.py').write_text('trusted source\n')
            git('add', '.'); git('commit', '-qm', 'base'); (root/'src').mkdir()
            git('mv', 'scripts/trusted.py', 'src/moved.py')
            self.assertFalse(check_patch(root, 'apply', 7))

    def test_new_file_in_planned_change_invalidates_digest(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); change = root/'openspec/changes/issue-7-plan'; change.mkdir(parents=True)
            (change/'proposal.md').write_text('plan')
            paths = ['openspec/changes/issue-7-plan/proposal.md']
            before = plan_digest(root, paths)
            (change/'new-spec.md').write_text('new requirement')
            self.assertNotEqual(before, plan_digest(root, paths))
    def test_failed_publish_guard_survives_unwritable_main(self):
        state = dict(input_hash='hash', status='blocked', reason='publication-failed', updated_at='2026-11-01T02:00:00')
        comment = dict(user=dict(login='github-actions[bot]', type='Bot'), body='<!-- c2s-worker -->\n<!-- c2s-state: '+json.dumps(state)+' -->')
        self.assertEqual(effective_state(None, [comment]), state)
        self.assertEqual(effective_state(dict(status='awaiting-decision', updated_at='2026-11-01T01:00:00'), [comment]), state)
        comment['user'] = dict(login='stranger', type='User')
        self.assertIsNone(effective_state(None, [comment]))

if __name__ == '__main__': unittest.main()
