import unittest
import platform
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

from c2s_skill.capability_matrix import (ToolRun, describe_tools_used, load_tool_matrix, select_tools,
                                         validate_matrix_evidence)
from c2s_skill.query import query_project


def provider(tool_id, provides, *, status="lit", evidence=True):
    return {"id": tool_id, "parser": "source_python", "provides": provides,
            "status": status, "validation": {"tests": ["skill/tests/test_capability_selection.py"],
                "evidence": ["skill/tests/test_capability_selection.py"] if evidence else []}}


class CapabilitySelectionTests(unittest.TestCase):
    def test_tool_run_exposes_constructs_from_selected_language_parsers(self):
        first = object()
        second = object()
        run = ToolRun(scan=type("Scan", (), {"files": [type("File", (), {"constructs": (first, second)})()]})(),
                      workspace_facts=(), workspace_gap=None, tools=("python-ast",))
        self.assertEqual(run.source_constructs, (first, second))

    def test_selects_smallest_tool_set_that_covers_every_need(self):
        matrix = {"tools": [
            provider("python", ["declarations", "definitions"]),
            provider("rust", ["declarations"]),
            provider("cargo", ["workspace"]),
        ]}

        selected = select_tools(["declarations", "workspace"], matrix,
                                available_tools={"python", "rust", "cargo"})

        self.assertEqual(selected.tools, ("cargo", "python"))
        self.assertEqual(selected.uncovered, ())

    def test_unlit_or_unavailable_parser_cannot_cover_a_need(self):
        matrix = {"tools": [
            provider("candidate", ["bindings"], status="candidate"),
            provider("not-installed", ["calls"]),
        ]}

        selected = select_tools(["bindings", "calls"], matrix,
                                available_tools={"candidate"})

        self.assertEqual(selected.tools, ())
        self.assertEqual(selected.uncovered, ("bindings", "calls"))

    def test_host_specific_tool_is_not_selected_for_an_unknown_host(self):
        tool = provider("linux-only", ["declarations"])
        tool["host_os"] = "linux"

        selected = select_tools(["declarations"], {"tools": [tool]},
                                available_tools={"linux-only"},
                                environment={"host_os": "windows", "target": ""})

        self.assertEqual(selected.tools, ())
        self.assertEqual(selected.uncovered, ("declarations",))

    def test_incomplete_validation_evidence_never_lights_a_parser(self):
        matrix = {"tools": [provider("parser", ["declarations"], evidence=False)]}

        selected = select_tools(["declarations"], matrix, available_tools={"parser"})

        self.assertEqual(selected.tools, ())
        self.assertEqual(selected.uncovered, ("declarations",))

    def test_runtime_selection_does_not_require_source_checkout_evidence_files(self):
        with TemporaryDirectory() as temporary:
            matrix = {"tools": [provider("installed-parser", ["declarations"])]}

            installed_module = Path(temporary) / "site-packages" / "c2s_skill" / "capability_matrix.py"
            with patch("c2s_skill.capability_matrix.__file__", str(installed_module)):
                selected = select_tools(["declarations"], matrix,
                    available_tools={"installed-parser"})

            self.assertEqual(selected.tools, ("installed-parser",))
            self.assertEqual(selected.uncovered, ())

    def test_checked_in_lit_matrix_references_real_test_and_evidence_files(self):
        validate_matrix_evidence(load_tool_matrix())

        invalid = {"tools": [provider("broken", ["declarations"])]}
        invalid["tools"][0]["validation"]["evidence"] = ["../escape"]
        with self.assertRaisesRegex(ValueError, "invalid evidence reference"):
            validate_matrix_evidence(invalid)

    def test_duplicate_or_unknown_needs_are_normalized_without_fake_coverage(self):
        matrix = {"tools": [provider("python", ["declarations"])]}

        selected = select_tools(["declarations", "declarations", "types"], matrix,
                                available_tools={"python"})

        self.assertEqual(selected.tools, ("python",))
        self.assertEqual(selected.uncovered, ("types",))

    def test_tool_session_version_uses_observed_runtime_and_unknown_stays_unknown(self):
        records = describe_tools_used(["project-manifests", "not-installed"], load_tool_matrix())
        observed = {item["name"]: item for item in records}
        self.assertEqual(observed["project-manifests"]["version"], platform.python_version())
        self.assertEqual(observed["project-manifests"]["status"], "verified")
        self.assertEqual(observed["not-installed"]["status"], "unknown")

    def test_query_executes_the_parser_selected_by_its_semantic_need(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "main.py").write_text("class Answer:\n    pass\n", encoding="utf-8")

            result = query_project(root, ["classes"])

            self.assertEqual([fact.name for fact in result.facts], ["Answer"])
            self.assertEqual(result.tools_used, ("python-ast",))


if __name__ == "__main__":
    unittest.main()
