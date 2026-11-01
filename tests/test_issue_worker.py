import unittest
from scripts.issue_worker.core import (fingerprint, work_kind, has_write, approval_token,
    choose_work, allowed_paths, validate_result)

ISSUE = {"number": 7, "title": "work", "body": "### 工作类型\n\nfeature\n\n### 工作内容\n\nBuild it"}
OPTIONS = dict(has_key=True, retry_id=None, approved_tokens=[], artifact_digest="plan-v1")

class SchedulingTests(unittest.TestCase):
    def test_fingerprint_ignores_feedback_but_not_body(self):
        self.assertEqual(fingerprint(ISSUE), fingerprint(dict(ISSUE, updated_at="later", labels=["done"])))
        self.assertNotEqual(fingerprint(ISSUE), fingerprint(dict(ISSUE, body="edited")))
    def test_explicit_type_only(self):
        self.assertEqual(work_kind(ISSUE), "feature")
        self.assertEqual(work_kind(dict(ISSUE, body="please implement")), "discuss")
    def test_authorization(self):
        for permission in ("admin", "maintain", "write"):
            self.assertTrue(has_write(permission))
        for permission in ("triage", "read", "none", None):
            self.assertFalse(has_write(permission))
    def test_plan_and_missing_key(self):
        self.assertEqual(choose_work(ISSUE, None, **OPTIONS)["phase"], "plan")
        self.assertEqual(choose_work(ISSUE, None, **dict(OPTIONS, has_key=False))["reason"], "missing-model-key")
    def test_current_approval_only(self):
        token = approval_token(fingerprint(ISSUE), "plan-v1")
        state = dict(input_hash=fingerprint(ISSUE), status="awaiting-decision", phase="plan", approval_token=token, plan_digest="plan-v1")
        self.assertEqual(choose_work(ISSUE, state, **dict(OPTIONS, approved_tokens=[token]))["phase"], "apply")
        self.assertIsNone(choose_work(ISSUE, state, **OPTIONS))
        self.assertEqual(choose_work(ISSUE, state, **dict(OPTIONS, approved_tokens=[token], artifact_digest="changed"))["phase"], "plan")
        self.assertEqual(choose_work(dict(ISSUE, body="edited"), state, **dict(OPTIONS, approved_tokens=[token]))["phase"], "plan")
    def test_completed_and_retry(self):
        state = dict(input_hash=fingerprint(ISSUE), status="completed", last_retry_id=None)
        self.assertIsNone(choose_work(ISSUE, state, **OPTIONS))
        state.update(status="blocked", reason="validation-failed")
        self.assertIsNone(choose_work(ISSUE, state, **OPTIONS))
        self.assertEqual(choose_work(ISSUE, state, **dict(OPTIONS, retry_id=45))["phase"], "plan")
    def test_key_restores_and_smoke_needs_no_key(self):
        state = dict(input_hash=fingerprint(ISSUE), status="blocked", reason="missing-model-key")
        self.assertEqual(choose_work(ISSUE, state, **OPTIONS)["phase"], "plan")
        self.assertIsNone(choose_work(ISSUE, state, **dict(OPTIONS, has_key=False)))
        self.assertEqual(choose_work(dict(ISSUE, body="### 工作类型\n\nsmoke"), None, **dict(OPTIONS, has_key=False))["phase"], "smoke")
    def test_paths_enforce_phase_and_trusted_boundary(self):
        self.assertTrue(allowed_paths(["docs/development/reviews/issues/7/report.md", "openspec/changes/issue-7-plan/proposal.md"], "plan", 7))
        for path in ("src/a.py", "AGENTS.md", ".github/workflows/x.yml", "docs/development/issues/7/state.json", "../escape", "docs/development/reviews/issues/8/a.md"):
            self.assertFalse(allowed_paths([path], "plan", 7), path)
        self.assertTrue(allowed_paths(["src/a.py", "tests/test_a.py"], "apply", 7))
        for path in ("scripts/issue_worker/core.py", "src/link/../../AGENTS.md", "src/fix.js", "src/AGENTS.md"):
            self.assertFalse(allowed_paths([path], "apply", 7), path)
    def test_missing_key_resume_revalidates_plan(self):
        token = approval_token(fingerprint(ISSUE), 'plan-v1')
        state = dict(input_hash=fingerprint(ISSUE), status='blocked', reason='missing-model-key', resume_phase='apply',
                     plan_digest='plan-v1', approval_token=token)
        self.assertEqual(choose_work(ISSUE, state, **dict(OPTIONS, artifact_digest='edited', approved_tokens=[token]))['phase'], 'plan')
        self.assertIsNone(choose_work(ISSUE, state, **OPTIONS))
        self.assertEqual(choose_work(ISSUE, state, **dict(OPTIONS, approved_tokens=[token]))['phase'], 'apply')
    def test_result_cannot_self_certify(self):
        self.assertEqual(validate_result(dict(status="completed", summary="done"), "plan", True)["status"], "blocked")
        self.assertEqual(validate_result(dict(status="completed", summary="done"), "apply", False)["status"], "blocked")
        self.assertEqual(validate_result(dict(status="completed", summary="done"), "apply", True)["status"], "completed")
        self.assertEqual(validate_result(None, "apply", True)["status"], "blocked")

if __name__ == "__main__": unittest.main()
