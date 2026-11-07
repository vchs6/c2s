from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "skill" / "src"))

from c2s_skill.entity_construction import construct_semantic_entity_candidates


class SemanticEntityConstructionTests(unittest.TestCase):
    def test_project_manifest_creates_evidence_backed_project_candidate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "pyproject.toml").write_text('[project]\nname = "sample-project"\n', encoding="utf-8")
            result = construct_semantic_entity_candidates(root)
        project = next(item for item in result["candidates"] if item["kind"] == "Project")
        self.assertEqual(project["name"], "sample-project")
        self.assertEqual(project["epistemicStatus"], "provisional")
        evidence = next(item for item in result["evidence"] if item["evidenceId"] == project["evidenceIds"][0])
        self.assertEqual(evidence["path"], "pyproject.toml")
        self.assertLess(evidence["startByte"], evidence["endByte"])

    def test_class_fields_and_functions_remain_distinct_provisional_candidates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "pyproject.toml").write_text('[project]\nname = "sample"\n', encoding="utf-8")
            source = ("class Order:\n    status: str\n\n"
                      "    def total(self):\n        return 0\n\n"
                      "def calculate_total(order):\n    return order.total\n")
            (root / "orders.py").write_text(source, encoding="utf-8")
            result = construct_semantic_entity_candidates(root)
        data_candidate = next(item for item in result["candidates"] if item["kind"] == "DataEntity")
        computation = next(item for item in result["candidates"] if item["kind"] == "ComputationEntity")
        computations = [item for item in result["candidates"] if item["kind"] == "ComputationEntity"]
        self.assertEqual(data_candidate["name"], "Order")
        self.assertEqual(computation["name"], "calculate_total")
        self.assertNotEqual(data_candidate["candidateId"], computation["candidateId"])
        status = data_candidate["attributes"][0]
        self.assertEqual(status["semanticType"], "unknown")
        self.assertEqual(status["implementationType"], "str")
        self.assertEqual(status["valueRange"]["kind"], "unknown")
        self.assertTrue(data_candidate["sourceConstructIds"])
        self.assertTrue(computation["sourceConstructIds"])
        self.assertEqual({item["name"] for item in computations}, {"total", "calculate_total"})

    def test_enum_declarations_only_supply_evidenced_value_ranges(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "pyproject.toml").write_text('[project]\nname = "sample"\n', encoding="utf-8")
            (root / "orders.py").write_text(
                "from enum import Enum\nclass State(Enum):\n    READY = 'ready'\n    SENT = 'sent'\n"
                "class Order:\n    state: State\n", encoding="utf-8")
            result = construct_semantic_entity_candidates(root)
        order = next(item for item in result["candidates"] if item["kind"] == "DataEntity")
        state = order["attributes"][0]
        self.assertEqual(state["implementationType"], "State")
        self.assertEqual(state["semanticType"], "unknown")
        self.assertEqual(state["valueRange"]["kind"], "finite_set")
        self.assertEqual(state["valueRange"]["values"], ["READY", "SENT"])
        self.assertTrue(state["valueRange"]["evidenceIds"])

    def test_documented_modules_and_capabilities_create_candidates_and_relation_candidates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "pyproject.toml").write_text('[project]\nname = "sample"\n', encoding="utf-8")
            (root / "README.md").write_text(
                "# Sample\n\n## Modules\n- parser: reads source text\n\n"
                "## Features\n- render: creates a report\n", encoding="utf-8")
            result = construct_semantic_entity_candidates(root)
        modules = [item for item in result["candidates"] if item["kind"] == "Module"]
        capabilities = [item for item in result["candidates"] if item["kind"] == "Capability"]
        self.assertEqual([item["name"] for item in modules], ["parser"])
        self.assertEqual([item["name"] for item in capabilities], ["render"])
        self.assertEqual({item["predicate"] for item in result["relationCandidates"]}, {"defines"})

    def test_missing_domain_evidence_does_not_invent_module_or_capability(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "pyproject.toml").write_text('[project]\nname = "sample"\n', encoding="utf-8")
            (root / "main.py").write_text("def run():\n    return 1\n", encoding="utf-8")
            result = construct_semantic_entity_candidates(root)
        self.assertFalse(any(item["kind"] in {"Module", "Capability"} for item in result["candidates"]))
        self.assertTrue(any(item["candidateKind"] == "Module" for item in result["diagnostics"]))
        self.assertTrue(any(item["candidateKind"] == "Capability" for item in result["diagnostics"]))


if __name__ == "__main__":
    unittest.main()
