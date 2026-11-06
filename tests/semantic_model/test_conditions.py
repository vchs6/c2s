import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from c2s_semantic_contract.conditions import (classify_claim_overlap, condition_satisfiability,
                                             diagnose_conditional_cycles)


class FiniteConditionTests(unittest.TestCase):
    def test_cycle_conditions_are_solved_jointly_and_original_edges_are_retained(self):
        edges = [
            {"edgeId": "ab", "source": "a", "target": "b",
             "condition": {"kind": "eq", "key": "x", "value": "A"}},
            {"edgeId": "ba", "source": "b", "target": "a",
             "condition": {"kind": "eq", "key": "x", "value": "B"}},
        ]

        result = diagnose_conditional_cycles(edges, {"x": ["A", "B"]})

        self.assertEqual(result["cycles"][0]["status"], "infeasible")
        self.assertEqual(result["cycles"][0]["edgeIds"], ["ab", "ba"])
        self.assertEqual(result["edges"], edges)

    def test_cycle_with_joint_witness_is_possible(self):
        edges = [
            {"edgeId": "ab", "source": "a", "target": "b", "condition": {"kind": "true"}},
            {"edgeId": "ba", "source": "b", "target": "a", "condition": {"kind": "eq", "key": "x", "value": True}},
        ]

        result = diagnose_conditional_cycles(edges, {"x": [True, False]})

        self.assertEqual(result["cycles"][0]["status"], "possible")
        self.assertEqual(result["cycles"][0]["witness"], {"x": True})

    def test_unknown_cycle_condition_stays_undetermined(self):
        edges = [
            {"edgeId": "ab", "source": "a", "target": "b", "condition": {"kind": "source", "expression": "cfg(x)"}},
            {"edgeId": "ba", "source": "b", "target": "a", "condition": {"kind": "true"}},
        ]

        result = diagnose_conditional_cycles(edges, {})

        self.assertEqual(result["cycles"][0]["status"], "undetermined")
        self.assertEqual(result["cycles"][0]["reason"], "CONDITION_UNSUPPORTED_FRAGMENT")

    def test_shared_enum_key_distinguishes_sat_and_unsat_with_witnesses(self):
        domains = {"target": ["linux", "windows"]}
        same = {"kind": "eq", "key": "target", "value": "linux"}
        other = {"kind": "eq", "key": "target", "value": "windows"}

        self.assertEqual(condition_satisfiability([same], domains)["status"], "sat")
        conflict = condition_satisfiability([same, other], domains)
        self.assertEqual(conflict["status"], "unsat")
        witness = condition_satisfiability([same], domains)["witness"]
        self.assertEqual(witness, {"target": "linux"})

    def test_boolean_condition_operators_use_three_valued_results(self):
        domains = {"enabled": [False, True]}
        expression = {"kind": "all", "conditions": [
            {"kind": "eq", "key": "enabled", "value": True},
            {"kind": "not", "condition": {"kind": "eq", "key": "enabled", "value": False}}]}
        self.assertEqual(condition_satisfiability([expression], domains)["status"], "sat")

    def test_unknown_domains_and_budget_overflow_remain_undetermined(self):
        unknown = condition_satisfiability([{"kind": "eq", "key": "missing", "value": "x"}], {})
        self.assertEqual(unknown["status"], "undetermined")
        domains = {f"key-{index}": [False, True] for index in range(13)}
        exceeded = condition_satisfiability([{"kind": "true"}], domains)
        self.assertEqual(exceeded["status"], "undetermined")
        self.assertEqual(exceeded["reason"], "CONDITION_BUDGET_EXCEEDED")

    def test_budget_includes_exactly_4096_assignments(self):
        domains = {f"key-{index}": [False, True] for index in range(12)}
        result = condition_satisfiability([{"kind": "true"}], domains)
        self.assertEqual(result["status"], "sat")
        self.assertIsNone(result["reason"])

    def test_malformed_domains_and_unsupported_condition_nodes_are_not_treated_as_false(self):
        malformed = condition_satisfiability([{"kind": "true"}], {"x": [["unhashable"]]})
        self.assertEqual(malformed["status"], "undetermined")
        unsupported = condition_satisfiability([{"kind": "source", "digest": "abc"}], {})
        self.assertEqual(unsupported["status"], "undetermined")
        self.assertEqual(unsupported["reason"], "CONDITION_UNSUPPORTED_FRAGMENT")

    def test_claim_overlap_separates_disjoint_conflicting_and_unknown_conditions(self):
        linux = {"kind": "eq", "key": "target", "value": "linux"}
        windows = {"kind": "eq", "key": "target", "value": "windows"}
        domains = {"target": ["linux", "windows"]}
        left = {"value": "name-a", "condition": linux}
        disjoint = {"value": "name-b", "condition": windows}
        overlapping = {"value": "name-b", "condition": linux}
        unknown = {"value": "name-b", "condition": {"kind": "source", "id": "condition-a"}}

        self.assertEqual(classify_claim_overlap(left, disjoint, domains)["status"], "compatible")
        self.assertEqual(classify_claim_overlap(left, overlapping, domains)["status"], "conflict")
        self.assertEqual(classify_claim_overlap(left, unknown, domains)["status"], "potential_conflict")

    def test_empty_all_and_any_follow_boolean_identity(self):
        self.assertEqual(condition_satisfiability([{"kind": "all", "conditions": []}], {})["status"], "sat")
        self.assertEqual(condition_satisfiability([{"kind": "any", "conditions": []}], {})["status"], "unsat")


if __name__ == "__main__":
    unittest.main()
