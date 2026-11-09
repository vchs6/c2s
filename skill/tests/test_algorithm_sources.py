import json
import subprocess
import unittest
from pathlib import Path

from c2s_skill.algorithm import _index_rust_functions, extract_python_algorithm, extract_rust_algorithm
from c2s_semantic_contract.algorithm_projection import check_source_coverage, project_algorithm


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads((Path(__file__).parent / "fixtures/algorithm-source-checklists.json").read_text())


class RealSourceChecklistTests(unittest.TestCase):
    def _verify_source(self, case):
        project = ROOT / case["project"]
        if not project.is_dir():
            self.skipTest(f"fixed project checkout unavailable: {case['project']}")
        revision = subprocess.run(["git", "-C", str(project), "rev-parse", "HEAD"], check=True,
                                  capture_output=True, text=True).stdout.strip()
        self.assertEqual(revision, case["commit"])
        source = (project / case["path"]).read_bytes()
        lines = source.decode("utf-8").splitlines()
        for item in case["items"]:
            excerpt = "\n".join(lines[item["startLine"] - 1:item["endLine"]])
            for needle in item["needles"]:
                self.assertIn(needle, excerpt, item["itemId"])
        return project, source

    def _manual_cpp_bundle(self, case, source):
        raw_lines = source.splitlines(keepends=True)
        offsets = [0]
        for line in raw_lines:
            offsets.append(offsets[-1] + len(line))
        steps = []
        impacts = {
            "sax-entry": "invoke sax_parse_internal and branch on its result",
            "sax-failure": "return false when the internal parser fails",
            "strict-error": "propagate the bool returned by syntax_error for trailing input",
            "lookahead-release": "release lexer lookahead so the caller can continue",
            "receiver-error-result": "return the receiver parse_error result unchanged",
        }
        for item in case["items"]:
            start = offsets[item["startLine"] - 1]
            end = offsets[item["endLine"]]
            for step_id in item["stepIds"]:
                steps.append({"step_id": step_id, "kind": "opaque", "region_id": "root",
                    "evidence_refs": [f"C5:{item['startLine']}-{item['endLine']}"],
                    "source": {"path": case["path"], "start_byte": start, "end_byte": end},
                    "impact": impacts[step_id], "unknowns": ["C++ type and callback behavior beyond this source span"],
                    "boundary": {"inputs": [], "outputs": [], "effects": ["receiver/input state"]}})
        evidence = ["C5:source-review"]
        categories = ("inputs", "outputs", "preconditions", "outcomes", "effects", "ordering")
        algorithm = {"algorithm_id": "alg:nlohmann:sax_parse", "purpose": "current_implementation",
            "problem": "Strict and non-strict SAX parse completion", "management": {
                "status": "unresolved", "project_subject_ids": []},
            "body": {"regions": [{"region_id": "root", "parent_region_id": None}], "steps": steps,
                     "control_edges": [], "data_edges": []},
            "contract": {"inputs": [], "outputs": [], "preconditions": [],
                "outcomes": [{"kind": "error", "description": "Strict trailing input returns the SAX parse_error callback result unchanged.",
                    "condition": {"kind": "unknown", "reason": "strict parser path selected by caller"}, "evidence_refs": evidence}],
                "effects": [{"kind": "external", "description": "Invokes SAX callbacks and may release lexer lookahead.",
                    "condition": {"kind": "unknown", "reason": "receiver and input state are external"}, "evidence_refs": evidence}],
                "ordering_constraints": [], "coverage": [{"category": category, "state": "complete",
                    "evidence_refs": evidence} for category in categories]},
            "implementation_refs": [{"subject_id": "subject:nlohmann:parser"}], "evidence_refs": evidence,
            "omissions": [{"reason": "C++ syntax lowering is not implemented; this is a manually source-reviewed fixture.",
                           "impact": "No project-wide C++ algorithm inference is claimed."}]}
        return {"schema_version": "1.0.0", "algorithms": [algorithm]}

    def test_rust_regex_visitor_source_checklist_maps_supported_steps(self):
        case = FIXTURE["R5"]
        project, source = self._verify_source(case)
        path = case["path"]
        _, functions = _index_rust_functions(source)
        starts = [start for start, node in functions.items()
                  if node.child_by_field_name("name").text.decode() == "visit"
                  and source[node.start_byte:node.end_byte].find(b"self.stack_class.clear()") >= 0]
        self.assertEqual(len(starts), 1)
        document = extract_rust_algorithm(source, path, "visit", start_byte=starts[0])
        checklist = {"reviewed": case["reviewed"], "items": case["items"]}
        bundle = {"schema_version": "1.0.0", "algorithms": [document["algorithm"]]}
        coverage = check_source_coverage(bundle, checklist)
        self.assertEqual(coverage["uncoveredItems"], [])
        projection = project_algorithm(bundle, {"algorithm_id": document["algorithm"]["algorithm_id"]})
        self.assertTrue(projection["stepMappings"])
        self.assertTrue(projection["gaps"])

    def test_click_unpack_args_checklist_catches_wildcard_and_zero_cases(self):
        case = FIXTURE["P7"]
        _, source = self._verify_source(case)
        document = extract_python_algorithm(source, case["path"], "_unpack_args")
        coverage = check_source_coverage({"algorithms": [document["algorithm"]]},
                                         {"reviewed": case["reviewed"], "items": case["items"]})
        self.assertEqual(coverage["uncoveredItems"], [])
        self.assertEqual({item["itemId"] for item in coverage["declaredGaps"]},
                         {"fetch-direction-helper", "zero-count-no-op"})
        text = project_algorithm({"schema_version": "1.0.0", "algorithms": [document["algorithm"]]},
                                 {"algorithm_id": document["algorithm"]["algorithm_id"]})["text"]
        self.assertIn("raise", text)
        self.assertIn("loop", text)

    def test_cpp_sax_source_is_preserved_as_an_explicit_unsupported_gap(self):
        case = FIXTURE["C5"]
        _, source = self._verify_source(case)
        document = self._manual_cpp_bundle(case, source)
        coverage = check_source_coverage(document, {"reviewed": case["reviewed"], "items": case["items"]})
        self.assertEqual(coverage["uncoveredItems"], [])
        self.assertEqual(coverage["declaredGaps"], [])
        text = project_algorithm(document, {"algorithm_id": "alg:nlohmann:sax_parse"})["text"]
        self.assertIn("return the receiver parse_error result unchanged", text)
        self.assertIn("C++ syntax lowering is not implemented", text)


if __name__ == "__main__":
    unittest.main()
