"""Public infrastructure checks; never product or private acceptance tests."""

import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "ci/acceptance/blind_delivery_probe.py"


class BlindDeliveryProbeTests(unittest.TestCase):
    def invoke(self, *arguments):
        environment = dict(os.environ, GITHUB_ACTIONS="false")
        return subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments],
                              capture_output=True, text=True, check=False, env=environment)

    def test_local_controls_execute_fixed_synthetic_acceptance_and_reject_mismatches(self):
        result = self.invoke("--local-controls")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertTrue(report["synthetic_only"])
        self.assertFalse(report["model_invoked"])
        self.assertFalse(report["development_ready"])
        self.assertFalse(report["container_repo_boundary_passed"])
        self.assertTrue(all(report["preparation_checks"].values()))
        self.assertTrue(report["acceptance_checks"]["matching_binding_passed"])
        self.assertTrue(report["acceptance_checks"]["wrong_answer_rejected"])
        self.assertTrue(report["acceptance_checks"]["contract_drift_rejected"])
        self.assertTrue(report["acceptance_checks"]["all_binding_mismatches_rejected"])
        self.assertTrue(report["acceptance_checks"]["controlled_report_only"])
        self.assertNotIn("PUBLIC_SYNTHETIC_RAW_DIAGNOSTIC", result.stdout)
        self.assertNotIn("expected_answer", result.stdout)

    def test_non_ci_worker_invocation_fails_closed_with_controlled_report(self):
        result = self.invoke("--role", "coding")
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["error"], "trusted_ci_required")
        self.assertFalse(report["development_ready"])
        self.assertFalse(report["model_invoked"])

    def test_invalid_arguments_do_not_echo_input(self):
        result = self.invoke("--role", "UNTRUSTED_ARGUMENT_MARKER")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("UNTRUSTED_ARGUMENT_MARKER", result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["error"], "invalid_arguments")

    def test_actual_author_contract_drift_rejects_before_candidate_execution(self):
        module = runpy.run_path(str(SCRIPT))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executed = root / "candidate-executed"
            for role in ("coding", "author"):
                for relative in module["boundary"].CONTRACTS:
                    path = root / role / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("public frozen contract\n")
            candidate = ("from pathlib import Path\nPath(" + repr(str(executed)) +
                         ").write_text('executed')\n"
                         "print('{\"answer\":42,\"diagnostic\":\"public\"}')\n")
            (root / "coding" / module["CANDIDATE"]).write_text(candidate)
            (root / "author" / module["SUITE"]).write_bytes(module["SUITE_BYTES"])
            expected = module["binding"](root, "1" * 40)
            contract = root / "author" / module["boundary"].CONTRACTS[0]
            contract.write_text("changed public contract\n")
            result = module["acceptance"](root, "1" * 40, expected, dict(expected))
            self.assertEqual(result["status"], "binding_mismatch")
            self.assertFalse(executed.exists())
            # Even freshly binding unequal contracts cannot authorize execution.
            unequal = module["binding"](root, "1" * 40)
            result = module["acceptance"](root, "1" * 40, unequal, dict(unequal))
            self.assertEqual(result["status"], "binding_mismatch")
            self.assertFalse(executed.exists())


if __name__ == "__main__":
    unittest.main()
