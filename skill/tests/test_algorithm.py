import unittest
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from c2s_skill.algorithm import (_index_python_functions, _index_rust_functions,
                                 extract_python_algorithm, extract_rust_algorithm, validate_algorithms)
from c2s_semantic_contract.algorithm_projection import check_source_coverage, project_algorithm


def _algorithm(steps=None, control_edges=None, data_edges=None):
    contract_categories = ("inputs", "outputs", "preconditions", "outcomes", "effects", "ordering")
    return {
        "schema_version": "1.0.0",
        "algorithms": [{
            "algorithm_id": "alg:run",
            "purpose": "current_implementation",
            "problem": "Compute a result",
            "management": {"status": "unresolved", "project_subject_ids": []},
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
            "contract": {
                "inputs": [{"name": "x", "description": "Input value", "evidence_refs": ["ev:1"]}],
                "outputs": [{"name": "result", "description": "Computed value", "evidence_refs": ["ev:2"]}],
                "preconditions": [],
                "outcomes": [{"kind": "normal", "description": "Returns result",
                              "condition": {"kind": "true"}, "evidence_refs": ["ev:2"]},
                             {"kind": "error", "description": "May fail",
                              "condition": {"kind": "unknown", "reason": "callee behavior not expanded"},
                              "evidence_refs": ["ev:2"]}],
                "effects": [{"kind": "unknown", "description": "Effects of callees not resolved",
                             "condition": {"kind": "unknown", "reason": "callee behavior not expanded"},
                             "evidence_refs": ["ev:1"]}],
                "ordering_constraints": [],
                "coverage": [{"category": category, "state": "complete", "evidence_refs": ["ev:1"]}
                             for category in contract_categories],
            },
            "implementation_refs": [{"subject_id": "subject:run"}],
            "evidence_refs": ["ev:1", "ev:2"],
            "omissions": [],
        }],
    }


