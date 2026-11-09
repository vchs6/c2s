import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from codesemantics.graph_tool_adapter import parse_code_review_graph_response
from codesemantics.capability_matrix import (ToolSelection, host_environment, load_tool_matrix,
                                         parse_selected_tool_output, select_tools)


class CodeReviewGraphAdapterTests(unittest.TestCase):
    def test_real_output_parser_is_dispatched_only_through_matrix_selection(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "run.py").write_text("def run():\n    parse()\n", encoding="utf-8")
            (root / "parse.py").write_text("def parse():\n    pass\n", encoding="utf-8")
            response = {"status": "ok", "pattern": "callees_of", "target": "run.py::run",
                "result_count": 1, "results_omitted": 0,
                "results": [{"name": "parse", "qualified_name": "parse.py::parse",
                    "file_path": "parse.py", "call_site": {"line": 2, "file": "run.py"}}],
                "edges": [{"source": "run.py::run", "target": "parse.py::parse"}]}
            matrix = load_tool_matrix()
            selection = select_tools(["calls.cross_file.candidates"], matrix,
                available_tools={"code-review-graph"}, environment=host_environment())

            parsed = parse_selected_tool_output(selection, "code-review-graph", response,
                                                root, "2.3.9", matrix)

            self.assertEqual(parsed.call_sites[0].callee_path, "parse.py")
            self.assertIn("GRAPH_INDEX_FRESHNESS_UNVERIFIED", {item.code for item in parsed.diagnostics})
            with self.assertRaisesRegex(ValueError, "was not selected"):
                parse_selected_tool_output(ToolSelection((), ("calls.cross_file.candidates",)),
                    "code-review-graph", response, root, "2.3.9", matrix)

    def test_parses_call_site_rows_and_keeps_resolution_and_source_locations(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "src").mkdir()
            (root / "src/run.py").write_text("def run():\n    parse()\n", encoding="utf-8")
            (root / "src/parse.py").write_text("def parse():\n    pass\n", encoding="utf-8")
            response = {
                "status": "ok", "pattern": "callees_of", "target": "run",
                "result_count": 1, "results_omitted": 0,
                "results": [{"kind": "Function", "name": "parse", "qualified_name": "parse",
                             "file_path": "src/parse.py", "line_start": 1, "line_end": 2,
                             "call_site": {"line": 2, "file": "src/run.py"},
                             "target_resolution": "direct"}],
                "edges": [{"source": "run", "target": "parse"}],
            }

            result = parse_code_review_graph_response(response, root)

            self.assertFalse(result.complete)
            self.assertIn("GRAPH_INDEX_FRESHNESS_UNVERIFIED", {item.code for item in result.diagnostics})
            self.assertIn("GRAPH_TOOL_VERSION_UNKNOWN", {item.code for item in result.diagnostics})
            self.assertEqual(len(result.call_sites), 1)
            call = result.call_sites[0]
            self.assertEqual((call.caller_path, call.caller_line), ("src/run.py", 2))
            self.assertEqual((call.callee_path, call.callee_name), ("src/parse.py", "parse"))
            self.assertEqual(call.resolution, "direct")

    def test_truncated_results_are_not_reported_as_complete(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "run.py").write_text("def run():\n    parse()\n", encoding="utf-8")
            response = {"status": "ok", "pattern": "callers_of", "target": "parse",
                        "result_count": 3, "results_omitted": 2,
                        "results": [{"kind": "Function", "name": "run", "qualified_name": "run",
                                     "file_path": "run.py", "line_start": 1, "line_end": 2,
                                     "call_site": {"line": 2}}], "edges": []}

            result = parse_code_review_graph_response(response, root)

            self.assertFalse(result.complete)
            self.assertEqual(result.omitted_count, 2)
            self.assertIn("GRAPH_RESULTS_TRUNCATED", {item.code for item in result.diagnostics})

    def test_callees_query_uses_target_file_when_call_site_file_is_omitted(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "src").mkdir()
            (root / "src/run.py").write_text("def run():\n    parse()\n", encoding="utf-8")
            (root / "src/parse.py").write_text("def parse():\n    pass\n", encoding="utf-8")
            response = {"status": "ok", "pattern": "callees_of", "target": "src/run.py::run",
                "result_count": 1, "results_omitted": 0,
                "results": [{"name": "parse", "qualified_name": "src/parse.py::parse",
                    "file_path": "src/parse.py", "call_site": {"line": 2}}],
                "edges": [{"source": "src/run.py::run", "target": "src/parse.py::parse"}]}

            result = parse_code_review_graph_response(response, root, tool_version="2.3.9")

            self.assertEqual(result.call_sites[0].caller_path, "src/run.py")
            self.assertEqual(result.call_sites[0].callee_path, "src/parse.py")

    def test_path_escape_and_unknown_resolution_are_preserved_as_gaps(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            response = {"status": "ok", "pattern": "callees_of", "target": "run",
                        "result_count": 1, "results_omitted": 0,
                        "results": [{"kind": "Function", "name": "parse", "qualified_name": "parse",
                                     "file_path": "../outside.py", "line_start": 1, "line_end": 1,
                                     "call_site": {"line": 2}, "target_resolution": "unresolved"}],
                        "edges": []}

            result = parse_code_review_graph_response(response, root)

            self.assertFalse(result.complete)
            self.assertEqual(result.call_sites, ())
            self.assertIn("GRAPH_PATH_OUTSIDE_ROOT", {item.code for item in result.diagnostics})

    def test_count_inconsistency_is_a_gap_even_when_no_rows_are_returned(self):
        with TemporaryDirectory() as temporary:
            response = {"status": "ok", "pattern": "callers_of", "target": "parse",
                        "result_count": 3, "results_omitted": 0, "results": [], "edges": []}

            result = parse_code_review_graph_response(response, Path(temporary))

            self.assertFalse(result.complete)
            self.assertIn("GRAPH_COUNT_MISMATCH", {item.code for item in result.diagnostics})

    def test_callsite_rows_without_matching_edge_records_are_a_gap(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "run.py").write_text("def run():\n    parse()\n", encoding="utf-8")
            (root / "parse.py").write_text("def parse():\n    pass\n", encoding="utf-8")
            response = {"status": "ok", "pattern": "callees_of", "target": "run",
                "result_count": 1, "results_omitted": 0,
                "results": [{"kind": "Function", "name": "parse", "qualified_name": "parse",
                    "file_path": "parse.py", "line_start": 1, "line_end": 2,
                    "call_site": {"line": 2}}], "edges": []}

            result = parse_code_review_graph_response(response, root, tool_version="2.3.9")

            self.assertIn("GRAPH_EDGE_ROWS_MISMATCH", {item.code for item in result.diagnostics})


if __name__ == "__main__":
    unittest.main()
