import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from c2s_skill.__main__ import main


class AlgorithmCliTests(unittest.TestCase):
    def test_cli_returns_source_bound_algorithm_and_gap_coverage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "main.py"
            source.write_text("def choose(flag):\n    if flag:\n        return 1\n    return 0\n", encoding="utf-8")
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = main(["algorithm", "--root", str(root), "--source", "main.py",
                               "--function", "choose", "--format", "json"])
            self.assertEqual(status, 0, errors.getvalue())
            result = json.loads(output.getvalue())
            self.assertEqual(result["algorithm"]["problem"], "choose")
            self.assertRegex(result["source_digest"], r"^[0-9a-f]{64}$")
            self.assertTrue(result["algorithm"]["omissions"])
            self.assertEqual(result["validation"]["diagnostics"], [])

    def test_cli_rejects_source_paths_that_escape_the_project_root(self):
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            root = Path(temporary)
            (Path(outside) / "main.py").write_text("def run(): return 1\n", encoding="utf-8")
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = main(["algorithm", "--root", str(root), "--source", str(Path(outside) / "main.py"),
                               "--function", "run", "--format", "json"])
            self.assertEqual(status, 64)
            self.assertIn("inside the analyzed project", errors.getvalue())

    def test_cli_uses_the_rust_frontend_for_rust_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "lib.rs").write_text("fn value() -> i32 { 1 }\n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                status = main(["algorithm", "--root", str(root), "--source", "lib.rs",
                               "--function", "value"])
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(output.getvalue())["algorithm"]["problem"], "value")

    def test_cli_rejects_symlinked_source_paths(self):
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            root, outside_root = Path(temporary), Path(outside)
            (outside_root / "main.py").write_text("def run(): return 1\n", encoding="utf-8")
            (root / "link.py").symlink_to(outside_root / "main.py")
            errors = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(errors):
                status = main(["algorithm", "--root", str(root), "--source", "link.py",
                               "--function", "run"])
            self.assertEqual(status, 64)
            self.assertIn("symlinks", errors.getvalue())

    def test_query_mode_still_requires_exactly_one_query_form(self):
        with tempfile.TemporaryDirectory() as temporary:
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = main(["query", "--root", temporary])
            self.assertEqual(status, 64)


if __name__ == "__main__":
    unittest.main()
