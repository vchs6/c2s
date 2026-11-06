import unittest
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from c2s_skill.algorithm import validate_algorithms


def _algorithm(steps=None, control_edges=None, data_edges=None):
    return {
        "schema_version": "1.0.0",
        "algorithms": [{
            "algorithm_id": "alg:run",
            "purpose": "current_implementation",
            "problem": "Compute a result",
            "body": {
                "regions": [{"region_id": "root", "parent_region_id": None}],
                "steps": steps if steps is not None else [
                    {"step_id": "s1", "kind": "compute", "region_id": "root",
                     "evidence_refs": ["ev:1"], "source": {"path": "src.py", "start_byte": 0, "end_byte": 8},
                     "attributes": {"operation": "add", "type_rule": "unknown", "evaluation_order": "unknown"}},
                    {"step_id": "s2", "kind": "return", "region_id": "root",
                     "evidence_refs": ["ev:2"], "source": {"path": "src.py", "start_byte": 9, "end_byte": 17}},
                ],
                "control_edges": control_edges if control_edges is not None else [
                    {"from_step": "s1", "to_step": "s2", "kind": "next", "condition": {"kind": "true"}}
                ],
                "data_edges": data_edges if data_edges is not None else [
                    {"from_step": "s1", "to_step": "s2", "role": "return_value"}
                ],
            },
            "implementation_refs": [{"subject_id": "subject:run"}],
            "evidence_refs": ["ev:1", "ev:2"],
            "omissions": [],
        }],
    }


class AlgorithmContractTests(unittest.TestCase):
    def test_schema_is_valid_2020_12_and_rejects_unknown_fields(self):
        schema_path = Path(__file__).resolve().parents[1] / "contracts/semantic-algorithm.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        document = _algorithm()
        document["algorithms"][0]["body"]["steps"][0]["untyped_guess"] = True
        self.assertTrue(any(item["code"] == "SCHEMA_INVALID" for item in validate_algorithms(document)))

    def test_malformed_identifier_values_return_diagnostics_instead_of_raising(self):
        document = _algorithm()
        document["algorithms"][0]["body"]["steps"][0]["step_id"] = {"not": "an id"}
        self.assertTrue(validate_algorithms(document))

    def test_malformed_region_parents_and_edge_endpoints_return_diagnostics(self):
        document = _algorithm()
        body = document["algorithms"][0]["body"]
        body["regions"][0]["parent_region_id"] = {"not": "an id"}
        body["control_edges"][0]["to_step"] = ["not", "an id"]
        self.assertTrue(validate_algorithms(document))

    def test_accepts_typed_algorithm_body_and_step_local_ids(self):
        document = _algorithm()
        document["algorithms"].append({**document["algorithms"][0], "algorithm_id": "alg:other"})
        self.assertEqual(validate_algorithms(document), [])

    def test_rejects_duplicate_step_ids_and_dangling_control_and_data_edges(self):
        document = _algorithm()
        body = document["algorithms"][0]["body"]
        body["steps"][1]["step_id"] = "s1"
        body["control_edges"].append({"from_step": "s1", "to_step": "missing", "kind": "branch_true",
                                      "condition": {"kind": "unknown", "reason": "dynamic"}})
        body["data_edges"].append({"from_step": "missing", "to_step": "s2", "role": "value"})
        diagnostics = validate_algorithms(document)
        codes = {item["code"] for item in diagnostics}
        self.assertTrue({"DUPLICATE_STEP_ID", "DANGLING_CONTROL_EDGE", "DANGLING_DATA_EDGE"} <= codes)

    def test_opaque_step_requires_source_impact_unknowns_and_effect_boundary(self):
        opaque = {"step_id": "opaque", "kind": "opaque", "region_id": "root",
                  "evidence_refs": ["ev:1"], "source": None}
        document = _algorithm(steps=[opaque], control_edges=[], data_edges=[])
        codes = {item["code"] for item in validate_algorithms(document)}
        self.assertIn("OPAQUE_BOUNDARY_REQUIRED", codes)
        opaque.update({"source": {"path": "src.py", "start_byte": 0, "end_byte": 4},
                       "impact": "May invoke arbitrary callback",
                       "unknowns": ["callback target"],
                       "boundary": {"inputs": ["x"], "outputs": ["y"], "effects": ["unknown"]}})
        self.assertEqual(validate_algorithms(document), [])

    def test_compute_requires_explicit_unknown_numeric_and_evaluation_rules(self):
        document = _algorithm()
        document["algorithms"][0]["body"]["steps"][0]["attributes"].pop("evaluation_order")
        codes = {item["code"] for item in validate_algorithms(document)}
        self.assertIn("COMPUTE_SEMANTICS_REQUIRED", codes)


if __name__ == "__main__":
    unittest.main()
