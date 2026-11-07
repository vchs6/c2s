import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from c2s_skill.__main__ import main


class AlgorithmCliTests(unittest.TestCase):
    def test_entities_command_constructs_and_queries_entity_archive(self):
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as data:
            root = Path(temporary)
            store = Path(data) / "entities.sqlite"
            (root / "main.py").write_text("def choose(flag):\n    return flag\n", encoding="utf-8")
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = main(["entities", "--root", str(root), "--select", "entities",
                               "--store", str(store), "--format", "json"])
            self.assertEqual(status, 0, errors.getvalue())
            result = json.loads(output.getvalue())
            self.assertEqual(result["status"], "obtained")
            self.assertTrue(result["members"])
            self.assertEqual(result["constructionStatus"], "constructed")

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

    def test_cli_can_return_a_valid_semantic_fact_bundle_for_one_algorithm(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "main.py").write_text(
                "def choose(flag):\n    if flag:\n        return 1\n    return 0\n", encoding="utf-8")
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = main(["algorithm", "--root", str(root), "--source", "main.py",
                               "--function", "choose", "--semantic-facts"])
            self.assertEqual(status, 0, errors.getvalue())
            result = json.loads(output.getvalue())
            bundle = result["semantic_fact_bundle"]
            self.assertEqual(bundle["profile"], "semantic-fact-model-1")
            self.assertTrue(any(fact["predicate"] == "behavior.control_edge" for fact in bundle["facts"]))
            self.assertEqual(result["semantic_validation"]["valid"], True)

    def test_cli_persists_and_reads_back_algorithm_full_profile(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            source = root / "main.py"
            source.write_text("def choose(flag):\n    if flag:\n        return 1\n    return 0\n", encoding="utf-8")
            database = Path(temporary) / "semantic.sqlite"
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = main(["algorithm", "--root", str(root), "--source", "main.py",
                    "--function", "choose", "--semantic-facts", "--store", str(database)])
            self.assertEqual(status, 0, errors.getvalue())
            response = json.loads(output.getvalue())
            self.assertEqual(response["semantic_store"]["state"], "stored")
            self.assertTrue(response["semantic_fact_bundle"]["facts"])
            self.assertEqual(response["semantic_fact_bundle"]["coverage"][0]["selector"],
                "algorithm:" + response["algorithm"]["algorithm_id"])

    def test_cli_parses_code_review_graph_json_for_source_mapped_call_facts(self):
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as output_dir:
            root = Path(temporary)
            (root / "src").mkdir()
            (root / "src/run.py").write_text("def run():\n    parse()\n", encoding="utf-8")
            (root / "src/parse.py").write_text("def parse():\n    return 1\n", encoding="utf-8")
            graph_output = Path(output_dir) / "graph.json"
            graph_output.write_text(json.dumps({
                "status": "ok", "pattern": "callees_of", "target": "run",
                "result_count": 1, "results_omitted": 0,
                "results": [{"kind": "Function", "name": "parse", "qualified_name": "parse",
                             "file_path": "src/parse.py", "line_start": 1, "line_end": 2,
                             "call_site": {"line": 2, "file": "src/run.py"}}],
                "edges": [{"source": "run", "target": "parse"}],
            }), encoding="utf-8")
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = main(["algorithm", "--root", str(root), "--source", "src/run.py",
                               "--function", "run", "--semantic-facts", "--graph-output",
                               str(graph_output), "--graph-version", "2.3.9"])

            self.assertEqual(status, 2, errors.getvalue())
            result = json.loads(output.getvalue())
            bundle = result["semantic_fact_bundle"]
            self.assertTrue(any(fact["predicate"] == "behavior.calls" for fact in bundle["facts"]))
            self.assertIn("GRAPH_INDEX_FRESHNESS_UNVERIFIED",
                          {item["code"] for item in bundle["coverage"][0]["diagnostics"]})
            self.assertTrue(result["semantic_validation"]["valid"], result["semantic_validation"]["diagnostics"])

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

    def test_cli_all_functions_traverses_python_and_rust_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "main.py").write_text("def alpha(): return 1\ndef beta(): return 2\n", encoding="utf-8")
            (root / "lib.rs").write_text("fn gamma() -> i32 { 3 }\n", encoding="utf-8")
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = main(["algorithm", "--root", str(root), "--all-functions"])
            self.assertEqual(status, 2, errors.getvalue())
            result = json.loads(output.getvalue())
            self.assertEqual(result["coverage"]["discovered_functions"], 3)
            self.assertEqual(result["coverage"]["analyzed_functions"], 3)
            self.assertEqual({item["function"] for item in result["algorithms"]}, {"alpha", "beta", "gamma"})
            self.assertTrue(all(item["algorithm"]["omissions"] for item in result["algorithms"]))
            self.assertFalse(result["complete"])

    def test_cli_all_functions_reports_unhandled_project_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "main.py").write_text("def run(): return 1\n", encoding="utf-8")
            (root / "notes.md").write_text("not parsed as source\n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                status = main(["algorithm", "--root", str(root), "--all-functions"])
            result = json.loads(output.getvalue())
            self.assertEqual(status, 2)
            self.assertEqual(result["coverage"]["unhandled_paths"], 1)
            self.assertIn({"path": "notes.md", "reason": "UNHANDLED_PROJECT_PATH",
                           "state": "readable", "diagnostic": None}, result["gaps"])

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

    def test_cli_reports_malformed_python_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "broken.py").write_text("def broken(:\n", encoding="utf-8")
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = main(["algorithm", "--root", str(root), "--source", "broken.py",
                               "--function", "broken"])
            self.assertEqual(status, 64)
            self.assertEqual(output.getvalue(), "")
            self.assertIn("invalid Python syntax", errors.getvalue())
            self.assertNotIn("Traceback", errors.getvalue())

    def test_query_mode_still_requires_exactly_one_query_form(self):
        with tempfile.TemporaryDirectory() as temporary:
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = main(["query", "--root", temporary])
            self.assertEqual(status, 64)

    def test_query_mode_rejects_algorithm_project_scan_flag(self):
        with tempfile.TemporaryDirectory() as temporary:
            errors = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(errors):
                status = main(["query", "--root", temporary, "--all-functions"])
            self.assertEqual(status, 64)
            self.assertIn("only valid for algorithm requests", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
