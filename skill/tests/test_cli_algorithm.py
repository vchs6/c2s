import contextlib
import io
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from c2s_skill.__main__ import main as _main


def main(args):
    """本组历史协议断言显式验证v1兼容入口。"""
    return _main([*args, "--model-profile", "semantic-entity-model-1"])


class AlgorithmCliTests(unittest.TestCase):
    def test_workspace_metadata_is_stored_as_e1_project_claims_not_package_entities(self):
        cargo = Path(__file__).resolve().parents[2] / ".local/cargo/bin/cargo"
        if not cargo.is_file():
            self.skipTest("repository-local Cargo toolchain is unavailable")
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as data:
            root = Path(temporary)
            (root / "crates/a/src").mkdir(parents=True)
            (root / "pyproject.toml").write_text('[project]\nname = "sample-workspace"\n', encoding="utf-8")
            (root / "Cargo.toml").write_text('[workspace]\nmembers = ["crates/*"]\nresolver = "2"\n',
                                              encoding="utf-8")
            (root / "crates/a/Cargo.toml").write_text(
                '[package]\nname = "sample-member"\nversion = "0.1.0"\nedition = "2021"\n', encoding="utf-8")
            (root / "crates/a/src/lib.rs").write_text("pub fn value() -> u8 { 1 }\n", encoding="utf-8")
            database = Path(data) / "entities.sqlite"
            env = {"CARGO": str(cargo), "RUSTUP_HOME": str(cargo.parents[2] / "rustup"),
                   "CARGO_HOME": str(cargo.parents[1])}
            output, errors = io.StringIO(), io.StringIO()
            with patch.dict(os.environ, env), contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = main(["query", "--root", str(root), "--select", "workspace-members",
                               "--format", "json", "--store", str(database)])
            self.assertEqual(status, 0, errors.getvalue())
            response = json.loads(output.getvalue())
            self.assertEqual(len(response["facts"]), 1)
            output = io.StringIO()
            with patch.dict(os.environ, env), contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                status = main(["entities", "--root", str(root), "--select", "project",
                               "--format", "json", "--store", str(database)])
            self.assertEqual(status, 0)
            entity_response = json.loads(output.getvalue())
            project = entity_response["entity"]
            self.assertIn("E1", project["observationViews"])
            claims = [item for item in project["claims"] if item["predicate"] == "workspaceMemberPackage"]
            self.assertEqual([item["value"]["packageName"] for item in claims], ["sample-member"])
            self.assertTrue(all(item["claimStatus"] == "confirmed" for item in claims))
            workspace_coverage = [item for item in project["coverage"]
                                   if item["selector"] == "workspace-members"]
            self.assertTrue(workspace_coverage)
            self.assertTrue(all(item["status"] == "obtained" for item in workspace_coverage))
            self.assertFalse(any(item["name"] == "sample-member" for item in entity_response["members"]))

    def test_workspace_metadata_failure_is_stored_as_not_acquired_coverage(self):
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as data:
            root = Path(temporary)
            (root / "Cargo.toml").write_text('[workspace]\nmembers = []\n', encoding="utf-8")
            (root / "pyproject.toml").write_text('[project]\nname = "sample-workspace"\n', encoding="utf-8")
            database = Path(data) / "entities.sqlite"
            env = {"CARGO": ""}
            output, errors = io.StringIO(), io.StringIO()
            with patch.dict(os.environ, env), patch("c2s_skill.acquisition.shutil.which", return_value=None), \
                    contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = main(["query", "--root", str(root), "--select", "workspace-members",
                               "--format", "json", "--store", str(database)])
            self.assertEqual(status, 2)
            self.assertTrue(any("TOOL_UNAVAILABLE:cargo" in item["reason"]
                                for item in json.loads(output.getvalue())["gaps"]))
            output = io.StringIO()
            with patch.dict(os.environ, env), patch("c2s_skill.acquisition.shutil.which", return_value=None), \
                    contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                status = main(["entities", "--root", str(root), "--select", "project",
                               "--format", "json", "--store", str(database)])
            self.assertEqual(status, 0)
            response = json.loads(output.getvalue())
            self.assertTrue(any(item["selector"] == "workspace-members" and item["status"] == "not_acquired"
                                for item in response["entity"]["coverage"]))
            self.assertTrue(any(item["code"] == "WORKSPACE_METADATA_NOT_ACQUIRED"
                                for item in response["constructionDiagnostics"]))

    def test_workspace_metadata_can_anchor_a_virtual_workspace_project(self):
        cargo = Path(__file__).resolve().parents[2] / ".local/cargo/bin/cargo"
        if not cargo.is_file():
            self.skipTest("repository-local Cargo toolchain is unavailable")
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as data:
            root = Path(temporary)
            (root / "crates/a/src").mkdir(parents=True)
            (root / "Cargo.toml").write_text('[workspace]\nmembers = ["crates/*"]\nresolver = "2"\n',
                                              encoding="utf-8")
            (root / "crates/a/Cargo.toml").write_text(
                '[package]\nname = "virtual-member"\nversion = "0.1.0"\nedition = "2021"\n', encoding="utf-8")
            (root / "crates/a/src/lib.rs").write_text("pub fn value() -> u8 { 1 }\n", encoding="utf-8")
            database = Path(data) / "entities.sqlite"
            env = {"CARGO": str(cargo), "RUSTUP_HOME": str(cargo.parents[2] / "rustup"),
                   "CARGO_HOME": str(cargo.parents[1])}
            output = io.StringIO()
            with patch.dict(os.environ, env), contextlib.redirect_stdout(output), \
                    contextlib.redirect_stderr(io.StringIO()):
                status = main(["query", "--root", str(root), "--select", "workspace-members",
                               "--format", "json", "--store", str(database)])
            self.assertEqual(status, 0)
            output = io.StringIO()
            with patch.dict(os.environ, env), contextlib.redirect_stdout(output), \
                    contextlib.redirect_stderr(io.StringIO()):
                status = main(["entities", "--root", str(root), "--select", "project",
                               "--format", "json", "--store", str(database)])
            self.assertEqual(status, 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result["entity"]["ref"]["kind"], "Project")
            self.assertTrue(any(item["predicate"] == "workspaceMemberPackage"
                                and item["value"]["packageName"] == "virtual-member"
                                for item in result["entity"]["claims"]))

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

    def test_query_store_and_entities_command_share_the_same_entity_archive(self):
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as data:
            root = Path(temporary)
            store = Path(data) / "shared.sqlite"
            (root / "main.py").write_text("def choose(flag):\n    return flag\n", encoding="utf-8")
            first_output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(first_output), contextlib.redirect_stderr(errors):
                first_status = main(["query", "--root", str(root), "--select", "functions",
                                     "--store", str(store), "--format", "json"])
            second_output = io.StringIO()
            with contextlib.redirect_stdout(second_output), contextlib.redirect_stderr(errors):
                second_status = main(["entities", "--root", str(root), "--select", "entities",
                                      "--store", str(store), "--format", "json"])
            self.assertIn(first_status, (0, 2), errors.getvalue())
            self.assertIn(second_status, (0, 2), errors.getvalue())
            first = json.loads(first_output.getvalue())
            second = json.loads(second_output.getvalue())
            self.assertEqual(first["semantic_entity_store"]["scopeId"], second["scopeId"])
            self.assertEqual(second["constructionStatus"], "reused")

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

    def test_function_query_returns_rendered_pseudocode_for_python_and_rust(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "main.py").write_text(
                "def choose(flag):\n    \"\"\"Select a result.\"\"\"\n    if flag:\n        return 1\n    return 0\n", encoding="utf-8")
            (root / "lib.rs").write_text(
                "fn answer(flag: bool) -> i32 { if flag { return 1; } 0 }\n", encoding="utf-8")
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = main(["query", "--root", str(root), "--select", "function:choose",
                               "--format", "json"])
            self.assertEqual(status, 0, errors.getvalue())
            result = json.loads(output.getvalue())
            choose = next(item for item in result["pseudocode"] if item["function"] == "choose")
            self.assertIn("如果 flag", choose["text"])
            self.assertIn("返回 1", choose["text"])
            self.assertNotIn("Select a result", choose["text"])
            self.assertTrue(choose["evidence_refs"])
            self.assertFalse(choose["complete"])
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                status = main(["query", "--root", str(root), "--select", "function:answer",
                               "--format", "json"])
            self.assertEqual(status, 0)
            answer = next(item for item in json.loads(output.getvalue())["pseudocode"]
                          if item["function"] == "answer")
            self.assertIn("如果 flag", answer["text"])
            self.assertIn("返回 1", answer["text"])

    def test_pseudocode_preserves_all_lines_of_multiline_statements(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "main.py").write_text(
                "def render(items):\n    result = build(\n        items,\n        option=\"all\",\n    )\n    return result\n",
                encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                status = main(["query", "--root", str(root), "--select", "function:render",
                               "--format", "json"])
            self.assertEqual(status, 0)
            rendered = json.loads(output.getvalue())["pseudocode"][0]["text"]
            self.assertIn("option=\"all\"", rendered)
            self.assertIn("items", rendered)
            (root / "main.py").write_text(
                "def choose(flag):\n    if flag:\n        return 1\n    else:\n        return 2\n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                status = main(["query", "--root", str(root), "--select", "function:choose",
                               "--format", "json"])
            self.assertEqual(status, 0)
            choose = next(item for item in json.loads(output.getvalue())["pseudocode"]
                          if item["function"] == "choose")
            self.assertIn("否则", choose["text"])

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

    def test_cli_persists_algorithm_through_entity_profile_and_not_legacy_archive(self):
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
            self.assertEqual(response["semantic_entity_store"]["state"], "stored")
            self.assertEqual(response["semantic_entity_store"]["profile"], "semantic-entity-model-1")
            self.assertTrue(response["semantic_fact_bundle"]["facts"])
            self.assertTrue(response["semantic_entity_validation"]["valid"])
            with sqlite3.connect(database) as connection:
                tables = {row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
                archive = connection.execute(
                    "SELECT payload FROM semantic_entity_archives WHERE scope_id=?",
                    (response["semantic_entity_store"]["scopeId"],)).fetchone()
            entity_model = json.loads(archive[0])
            self.assertTrue(any(item["ref"]["kind"] == "ComputationEntity" for item in entity_model["entities"]))
            self.assertTrue(any("implementationView" in item for item in entity_model["sourceMappings"]))
            stored_views = [item["implementationView"] for item in entity_model["sourceMappings"]
                            if "implementationView" in item]
            self.assertTrue(stored_views[0]["pseudocode"]["text"])
            self.assertNotIn("sessions", tables)

    def test_cli_parses_code_review_graph_json_for_source_mapped_call_facts(self):
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as output_dir:
            root = Path(temporary)
            (root / "src").mkdir()
            (root / "src/run.py").write_text("def run():\n    parse()\n", encoding="utf-8")
            (root / "src/parse.py").write_text("def parse():\n    return 1\n", encoding="utf-8")
            graph_output = Path(output_dir) / "graph.json"
            graph_document = {
                "status": "ok", "pattern": "callees_of", "target": "run",
                "result_count": 1, "results_omitted": 0,
                "results": [{"kind": "Function", "name": "parse", "qualified_name": "parse",
                             "file_path": "src/parse.py", "line_start": 1, "line_end": 2,
                             "call_site": {"line": 2, "file": "src/run.py"}}],
                "edges": [{"source": "run", "target": "parse"}],
            }
            graph_output.write_text(json.dumps(graph_document), encoding="utf-8")
            database = Path(output_dir) / "semantic.sqlite"
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = main(["algorithm", "--root", str(root), "--source", "src/run.py",
                               "--function", "run", "--semantic-facts", "--graph-output",
                               str(graph_output), "--graph-version", "2.3.9", "--store", str(database)])

            self.assertEqual(status, 2, errors.getvalue())
            result = json.loads(output.getvalue())
            bundle = result["semantic_fact_bundle"]
            self.assertTrue(any(fact["predicate"] == "behavior.calls" for fact in bundle["facts"]))
            self.assertIn("GRAPH_INDEX_FRESHNESS_UNVERIFIED",
                          {item["code"] for item in bundle["coverage"][0]["diagnostics"]})
            self.assertTrue(result["semantic_validation"]["valid"], result["semantic_validation"]["diagnostics"])
            with sqlite3.connect(database) as connection:
                archive = connection.execute("SELECT payload FROM semantic_entity_archives WHERE scope_id=?",
                    (result["semantic_entity_store"]["scopeId"],)).fetchone()
            entity_model = json.loads(archive[0])
            views = [item["implementationView"] for item in entity_model["sourceMappings"]
                     if "implementationView" in item]
            self.assertEqual(len(views), 1)
            self.assertEqual(views[0]["algorithm"]["problem"], "run")
            self.assertEqual(views[0]["graphToolResult"], graph_document)
            self.assertTrue(any(item.get("toolName") == "code-review-graph"
                                for item in entity_model["evidence"]))
            algorithm_evidence_ids = {item["evidenceId"]
                                      for item in views[0]["semanticFactBundle"]["evidence"]}
            self.assertTrue(algorithm_evidence_ids <= {item["evidenceId"] for item in entity_model["evidence"]})
            changed_graph = {**graph_document, "result_count": 2,
                             "results": graph_document["results"] + [{"kind": "Function",
                                 "name": "extra", "qualified_name": "extra", "file_path": "src/parse.py",
                                 "line_start": 3, "line_end": 4,
                                 "call_site": {"line": 2, "file": "src/run.py"}}]}
            graph_output.write_text(json.dumps(changed_graph), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                status = main(["algorithm", "--root", str(root), "--source", "src/run.py",
                               "--function", "run", "--semantic-facts", "--graph-output",
                               str(graph_output), "--graph-version", "2.3.9", "--store", str(database)])
            self.assertEqual(status, 2)
            with sqlite3.connect(database) as connection:
                archive = connection.execute("SELECT payload FROM semantic_entity_archives WHERE scope_id=?",
                    (result["semantic_entity_store"]["scopeId"],)).fetchone()
            entity_model = json.loads(archive[0])
            views = [item["implementationView"] for item in entity_model["sourceMappings"]
                     if "implementationView" in item]
            self.assertEqual({json.dumps(item["graphToolResult"], sort_keys=True) for item in views},
                             {json.dumps(graph_document, sort_keys=True), json.dumps(changed_graph, sort_keys=True)})
            queried = io.StringIO()
            with contextlib.redirect_stdout(queried), contextlib.redirect_stderr(io.StringIO()):
                status = main(["entities", "--root", str(root), "--select", "run", "--store", str(database),
                               "--format", "json"])
            self.assertEqual(status, 0)
            entity_response = json.loads(queried.getvalue())
            queried_views = [item["implementationView"] for item in entity_response["entity"]["sourceMappings"]
                             if "implementationView" in item]
            self.assertTrue(all(item["pseudocode"]["text"] for item in queried_views))
            self.assertEqual({json.dumps(item["graphToolResult"], sort_keys=True) for item in queried_views},
                             {json.dumps(graph_document, sort_keys=True), json.dumps(changed_graph, sort_keys=True)})
            self.assertTrue(algorithm_evidence_ids <= {item["evidenceId"]
                for item in entity_response["entity"]["evidence"]})

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
