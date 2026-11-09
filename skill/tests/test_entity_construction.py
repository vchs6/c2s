from __future__ import annotations

import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "skill" / "src"))

from codesemantics.entity_construction import construct_semantic_entity_candidates


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

    def test_test_function_is_a_distinct_entity_linked_only_to_a_unique_called_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "pyproject.toml").write_text('[project]\nname = "sample"\n', encoding="utf-8")
            (root / "logic.py").write_text("def calculate_total(order):\n    return order.total\n", encoding="utf-8")
            (root / "test_logic.py").write_text(
                "from logic import calculate_total\n"
                "def test_calculate_total():\n    assert calculate_total({'total': 4}) == 4\n\n"
                "def test_calculate_total_empty():\n    assert calculate_total({'total': 0}) == 0\n", encoding="utf-8")
            result = construct_semantic_entity_candidates(root)
        tests = [item for item in result["candidates"] if item["kind"] == "TestEntity"]
        computation = next(item for item in result["candidates"] if item["name"] == "calculate_total")
        self.assertEqual({item["name"] for item in tests},
                         {"test_calculate_total", "test_calculate_total_empty"})
        self.assertTrue(all(item["candidateId"] != computation["candidateId"] for item in tests))
        relations = [item for item in result["relationCandidates"] if item["predicate"] == "verified_by"]
        self.assertEqual(len(relations), 2)
        self.assertTrue(all(item["subjectCandidateId"] == computation["candidateId"] for item in relations))
        self.assertEqual({item["targetCandidateId"] for item in relations},
                         {item["candidateId"] for item in tests})

    def test_test_without_resolvable_target_remains_a_gap(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "pyproject.toml").write_text('[project]\nname = "sample"\n', encoding="utf-8")
            (root / "test_external.py").write_text(
                "def test_external_service():\n    assert external_call()\n", encoding="utf-8")
            result = construct_semantic_entity_candidates(root)
        test_entity = next(item for item in result["candidates"] if item["kind"] == "TestEntity")
        self.assertFalse(any(item["predicate"] == "verified_by" for item in result["relationCandidates"]))
        self.assertTrue(any(item.get("candidateId") == test_entity["candidateId"]
                            and item["code"] == "TEST_TARGET_UNRESOLVED"
                            for item in result["diagnostics"]))

    def test_algorithm_steps_are_implementation_views_of_computation_not_entities(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "pyproject.toml").write_text('[project]\nname = "sample"\n', encoding="utf-8")
            (root / "logic.py").write_text(
                "def calculate(value):\n    result = normalize(value)\n    return result\n\n"
                "def normalize(value):\n    return value\n", encoding="utf-8")
            result = construct_semantic_entity_candidates(root)
        calculate = next(item for item in result["candidates"] if item["name"] == "calculate")
        self.assertTrue(calculate["implementationViews"])
        self.assertTrue(all(item["evidenceIds"] for item in calculate["implementationViews"]))
        self.assertFalse(any(item["kind"] == "AlgorithmStep" for item in result["candidates"]))

    def test_rust_computation_keeps_source_mapped_algorithm_view(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Cargo.toml").write_text('[package]\nname = "sample"\nversion = "0.1.0"\nedition = "2021"\n',
                                            encoding="utf-8")
            (root / "src").mkdir()
            (root / "src/lib.rs").write_text(
                "pub fn calculate(value: i32) -> i32 {\n    let result = normalize(value);\n    result\n}\n"
                "fn normalize(value: i32) -> i32 { value }\n", encoding="utf-8")
            result = construct_semantic_entity_candidates(root)
        calculate = next(item for item in result["candidates"] if item["name"] == "calculate")
        self.assertTrue(calculate["implementationViews"])
        self.assertTrue(all(item["path"] == "src/lib.rs" for item in calculate["implementationViews"]))

    def test_language_constructs_are_implementation_references_not_semantic_entity_kinds(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Cargo.toml").write_text('[package]\nname = "sample"\nversion = "0.1.0"\nedition = "2021"\n',
                                            encoding="utf-8")
            (root / "src").mkdir()
            (root / "src/lib.rs").write_text(
                "enum State { Ready, Sent }\nstruct Record<T> { state: State, value: T }\n"
                "macro_rules! mark { ($x:expr) => {$x}; }\n"
                "pub fn calculate(value: i32) -> i32 { let f = |x| x + 1; mark!(f(value)) }\n",
                encoding="utf-8")
            result = construct_semantic_entity_candidates(root)
        record = next(item for item in result["candidates"] if item["name"] == "Record")
        calculate = next(item for item in result["candidates"] if item["name"] == "calculate")
        self.assertIn("enum_declaration", " ".join(
            item["description"] for item in result["evidence"] if item["evidenceId"] in record["evidenceIds"]))
        self.assertTrue(any(item["role"] == "implementation_reference"
                            and item["candidateId"] == calculate["candidateId"]
                            for item in result["sourceMappings"]))
        self.assertFalse(any(item["kind"] in {"Macro", "Enum", "Closure", "Generic"}
                            for item in result["candidates"]))



if __name__ == "__main__":
    unittest.main()
