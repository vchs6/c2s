from __future__ import annotations

import unittest

from c2s_skill.semantic_entity_query import (query_entity_store, query_semantic_entities,
                                             render_entity_query)


def archive():
    project = {"identity": {"authority": "test", "domainId": "scope-a", "localId": "p"}, "kind": "Project"}
    module = {"identity": {"authority": "test", "domainId": "scope-a", "localId": "m"}, "kind": "Module"}
    data = {"identity": {"authority": "test", "domainId": "scope-a", "localId": "d"}, "kind": "DataEntity"}
    return {"version": "1.0.0", "profile": "semantic-entity-model-1", "scopeId": "scope-a",
        "entities": [
            {"ref": project, "name": "项目", "aliases": [], "description": "", "attributes": [],
             "sourceKeys": [], "observationViews": ["E0"]},
            {"ref": module, "name": "模块", "aliases": [], "description": "", "attributes": [],
             "sourceKeys": [], "observationViews": ["E1"]},
            {"ref": data, "name": "订单", "aliases": [], "description": "", "attributes": [
                {"attributeId": "status", "name": "状态", "semanticType": "unknown",
                 "valueRange": {"kind": "unknown"}, "cardinality": "one", "constraints": [],
                 "evidenceIds": []}], "sourceKeys": ["src:order"], "observationViews": ["E2"]}],
        "claims": [], "relations": [
            {"relationId": "r1", "predicate": "defines", "subject": project, "target": module,
             "evidenceIds": [], "condition": {"kind": "true"}},
            {"relationId": "r2", "predicate": "contains", "subject": module, "target": data,
             "evidenceIds": [], "condition": {"kind": "true"}}],
        "continuityCandidates": [], "evidence": [], "coverage": []}


class SemanticEntityQueryTests(unittest.TestCase):
    def test_project_listing_returns_direct_child_refs_without_recursive_details(self):
        result = query_semantic_entities(archive(), "project")
        self.assertEqual(result["status"], "obtained")
        self.assertEqual([item["name"] for item in result["members"]], ["模块"])
        self.assertNotIn("attributes", result["members"][0])

    def test_entity_details_return_all_attributes_and_child_refs_once(self):
        result = query_semantic_entities(archive(), "entity:m")
        self.assertEqual(result["status"], "obtained")
        self.assertEqual(result["entity"]["attributes"], [])
        self.assertEqual([item["name"] for item in result["members"]], ["订单"])
        self.assertNotIn("attributes", result["members"][0])

    def test_explicit_expand_returns_child_attributes(self):
        result = query_semantic_entities(archive(), "expand:m")
        self.assertEqual(result["expandedMembers"][0]["entity"]["attributes"][0]["name"], "状态")

    def test_unknown_and_ambiguous_targets_remain_distinct_gaps(self):
        missing = query_semantic_entities(archive(), "entity:missing")
        self.assertEqual(missing["status"], "not_found")
        data = archive()
        duplicate = dict(data["entities"][2])
        duplicate["ref"] = {"identity": {"authority": "other", "domainId": "scope-a", "localId": "d"},
                             "kind": "DataEntity"}
        data["entities"].append(duplicate)
        ambiguous = query_semantic_entities(data, "entity:d")
        self.assertEqual(ambiguous["status"], "ambiguous")

    def test_structured_request_is_schema_checked_and_reads_isolated_store(self):
        class Store:
            def read(self, scope_id):
                return archive() if scope_id == "scope-a" else None
        request = {"version": "1.0.0", "profile": "semantic-entity-query-1", "scopeId": "scope-a",
                   "selector": "entity:d"}
        self.assertEqual(query_entity_store(Store(), request)["entity"]["name"], "订单")
        request["ignored"] = True
        with self.assertRaises(ValueError):
            query_entity_store(Store(), request)

    def test_chinese_request_resolves_project_and_entity_details(self):
        result = query_semantic_entities(archive(), "项目都定义了哪些语义实体")
        self.assertEqual(result["status"], "obtained")
        detail = query_semantic_entities(archive(), "查询订单实体的属性")
        self.assertEqual(detail["entity"]["name"], "订单")

    def test_json_and_markdown_render_the_same_attributes_relations_and_gaps(self):
        result = query_semantic_entities(archive(), "entity:d")
        encoded = render_entity_query(result, "json")
        markdown = render_entity_query(result, "markdown")
        self.assertIn('"status": "obtained"', encoded)
        self.assertIn("## 属性：状态", markdown)
        self.assertIn('"localId": "d"', encoded)
        self.assertIn('"localId": "d"', markdown)
        self.assertIn("状态", markdown)


if __name__ == "__main__":
    unittest.main()