class AlgorithmContractTests(unittest.TestCase):
    def test_function_indexes_build_once_and_preserve_source_start_offsets(self):
        python_source = b"def alpha(): return 1\nclass C:\n    def beta(self): return 2\n"
        _, _, python_index = _index_python_functions(python_source)
        self.assertEqual([python_index[offset].name for offset in sorted(python_index)], ["alpha", "beta"])
        rust_source = b"fn alpha() {}\nimpl C { fn beta(&self) {} }\n"
        _, rust_index = _index_rust_functions(rust_source)
        self.assertEqual([rust_index[offset].child_by_field_name("name").text.decode()
                          for offset in sorted(rust_index)], ["alpha", "beta"])

    def test_python_source_produces_located_algorithm_regions_and_explicit_gaps(self):
        source = (b"def answer(flag):\n"
                  b"    if flag:\n"
                  b"        return helper(1)\n"
                  b"    raise ValueError('missing')\n")
        algorithm = extract_python_algorithm(source, "src/app.py", "answer")
        self.assertEqual(algorithm["algorithm"]["purpose"], "current_implementation")
        body = algorithm["algorithm"]["body"]
        self.assertEqual([step["kind"] for step in body["steps"]], ["select", "return", "raise"])
        self.assertTrue(all(step["source"]["path"] == "src/app.py" for step in body["steps"]))
        self.assertTrue(any(edge["kind"] == "branch_true" for edge in body["control_edges"]))
        self.assertTrue(any(outcome["kind"] == "error" for outcome in algorithm["algorithm"]["contract"]["outcomes"]))
        self.assertIn("outputs", {gap["category"] for gap in algorithm["algorithm"]["contract"]["coverage"]
                                  if gap["state"] == "unknown"})
        self.assertEqual(validate_algorithms({"schema_version": "1.0.0", "algorithms": [algorithm["algorithm"]]}), [])

    def test_python_if_fallthrough_has_a_conditional_target_not_an_unconditional_edge(self):
        source = b"def choose(flag):\n    if flag:\n        return 1\n    return 0\n"
        body = extract_python_algorithm(source, "src.py", "choose")["algorithm"]["body"]
        select = next(step["step_id"] for step in body["steps"] if step["kind"] == "select")
        following_return = body["steps"][-1]["step_id"]
        edges = [edge for edge in body["control_edges"] if edge["from_step"] == select and
                 edge["to_step"] == following_return]
        self.assertEqual([edge["kind"] for edge in edges], ["branch_false"])

    def test_loop_does_not_add_implicit_continue_after_a_terminal_return(self):
        source = b"def first(items):\n    for item in items:\n        return item\n"
        body = extract_python_algorithm(source, "src.py", "first")["algorithm"]["body"]
        returned = next(step["step_id"] for step in body["steps"] if step["kind"] == "return")
        self.assertFalse(any(edge["from_step"] == returned and edge["kind"] == "continue"
                             for edge in body["control_edges"]))

    def test_rust_source_produces_located_control_regions_and_signature_contract(self):
        source = b"fn choose(flag: bool) -> i32 { if flag { return 1; } 0 }"
        algorithm = extract_rust_algorithm(source, "src/lib.rs", "choose")["algorithm"]
        self.assertEqual([port["name"] for port in algorithm["contract"]["inputs"]], ["flag"])
        self.assertEqual(algorithm["contract"]["outputs"][0]["name"], "return")
        self.assertTrue(any(step["kind"] == "select" for step in algorithm["body"]["steps"]))
        self.assertTrue(any(edge["kind"] == "branch_true" for edge in algorithm["body"]["control_edges"]))
        self.assertEqual(validate_algorithms({"schema_version": "1.0.0", "algorithms": [algorithm]}), [])

    def test_rust_only_treats_the_block_tail_expression_as_an_implicit_return(self):
        discarded = extract_rust_algorithm(b"fn discarded() { 1; }", "src.rs", "discarded")["algorithm"]
        tail = extract_rust_algorithm(b"fn tail() -> i32 { 1 }", "src.rs", "tail")["algorithm"]
        self.assertFalse(any(step["kind"] == "return" for step in discarded["body"]["steps"]))
        self.assertFalse(any(outcome["kind"] == "normal" and "Implicit tail" in outcome["description"]
                             for outcome in discarded["contract"]["outcomes"]))
        self.assertTrue(any(outcome["kind"] == "normal" and "Implicit tail" in outcome["description"]
                            for outcome in tail["contract"]["outcomes"]))

    def test_python_decorator_metadata_and_closure_binding_remain_explicitly_unresolved(self):
        source = (b"def register(callback):\n"
                  b"    @framework.command()\n"
                  b"    def wrapped(value):\n"
                  b"        return callback(value)\n"
                  b"    return wrapped\n")
        outer = extract_python_algorithm(source, "src/cli.py", "register")["algorithm"]
        algorithm = extract_python_algorithm(source, "src/cli.py", "register.wrapped")["algorithm"]
        reasons = " ".join(item["reason"] for item in algorithm["omissions"])
        self.assertIn("decorator", reasons.lower())
        self.assertIn("closure", " ".join(item["reason"] for item in outer["omissions"]).lower())
        self.assertFalse(any(step["kind"] == "call" and "framework.command" in
                             source[step["source"]["start_byte"]:step["source"]["end_byte"]].decode()
                             for step in algorithm["body"]["steps"]))

    def test_rust_macro_invocation_is_a_source_bound_opaque_step(self):
        source = b"fn report(value: &str) { println!(\"{value}\"); }"
        algorithm = extract_rust_algorithm(source, "src/lib.rs", "report")["algorithm"]
        macro = next(step for step in algorithm["body"]["steps"] if step["kind"] == "opaque")
        self.assertIn("macro_invocation", macro["impact"])
        self.assertIsNotNone(macro["source"])
        self.assertTrue(macro["unknowns"])

    def test_rust_closure_body_is_not_misattributed_to_enclosing_operation(self):
        source = b"fn mapper() { let add = |x| x + 1; consume(move || { send(); }); }"
        algorithm = extract_rust_algorithm(source, "src/lib.rs", "mapper")["algorithm"]
        reasons = " ".join(item["reason"] for item in algorithm["omissions"])
        self.assertIn("closure", reasons.lower())
        self.assertIn("capture", reasons.lower())
        self.assertFalse(any(step.get("attributes", {}).get("operation") == "+"
                             for step in algorithm["body"]["steps"]))
        self.assertEqual(validate_algorithms({"schema_version": "1.0.0", "algorithms": [algorithm]}), [])

    def test_python_lambda_body_and_capture_are_explicit_omissions(self):
        source = b"def mapper(x):\n    return lambda y: x + y\n"
        algorithm = extract_python_algorithm(source, "src/module.py", "mapper")["algorithm"]
        reasons = " ".join(item["reason"] for item in algorithm["omissions"])
        self.assertIn("lambda", reasons.lower())
        self.assertIn("capture", reasons.lower())

    def test_real_regex_function_is_lowered_with_rust_syntax_evidence(self):
        root = Path(__file__).resolve().parents[2] / ".local/real-projects/regex"
        path = root / "regex-automata/src/nfa/thompson/backtrack.rs"
        algorithm = extract_rust_algorithm(path.read_bytes(), "regex-automata/src/nfa/thompson/backtrack.rs",
                                           "min_visited_capacity")["algorithm"]
        self.assertEqual(validate_algorithms({"schema_version": "1.0.0", "algorithms": [algorithm]}), [])
        self.assertTrue(algorithm["contract"]["inputs"])
        source = path.read_bytes()
        self.assertTrue(all(source[step["source"]["start_byte"]:step["source"]["end_byte"]]
                            for step in algorithm["body"]["steps"]))

    def test_real_click_function_is_lowered_with_source_checked_step_spans(self):
        root = Path(__file__).resolve().parents[2] / ".local/real-projects/click"
        path = root / "examples/naval/naval.py"
        algorithm = extract_python_algorithm(path.read_bytes(), "examples/naval/naval.py", "ship_move")["algorithm"]
        self.assertEqual(validate_algorithms({"schema_version": "1.0.0", "algorithms": [algorithm]}), [])
        source = path.read_bytes()
        self.assertTrue(algorithm["body"]["steps"])
        self.assertTrue(all(source[step["source"]["start_byte"]:step["source"]["end_byte"]]
                            for step in algorithm["body"]["steps"]))

    def test_schema_is_valid_2020_12_and_rejects_unknown_fields(self):
        schema_path = Path(__file__).resolve().parents[1] / "contracts/semantic-algorithm.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        document = _algorithm()
        document["algorithms"][0]["body"]["steps"][0]["untyped_guess"] = True
        self.assertTrue(any(item["code"] == "SCHEMA_INVALID" for item in validate_algorithms(document)))

    def test_operation_contract_requires_evidence_state_for_every_category(self):
        document = _algorithm()
        contract = document["algorithms"][0]["contract"]
        contract["coverage"] = [entry for entry in contract["coverage"] if entry["category"] != "effects"]
        self.assertIn("CONTRACT_COVERAGE_INCOMPLETE",
                      {item["code"] for item in validate_algorithms(document)})

    def test_unknown_contract_category_requires_reason_and_keeps_error_distinct(self):
        document = _algorithm()
        contract = document["algorithms"][0]["contract"]
        contract["coverage"][2] = {"category": "preconditions", "state": "unknown",
                                    "evidence_refs": ["ev:1"], "reason": "dynamic input validation"}
        contract["outcomes"].append({"kind": "termination", "description": "May exit process",
                                     "condition": {"kind": "unknown", "reason": "indirect call"},
                                     "evidence_refs": ["ev:2"]})
        self.assertEqual(validate_algorithms(document), [])
        contract["coverage"][2].pop("reason")
        self.assertIn("SCHEMA_INVALID", {item["code"] for item in validate_algorithms(document)})

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

    def test_algorithm_constructor_catalog_and_ownership_are_explicit(self):
        kinds = ("sequence", "bind", "assign", "compute", "select", "loop", "call", "return", "raise",
                 "handle", "resource", "concurrent", "synchronize", "unknown", "opaque")
        steps = []
        for index, kind in enumerate(kinds):
            step = {"step_id": f"s{index}", "kind": kind, "region_id": "root", "evidence_refs": ["ev"],
                    "source": {"path": "src.py", "start_byte": index, "end_byte": index + 1}}
            if kind == "compute":
                step["attributes"] = {"operation": "unknown", "type_rule": "unknown", "evaluation_order": "unknown"}
            if kind == "opaque":
                step.update({"impact": "Unknown syntax", "unknowns": ["semantics"],
                             "boundary": {"inputs": [], "outputs": [], "effects": ["unknown"]}})
            steps.append(step)
        document = _algorithm(steps=steps, control_edges=[], data_edges=[])
        document["algorithms"][0]["management"] = {"status": "ambiguous", "project_subject_ids": ["project:a", "project:b"]}
        document["algorithms"][0]["implementation_refs"].append({"subject_id": "subject:other"})

        self.assertEqual(validate_algorithms(document), [])

    def test_algorithm_management_candidate_cardinality_is_validated(self):
        document = _algorithm()
        document["algorithms"][0]["management"] = {"status": "ambiguous", "project_subject_ids": ["project:a"]}

        codes = {item["code"] for item in validate_algorithms(document)}

        self.assertIn("MANAGEMENT_PROJECT_CARDINALITY", codes)

    def test_algorithm_projection_maps_each_rendered_step_and_keeps_gaps(self):
        document = _algorithm()
        algorithm = document["algorithms"][0]
        algorithm["omissions"] = [{"reason": "Calls are unresolved", "impact": "Effects remain unknown"}]
        algorithm["contract"]["coverage"][0].update({"state": "partial", "reason": "Only syntax inputs are listed"})

        result = project_algorithm(document, {"algorithm_id": "alg:run"})

        self.assertEqual({item["stepId"] for item in result["stepMappings"]}, {"s1", "s2"})
        self.assertIn("compute", result["text"])
        self.assertTrue(result["gaps"])

    def test_source_checklist_review_gate_and_deleted_step_detection(self):
        document = _algorithm()
        empty = check_source_coverage(document, {"reviewed": True, "items": []})
        self.assertTrue(empty["uncoveredItems"])
        checklist = {"reviewed": False, "items": [{"itemId": "error-exit", "description": "Failure exit",
            "stepIds": ["s2"], "effectIndices": [], "gapReason": None}]}

        unreviewed = check_source_coverage(document, checklist)
        self.assertFalse(unreviewed["reviewed"])
        self.assertEqual([item["itemId"] for item in unreviewed["uncoveredItems"]], ["error-exit"])

        checklist["reviewed"] = True
        self.assertEqual(check_source_coverage(document, checklist)["uncoveredItems"], [])
        document["algorithms"][0]["body"]["steps"].pop()
        document["algorithms"][0]["body"]["control_edges"] = []
        document["algorithms"][0]["body"]["data_edges"] = []
        text = project_algorithm(document, {"algorithm_id": "alg:run"})["text"]
        self.assertNotIn("s2", text)
        deleted = check_source_coverage(document, checklist)
        self.assertEqual([item["itemId"] for item in deleted["uncoveredItems"]], ["error-exit"])

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
