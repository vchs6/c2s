import tempfile
import unittest
import os
from pathlib import Path
from unittest.mock import patch

from c2s_semantic_contract import semantic_model_catalogs, validate_model
from c2s_semantic_contract.projection import project_query_to_semantic_model
from c2s_semantic_contract.projection import project_algorithm_to_semantic_model
from c2s_skill.algorithm import extract_python_algorithm, extract_rust_algorithm
from c2s_skill.query import query_project


class FullSemanticProjectionTests(unittest.TestCase):
    def test_algorithm_projection_emits_typed_steps_regions_and_control_edges(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = b"def choose(flag):\n    if flag:\n        return 1\n    return 0\n"
            (root / "sample.py").write_bytes(source)
            algorithm = extract_python_algorithm(source, "sample.py", "choose")["algorithm"]
            algorithm["body"]["data_edges"].append({"from_step": "s1", "to_step": "s2", "role": "value"})

            projection = project_algorithm_to_semantic_model(algorithm, root)
            bundle = projection["bundle"]
            validation = validate_model(bundle, semantic_model_catalogs(), projection["sourceObservations"])

        self.assertTrue(validation["valid"], validation["diagnostics"])
        predicates = [fact["predicate"] for fact in bundle["facts"]]
        self.assertIn("behavior.has_body", predicates)
        self.assertIn("behavior.body_region", predicates)
        self.assertIn("region.member", predicates)
        self.assertIn("behavior.control_edge", predicates)
        self.assertIn("behavior.data_edge", predicates)
        edge = next(fact for fact in bundle["facts"] if fact["predicate"] == "behavior.control_edge")
        self.assertEqual({item["role"] for item in edge["arguments"]}, {"target", "edgeKind", "condition"})

    def test_algorithm_projection_rejects_source_changes_after_lowering(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "sample.py"
            source = b"def value():\n    return 1\n"
            path.write_bytes(source)
            algorithm = extract_python_algorithm(source, "sample.py", "value")["algorithm"]
            path.write_bytes(source.replace(b"return 1", b"return 2"))

            with self.assertRaisesRegex(ValueError, "digest changed"):
                project_algorithm_to_semantic_model(algorithm, root)

    def test_algorithm_projection_rejects_structurally_invalid_documents(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = b"def value():\n    return 1\n"
            (root / "sample.py").write_bytes(source)
            algorithm = extract_python_algorithm(source, "sample.py", "value")["algorithm"]
            algorithm["body"]["steps"][0]["kind"] = "not-a-step-kind"

            with self.assertRaisesRegex(ValueError, "structural validation"):
                project_algorithm_to_semantic_model(algorithm, root)

    def test_rust_algorithm_projection_preserves_source_mapped_steps(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = b"fn choose(flag: bool) -> i32 { if flag { return 1; } 0 }"
            (root / "lib.rs").write_bytes(source)
            algorithm = extract_rust_algorithm(source, "lib.rs", "choose")["algorithm"]

            projection = project_algorithm_to_semantic_model(algorithm, root)
            validation = validate_model(projection["bundle"], semantic_model_catalogs(),
                                        projection["sourceObservations"])

        self.assertTrue(validation["valid"], validation["diagnostics"])
        self.assertTrue(any(fact["predicate"] == "behavior.control_edge"
                            for fact in projection["bundle"]["facts"]))
        self.assertTrue(all(item["status"] == "verified"
                            for item in projection["sourceObservations"]["items"]))

    def test_fixed_real_projects_project_every_acquired_fact_and_keep_gaps(self):
        checkout_root = Path(__file__).resolve().parents[2] / ".local/real-projects"
        cases = (("click", 23779, True), ("regex", 54313, False))
        for name, expected_count, expected_complete in cases:
            with self.subTest(project=name):
                root = checkout_root / name
                if not root.is_dir():
                    self.skipTest(f"fixed project checkout unavailable: {name}")
                if name == "regex":
                    with patch.dict(os.environ, {"CARGO": ""}), \
                            patch("c2s_skill.acquisition.shutil.which", return_value=None):
                        query = query_project(root, ["all-supported-facts"])
                else:
                    query = query_project(root, ["all-supported-facts"])

                projection = project_query_to_semantic_model(query)
                bundle = projection["bundle"]
                validation = validate_model(bundle, semantic_model_catalogs(),
                                            projection["sourceObservations"])
                self.assertEqual(len(query.facts), expected_count)
                self.assertEqual(len(bundle["facts"]), expected_count)
                self.assertEqual(len({fact["factId"] for fact in bundle["facts"]}), expected_count)
                self.assertEqual(query.complete, expected_complete)
                self.assertTrue(validation["valid"], validation["diagnostics"])
                coverage_diagnostics = bundle["coverage"][0]["diagnostics"]
                self.assertFalse(any(diagnostic["code"] == "FACT_KIND_UNMAPPED"
                                     for diagnostic in coverage_diagnostics))
                self.assertEqual(bool(bundle["coverage"][0]["complete"]), expected_complete)
                if name == "regex":
                    self.assertTrue(query.gaps)
                    self.assertTrue(any(diagnostic["severity"] == "gap"
                                        for diagnostic in coverage_diagnostics))

    def test_real_python_query_projects_all_supported_kinds_into_one_valid_fact_set(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "semantic-fixture"\nrequires-python = ">=3.11"\n')
            (root / "sample.py").write_text(
                '"""Module documentation."""\n'
                'def outer(value):\n'
                '    """Return a transformed value."""\n'
                '    local_value = value + 1\n'
                '    return local_value\n')
            query = query_project(root, ["all-supported-facts"])

            projection = project_query_to_semantic_model(query)
            bundle = projection["bundle"]
            validation = validate_model(bundle, semantic_model_catalogs(), projection["sourceObservations"])

        self.assertTrue(validation["valid"], validation["diagnostics"])
        self.assertEqual(bundle["profile"], "semantic-fact-model-1")
        predicates = {fact["predicate"] for fact in bundle["facts"]}
        self.assertTrue({"project.name", "project.language_declared", "function.declared",
                         "behavior.contract", "behavior.algorithm_step", "binding.local"} <= predicates)
        function_fact = next(fact for fact in bundle["facts"] if fact["predicate"] == "function.declared")
        body_facts = [fact for fact in bundle["facts"] if fact["predicate"] == "behavior.algorithm_step"]
        self.assertTrue(body_facts)
        self.assertTrue(all(fact["subject"]["identity"] == function_fact["subject"]["identity"]
                            for fact in body_facts))
        self.assertTrue(all(fact["sourceMetadata"]["kind"] == "algorithm_step" for fact in body_facts))


if __name__ == "__main__":
    unittest.main()
