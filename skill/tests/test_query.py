import unittest
import os
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from jsonschema import Draft202012Validator

from c2s_skill.acquisition import cargo_workspace_facts, scan_project
from c2s_skill.query import normalize_request, query_from_scan, query_project, result_to_dict, result_to_markdown


class QueryTests(unittest.TestCase):
    def test_workspace_members_uses_native_cargo_metadata_without_resolving_dependencies(self):
        cargo = Path(__file__).resolve().parents[2] / ".local/cargo/bin/cargo"
        if not cargo.is_file():
            self.skipTest("local Cargo toolchain is unavailable")
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "crates/a/src").mkdir(parents=True)
            (root / "crates/b/src").mkdir(parents=True)
            (root / "Cargo.toml").write_text('[workspace]\nmembers = ["crates/*"]\nresolver = "2"\n')
            for name in ("a", "b"):
                (root / "crates" / name / "Cargo.toml").write_text(
                    f'[package]\nname = "{name}"\nversion = "0.1.0"\nedition = "2021"\n')
                (root / "crates" / name / "src/lib.rs").write_text("pub fn value() {}\n")
            env = {"CARGO": str(cargo), "RUSTUP_HOME": str(cargo.parents[2] / "rustup"),
                   "CARGO_HOME": str(cargo.parents[1])}
            with patch.dict(os.environ, env):
                result = query_project(root, ["workspace-members"])
            self.assertTrue(result.complete)
            self.assertEqual({fact.name for fact in result.facts}, {"a", "b"})
            self.assertTrue(all(fact.kind == "workspace_member" and fact.layer == "E1"
                                for fact in result.facts))
    def test_malformed_target_selector_fails_before_source_acquisition(self):
        with TemporaryDirectory() as temporary:
            with patch("c2s_skill.query.scan_project", side_effect=AssertionError("scan must not start")):
                with self.assertRaisesRegex(ValueError, "requires a target"):
                    query_project(Path(temporary), ["function:"])

    def test_missing_target_selectors_return_explicit_gaps(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "api.py").write_text("class Existing:\n    def actual(self): pass\n")
            missing_function = query_project(root, ["function:missing"])
            missing_class = query_project(root, ["members:Missing"])
            self.assertFalse(missing_function.complete)
            self.assertIn("SUBJECT_NOT_FOUND:function:missing", {gap.reason for gap in missing_function.gaps})
            self.assertFalse(missing_class.complete)
            self.assertIn("SUBJECT_NOT_FOUND:members:Missing", {gap.reason for gap in missing_class.gaps})

    def test_natural_request_resolves_explicit_class_and_member_queries(self):
        self.assertEqual(normalize_request("有哪些类"), ["classes"])
        self.assertEqual(normalize_request("Command 的成员有哪些"), ["members:Command"])
        self.assertEqual(normalize_request("函数如何实现"), ["unrecognized:函数如何实现"])

    def test_class_request_returns_all_matching_top_level_facts_without_members(self):
        root = Path(__file__).resolve().parents[2] / ".local/real-projects/click"
        result = query_project(root, ["classes"])
        self.assertTrue(result.facts)
        self.assertTrue(all(fact.kind in {"class", "struct", "enum", "trait"} for fact in result.facts))
        self.assertTrue(result.complete)
        self.assertEqual(result.requested, ("classes",))

    def test_type_and_function_lists_do_not_disclose_unrequested_bodies(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "api.py").write_text(
                "class Sample:\n    def method(self):\n        return secret()\ndef run():\n    return hidden()\n",
                encoding="utf-8")
            classes = query_project(root, ["classes"])
            functions = query_project(root, ["functions"])
            self.assertFalse(any("def method" in fact.text or "secret" in fact.text for fact in classes.facts))
            self.assertFalse(any("hidden" in fact.text for fact in functions.facts))
            self.assertTrue(all(not fact.evidence_included for fact in classes.facts + functions.facts))
            definition = query_project(root, ["function:run"])
            self.assertIn("hidden", next(fact.text for fact in definition.facts))

    def test_unknown_selector_is_preserved_as_a_gap(self):
        root = Path(__file__).resolve().parents[2] / ".local/real-projects/click"
        result = query_project(root, ["classes", "not-a-supported-selector"])
        self.assertIn("not-a-supported-selector", result.requested)
        self.assertFalse(result.complete)
        self.assertTrue(any(gap.selector == "not-a-supported-selector" for gap in result.gaps))

    def test_json_and_markdown_are_views_of_the_same_fact_ids(self):
        root = Path(__file__).resolve().parents[2] / ".local/real-projects/click"
        result = query_project(root, ["functions"])
        structured = result_to_dict(result)
        markdown = result_to_markdown(result)
        for fact in structured["facts"]:
            self.assertIn(f"`{fact['id']}`", markdown)
            self.assertIn(f"subject `{fact['subject_id']}`", markdown)
            self.assertIn(f"`{fact['kind']}` **{fact['name']}**", markdown)
            self.assertTrue(all(f"> {line}" in markdown or line == "" for line in fact["text"].splitlines()))
        self.assertEqual(structured["gaps"], [])

    def test_json_and_markdown_disclose_unhandled_project_paths(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "module.py").write_text("value = 1\n", encoding="utf-8")
            (root / "design.md").write_text("requirements", encoding="utf-8")
            result = query_project(root, ["all-supported-facts"])
            structured = result_to_dict(result)
            self.assertIn({"path": "design.md", "kind": "file", "state": "readable", "diagnostic": None,
                           "reason": "UNSUPPORTED_FILE_TYPE"},
                          structured["coverage"]["unhandled_paths"])
            self.assertIn("`design.md` (file, readable, UNSUPPORTED_FILE_TYPE)", result_to_markdown(result))
            self.assertIn("1 unhandled path", result_to_markdown(result))

    def test_all_declarations_returns_every_fact_from_every_supported_source_file(self):
        for project in ("click", "regex"):
            with self.subTest(project=project):
                root = Path(__file__).resolve().parents[2] / ".local/real-projects" / project
                if not (root / ".git").exists():
                    self.skipTest(f"pinned {project} project is unavailable")
                scan = scan_project(root)
                result = query_project(root, ["all-declarations"])
                expected = sum(fact.kind in {"class", "struct", "enum", "trait", "field", "variant", "function",
                                               "constant", "constant_item", "static_item", "type_alias", "module", "impl", "import"}
                               for parsed in scan.files for fact in parsed.facts)
                self.assertEqual(len(result.facts), expected)
                self.assertEqual(result.parsed_files, result.source_files)
                self.assertTrue(result.complete)

    def test_all_supported_facts_returns_every_emitted_fact_for_both_real_projects(self):
        for project in ("click", "regex"):
            with self.subTest(project=project):
                root = Path(__file__).resolve().parents[2] / ".local/real-projects" / project
                scan = scan_project(root)
                cargo = Path(__file__).resolve().parents[2] / ".local/cargo/bin/cargo"
                if project == "regex" and cargo.is_file():
                    env = {"CARGO": str(cargo), "RUSTUP_HOME": str(cargo.parents[2] / "rustup"),
                           "CARGO_HOME": str(cargo.parents[1])}
                    with patch.dict(os.environ, env):
                        workspace_facts, workspace_gap = cargo_workspace_facts(root)
                        result = query_project(root, ["all-supported-facts"])
                else:
                    workspace_facts, workspace_gap = [], None
                    result = query_project(root, ["all-supported-facts"])
                expected = sum(len(parsed.facts) for parsed in scan.files) + len(scan.project_facts)
                expected += len(workspace_facts)
                self.assertEqual(len(result.facts), expected)
                self.assertEqual(len({fact.id for fact in result.facts}), expected)
                self.assertTrue(result.complete)
                self.assertIsNone(workspace_gap)
                schema_path = Path(__file__).resolve().parents[1] / "contracts/semantic-fact-query.schema.json"
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                Draft202012Validator(schema).validate(result_to_dict(result))

    def test_function_selector_projects_every_real_function_subject_completely(self):
        repository = Path(__file__).resolve().parents[2]
        for project in ("click", "regex"):
            with self.subTest(project=project):
                root = repository / ".local/real-projects" / project
                scan = scan_project(root)
                all_facts = [fact for parsed in scan.files for fact in parsed.facts] + list(scan.project_facts)
                declarations = [fact for fact in all_facts if fact.kind == "function"]
                self.assertTrue(declarations)
                targets = {(f"{fact.owner}.{fact.name}" if fact.owner else fact.name)
                           for fact in declarations}
                selectors = [f"function:{target}" for target in sorted(targets)]
                subjects = {fact.subject_id for fact in declarations
                            if fact.name in targets or f"{fact.owner}.{fact.name}" in targets}
                expected = {fact.id for fact in all_facts
                            if fact.subject_id in subjects and fact.kind in
                            {"function", "behavior_contract", "algorithm_step", "local_binding"}}
                result = query_from_scan(scan, selectors)
                self.assertTrue(result.complete, project)
                self.assertEqual({fact.id for fact in result.facts}, expected, project)

    def test_members_selector_scopes_fields_and_methods_to_the_requested_class(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "a.py").write_text("class Wanted:\n    value: int\n    def read(self): pass\nclass Other:\n    ignored: str\n")
            result = query_project(root, ["members:Wanted"])
            self.assertEqual({fact.name for fact in result.facts}, {"value", "read"})

    def test_project_selector_returns_explicit_project_name_and_language_declaration(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "pyproject.toml").write_text('[project]\nname = "sample-app"\nrequires-python = ">=3.11"\n')
            result = query_project(root, ["project"])
            self.assertEqual({fact.name for fact in result.facts}, {"sample-app", "Python"})
            self.assertEqual({fact.kind for fact in result.facts}, {"project_name", "language_declared"})

    def test_project_selector_reports_missing_explicit_metadata(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "pyproject.toml").write_text('[project]\nname = "sample-app"\n')
            result = query_project(root, ["project"])
            self.assertFalse(result.complete)
            self.assertIn("PROJECT_FACT_UNAVAILABLE:language_declared", {gap.reason for gap in result.gaps})

    def test_workspace_request_reports_missing_native_metadata_tool(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Cargo.toml").write_text('[workspace]\nmembers = ["crates/*"]\n')
            result = query_project(root, ["workspace-members"])
            self.assertFalse(result.complete)
            self.assertTrue(any("TOOL_UNAVAILABLE:cargo" == gap.reason for gap in result.gaps))

    def test_all_supported_facts_reports_missing_cargo_metadata_instead_of_claiming_complete(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Cargo.toml").write_text('[workspace]\nmembers = []\n')
            with patch.dict(os.environ, {"PATH": "", "CARGO": ""}):
                result = query_project(root, ["all-supported-facts"])
            self.assertFalse(result.complete)
            self.assertTrue(any(gap.selector == "all-supported-facts" and gap.reason == "TOOL_UNAVAILABLE:cargo"
                                for gap in result.gaps))

    def test_function_selector_returns_only_the_selected_function_and_its_body_facts(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "functions.py").write_text(
                'def run(value):\n    """Return a transformed value."""\n    result = helper(value + 1)\n    return result\n\n'
                'def other():\n    return unrelated()\n', encoding="utf-8")
            result = query_project(root, ["function:run"])
            self.assertEqual({fact.kind for fact in result.facts},
                             {"function", "behavior_contract", "algorithm_step", "local_binding"})
            self.assertTrue(any(fact.name == "Assign" for fact in result.facts))
            self.assertTrue(any(fact.name == "Return" for fact in result.facts))
            self.assertFalse(any("unrelated" in fact.text for fact in result.facts))
            subjects = {fact.subject_id for fact in result.facts}
            self.assertEqual(len(subjects), 1)
            self.assertTrue(result.complete)

    def test_local_bindings_have_a_dedicated_selector_and_function_projection(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "bindings.py").write_text(
                "def run(value):\n    result = helper(value)\n    return result\n\n"
                "def other():\n    ignored = unrelated()\n", encoding="utf-8")
            bindings = query_project(root, ["local-bindings"])
            self.assertTrue(bindings.complete)
            self.assertEqual({fact.kind for fact in bindings.facts}, {"local_binding"})
            self.assertEqual({fact.name for fact in bindings.facts}, {"result", "ignored"})
            selected = query_project(root, ["function:run"])
            self.assertIn("local_binding", {fact.kind for fact in selected.facts})
            self.assertNotIn("ignored", {fact.name for fact in selected.facts
                                         if fact.kind == "local_binding"})

    def test_nested_function_steps_keep_the_nested_function_subject(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "nested.py").write_text(
                "def outer():\n    def inner():\n        return hidden()\n    return inner()\n",
                encoding="utf-8")
            outer = query_project(root, ["function:outer"])
            self.assertFalse(any(fact.kind == "algorithm_step" and "hidden" in fact.text for fact in outer.facts))
            self.assertTrue(any("inner()" in fact.text for fact in outer.facts))
            inner = query_project(root, ["function:inner"])
            self.assertTrue(any("hidden()" in fact.text for fact in inner.facts))
            outer_id = next(f.subject_id for f in outer.facts if f.kind == "function")
            inner_id = next(f.subject_id for f in inner.facts if f.kind == "function")
            self.assertNotEqual(outer_id, inner_id)

    def test_behavior_contract_query_returns_only_source_documented_contracts(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "docs.py").write_text('def run():\n    """Return the parsed value."""\n    return 1\n')
            result = query_project(root, ["behavior-contracts"])
            self.assertEqual(len(result.facts), 1)
            self.assertEqual(result.facts[0].kind, "behavior_contract")
            self.assertEqual(result.facts[0].claim_mode, "documentation")
            self.assertEqual(result.facts[0].layer, "E3")


if __name__ == "__main__":
    unittest.main()
