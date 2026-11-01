"""Manual entry and planning-only boundaries; no network or model calls."""
import importlib
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.issue_worker import core, pipeline


class ManualPlanningTests(unittest.TestCase):
    def test_issue_events_rejected_before_api(self):
        cli = importlib.import_module('scripts.issue_worker.__main__')
        with tempfile.TemporaryDirectory() as folder:
            for event in ('issues', 'issue_comment', 'schedule', 'push'):
                with self.subTest(event=event), patch.object(cli, 'GitHub') as api, patch.dict(os.environ, {
                    'GITHUB_EVENT_NAME': event, 'GITHUB_OUTPUT': str(Path(folder)/'out'),
                    'C2S_ISSUE_NUMBER': '7', 'C2S_OPERATION': 'plan', 'GITHUB_ACTOR': 'maintainer',
                }), patch('sys.argv', ['worker', 'prepare']):
                    api.return_value.pages.return_value = []
                    with self.assertRaisesRegex(ValueError, 'manual'):
                        cli.main()
                    api.assert_not_called()

    def test_dispatch_requires_explicit_positive_issue(self):
        cli = importlib.import_module('scripts.issue_worker.__main__')
        with tempfile.TemporaryDirectory() as folder:
            for number in ('', '0', '-1', 'all', '1/../../2'):
                with self.subTest(number=number), patch.object(cli, 'GitHub') as api, patch.dict(os.environ, {
                    'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_OUTPUT': str(Path(folder)/'out'),
                    'C2S_ISSUE_NUMBER': number, 'C2S_OPERATION': 'plan', 'GITHUB_ACTOR': 'maintainer',
                }), patch('sys.argv', ['worker', 'prepare']):
                    api.return_value.pages.return_value = []
                    with self.assertRaises(ValueError):
                        cli.main()
                    api.assert_not_called()

    def test_worker_has_only_explicit_dispatch_trigger(self):
        text = Path('.github/workflows/issue-worker.yml').read_text()
        events = text.split('\non:', 1)[1].split('\nconcurrency:', 1)[0]
        self.assertEqual(re.findall(r'^  ([a-z_]+):', events, re.M), ['workflow_dispatch'])
        self.assertIn('C2S_ISSUE_NUMBER:', text)
        self.assertNotIn("outputs.phase == 'apply'", text)

    def test_manual_plan_ignores_old_implementation_token(self):
        select = getattr(pipeline, 'select_manual_issue', None)
        self.assertTrue(callable(select), 'manual selector must exist')
        issue = dict(number=7, title='task', body='### 工作类型\n\nimplement', state='open', user=dict(login='owner', type='User'))
        class API:
            def permission(self, login): return 'write'
            def comments(self, number): raise AssertionError('comments must not select work')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state = root/'docs/development/issues/7/state.json'; state.parent.mkdir(parents=True)
            state.write_text(json.dumps(dict(status='awaiting-decision', approval_token='approved', change_name='existing-model')))
            context = select(issue, API(), root, True, actor='maintainer', operation='plan')
            self.assertEqual(context['phase'], 'plan')
            self.assertEqual(context['change_name'], 'existing-model')
            self.assertFalse(context['implementation_approved'])
            self.assertEqual(select(issue, API(), root, True, actor='maintainer', operation='smoke')['phase'], 'smoke')
            with self.assertRaises(ValueError):
                select(issue, API(), root, True, actor='maintainer', operation='apply')

    def test_manual_selector_checks_author_and_invoker(self):
        select = getattr(pipeline, 'select_manual_issue', None)
        self.assertTrue(callable(select), 'manual selector must exist')
        issue = dict(number=7, title='task', body='', state='open', user=dict(login='owner', type='User'))
        class API:
            def permission(self, login): return 'read' if login == 'reader' else 'write'
        with tempfile.TemporaryDirectory() as folder:
            for candidate, actor in [(issue, 'reader'), (dict(issue, user=dict(login='reader', type='User')), 'maintainer'), (dict(issue, pull_request={}), 'maintainer')]:
                with self.assertRaises(ValueError):
                    select(candidate, API(), Path(folder), True, actor=actor)
            self.assertEqual(select(issue, API(), Path(folder), False, actor='maintainer')['reason'], 'missing-model-key')

    def test_existing_change_scoped_paths_and_digest(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); change=root/'openspec/changes/existing-model'; change.mkdir(parents=True)
            (change/'proposal.md').write_text('proposal')
            before=pipeline.plan_digest(root, ['openspec/changes/existing-model/proposal.md'])
            (change/'spec.md').write_text('new contract')
            self.assertNotEqual(before,pipeline.plan_digest(root, ['openspec/changes/existing-model/proposal.md']))
        self.assertTrue(core.allowed_paths(['openspec/changes/existing-model/specs/a/spec.md'], 'plan', 7, change_name='existing-model'))
        self.assertFalse(core.allowed_paths(['openspec/changes/another-model/spec.md'], 'plan', 7, change_name='existing-model'))

    def test_planning_completeness_honors_explicit_skip_specs(self):
        complete = getattr(pipeline, 'planning_complete', None)
        self.assertTrue(callable(complete), 'OpenSpec planning completion helper must exist')
        with tempfile.TemporaryDirectory() as folder:
            change = Path(folder)
            for name in ('proposal.md', 'design.md', 'tasks.md'):
                (change/name).write_text('planning artifact')
            self.assertFalse(complete(change))
            (change/'.openspec.yaml').write_text('schema: spec-driven\nskip_specs: true\n')
            self.assertTrue(complete(change))
            (change/'proposal.md').unlink()
            self.assertFalse(complete(change))

    def test_selected_unchanged_change_is_in_manifest(self):
        selected = getattr(pipeline, 'planning_paths', None)
        self.assertTrue(callable(selected), 'selected-change manifest collector must exist')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); change = root/'openspec/changes/existing-model'; change.mkdir(parents=True)
            (change/'proposal.md').write_text('existing proposal')
            paths = selected(root, ['docs/development/reviews/issues/7/report.md'], [], 'existing-model')
            self.assertIn('openspec/changes/existing-model/proposal.md', paths)
            before = pipeline.plan_digest(root, paths)
            (change/'proposal.md').write_text('changed existing proposal')
            self.assertNotEqual(before, pipeline.plan_digest(root, paths))

    def test_model_and_publisher_reject_apply_before_side_effects(self):
        from scripts.issue_worker import runner, publish
        with patch.object(runner, 'load_json', return_value={'phase':'apply', 'issue':{'number':7}}), patch.object(runner.subprocess, 'run') as command, patch.object(runner, 'invoke', side_effect=ValueError('model reached')), patch.dict(os.environ, {'OPENAI_API_KEY':'test-only-non-secret'}):
            with self.assertRaisesRegex(ValueError, 'planning-only'):
                runner.run()
            command.assert_not_called()
        class API:
            def request(self, path): raise AssertionError('must reject before network')
            def feedback(self, *args): raise AssertionError('must reject before feedback')
        with self.assertRaisesRegex(ValueError, 'planning-only'):
            publish.publish(API(), {'phase':'apply'}, False)


if __name__ == '__main__':
    unittest.main()
