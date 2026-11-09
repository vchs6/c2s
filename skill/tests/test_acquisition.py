from real_project_support import require_real_project
import unittest
import tempfile
from pathlib import Path

from c2s_skill.acquisition import parse_source, scan_project


class AcquisitionTests(unittest.TestCase):
    def test_python_source_constructs_cover_declarations_fields_generics_decorators_and_lambda(self):
        source = (b"@decorate(flag=True)\n"
                  b"class Box[T]:\n"
                  b"    value: str\n"
                  b"    def map(self, fn):\n"
                  b"        return lambda item: fn(item)\n")
        result = parse_source("box.py", source, "python")
        constructs = {item.syntax_kind: item for item in result.constructs}
        self.assertTrue({"class_declaration", "field_declaration", "function_declaration",
                         "generic_parameter", "decorator_application", "lambda_expression"} <= set(constructs))
        self.assertEqual(source[constructs["lambda_expression"].start_byte:
                                constructs["lambda_expression"].end_byte], b"lambda item: fn(item)")
        self.assertEqual(constructs["function_declaration"].parent_id,
                         constructs["class_declaration"].construct_id)

    def test_python_chained_class_assignments_have_one_field_construct_per_member(self):
        source = b"class Pair:\n    left = right = 1\n"
        result = parse_source("pair.py", source, "python")
        fields = [item for item in result.constructs if item.syntax_kind == "field_declaration"]
        self.assertEqual([item.name for item in fields], ["left", "right"])
        self.assertEqual([item.text for item in fields], ["left", "right"])

    def test_python_enum_construct_separates_enum_type_and_members(self):
        source = b"from enum import Enum\nclass Status(Enum):\n    READY = 'ready'\n"
        result = parse_source("status.py", source, "python")
        enum_type = next(item for item in result.constructs if item.syntax_kind == "enum_declaration")
        variant = next(item for item in result.constructs if item.syntax_kind == "enum_variant")
        self.assertEqual(enum_type.name, "Status")
        self.assertEqual(variant.name, "READY")
        self.assertEqual(variant.parent_id, enum_type.construct_id)

    def test_rust_source_constructs_cover_items_members_generics_macros_attributes_and_closures(self):
        source = (b"#[derive(Debug)] struct Box<T> { value: T }\n"
                  b"enum State { Ready }\n"
                  b"macro_rules! check { () => {} }\n"
                  b"fn run() { let f = |x: i32| x + 1; check!(); }\n")
        result = parse_source("src/lib.rs", source, "rust")
        kinds = {item.syntax_kind for item in result.constructs}
        self.assertTrue({"struct_declaration", "field_declaration", "generic_parameter_list", "enum_declaration",
                         "enum_variant", "macro_definition", "macro_invocation", "attribute_application",
                         "function_declaration", "closure_expression"} <= kinds)
        self.assertNotIn("struct_item", kinds)
        for item in result.constructs:
            self.assertEqual(source[item.start_byte:item.end_byte], item.text.encode("utf-8"))

    def test_source_construct_records_language_parser_version_and_byte_location(self):
        source = "class Café:\n    value: str\n".encode("utf-8")
        result = parse_source("src.py", source, "python")
        construct = next(item for item in result.constructs if item.syntax_kind == "class_declaration")
        self.assertEqual(construct.language, "python")
        self.assertTrue(construct.parser_id)
        self.assertTrue(construct.parser_version)
        self.assertEqual(source[construct.start_byte:construct.end_byte], construct.text.encode("utf-8"))

    def test_unparseable_source_retains_an_opaque_construct_boundary(self):
        python = parse_source("broken.py", b"def broken(:\n", "python")
        self.assertFalse(python.parse_complete)
        self.assertTrue(any(item.opaque and item.syntax_kind == "opaque_file" for item in python.constructs))

        rust = parse_source("broken.rs", b"fn broken( {", "rust")
        self.assertFalse(rust.parse_complete)
        self.assertTrue(any(item.opaque and item.syntax_kind == "opaque_error" for item in rust.constructs))

    def test_python_parser_emits_nested_declarations_and_byte_spans(self):
        source = "class Café:\n    value: int\n    def read(self) -> int:\n        return 1\n"
        result = parse_source("src.py", source.encode(), "python")
        self.assertTrue(result.parse_complete)
        self.assertTrue({"class", "field", "function"} <= {fact.kind for fact in result.facts})
        method = next(f for f in result.facts if f.kind == "function" and f.name == "read")
        self.assertEqual(source.encode()[method.start_byte:method.end_byte], b"def read(self) -> int:\n        return 1")

    def test_python_parser_emits_control_flow_and_call_steps(self):
        source = b"def run(x):\n    if x:\n        return helper(x + 1)\n    return None\n"
        result = parse_source("src.py", source, "python")
        steps = [fact for fact in result.facts if fact.kind == "algorithm_step"]
        self.assertEqual({fact.name for fact in steps}, {"If", "Call", "BinOp", "Return"})

    def test_python_and_rust_emit_local_binding_and_assignment_steps(self):
        python = parse_source("src.py", b"def run(x):\n    value = x + 1\n    value += 2\n    return value\n", "python")
        python_steps = [fact for fact in python.facts if fact.kind == "algorithm_step"]
        self.assertEqual({fact.name for fact in python_steps}, {"Assign", "AugAssign", "BinOp", "Return"})

        rust = parse_source("src.rs", b"fn run(x: i32) -> i32 { let value = x + 1; value }", "rust")
        rust_steps = [fact for fact in rust.facts if fact.kind == "algorithm_step"]
        self.assertIn("let_declaration", {fact.name for fact in rust_steps})
        self.assertIn("binary_expression", {fact.name for fact in rust_steps})

    def test_python_and_rust_emit_explicit_local_binding_facts(self):
        python = parse_source("src.py", b"def run(x):\n    value = x + 1\n    value += 2\n", "python")
        python_bindings = [fact for fact in python.facts if fact.kind == "local_binding"]
        self.assertEqual([fact.name for fact in python_bindings], ["value", "value"])
        self.assertTrue(all(fact.layer == "E4" and fact.owner == "run" for fact in python_bindings))
        self.assertEqual([fact.text for fact in python_bindings], ["value", "value"])

        rust = parse_source("src.rs", b"fn run(x: i32) { let value = x + 1; let (left, right) = pair; }", "rust")
        rust_bindings = [fact for fact in rust.facts if fact.kind == "local_binding"]
        self.assertEqual([fact.name for fact in rust_bindings], ["value", "left", "right"])
        self.assertEqual(rust_bindings[0].layer, "E4")
        self.assertEqual(rust_bindings[0].owner, "run")
        self.assertEqual([fact.text for fact in rust_bindings], ["value", "left", "right"])

    def test_rust_local_binding_facts_cover_struct_tuple_struct_and_slice_patterns(self):
        source = (b"struct Point { x: i32, y: i32 }\n"
                  b"fn run(point: Point, option: Option<i32>, values: [i32; 2]) {\n"
                  b"    let Point { x, y: z } = point;\n"
                  b"    let Some(value) = option else { return; };\n"
                  b"    let [first, second] = values;\n"
                  b"}\n")
        result = parse_source("src.rs", source, "rust")
        self.assertTrue(result.parse_complete)
        bindings = [fact for fact in result.facts if fact.kind == "local_binding"]
        self.assertEqual([fact.name for fact in bindings],
                         ["x", "z", "value", "first", "second"])
        self.assertTrue(all(fact.layer == "E4" and fact.owner == "run" for fact in bindings))
        self.assertEqual(len({fact.id for fact in bindings}), len(bindings))

    def test_rust_local_binding_facts_cover_or_reference_and_captured_patterns(self):
        source = (b"enum Choice { A(i32), B(i32) }\n"
                  b"fn run(choice: Choice, borrowed: &i32, number: i32) {\n"
                  b"    let Choice::A(shared) | Choice::B(shared) = choice else { return; };\n"
                  b"    let &reference = borrowed;\n"
                  b"    let captured @ 1..=3 = number else { return; };\n"
                  b"}\n")
        result = parse_source("src.rs", source, "rust")
        self.assertTrue(result.parse_complete)
        bindings = [fact for fact in result.facts if fact.kind == "local_binding"]
        self.assertEqual([fact.name for fact in bindings], ["shared", "reference", "captured"])
        self.assertTrue(all(fact.owner == "run" and fact.layer == "E4" for fact in bindings))

    def test_python_repeated_local_binding_names_keep_distinct_source_ids(self):
        source = b"def bind(runner):\n    with runner.isolation() as (out, _, _):\n        pass\n"
        result = parse_source("src.py", source, "python")
        bindings = [fact for fact in result.facts if fact.kind == "local_binding"]
        self.assertEqual([fact.name for fact in bindings], ["out", "_", "_"])
        self.assertEqual(len({fact.id for fact in bindings}), 3)
        self.assertEqual([fact.text for fact in bindings], ["out", "_", "_"])

    def test_python_local_binding_facts_cover_loop_with_and_exception_targets(self):
        source = (b"def bind(items, manager):\n"
                  b"    for item in items:\n        pass\n"
                  b"    with manager as resource:\n        pass\n"
                  b"    try:\n        pass\n"
                  b"    except ValueError as error:\n        pass\n")
        result = parse_source("src.py", source, "python")
        bindings = [fact for fact in result.facts if fact.kind == "local_binding"]
        self.assertEqual([fact.name for fact in bindings], ["item", "resource", "error"])
        self.assertTrue(all(fact.owner == "bind" and fact.layer == "E4" for fact in bindings))

    def test_rust_parser_emits_struct_fields_and_methods(self):
        source = b"pub struct Item { pub value: u32 } impl Item { /// Return the stored value.\n pub fn read(&self) -> u32 { if self.value > 0 { helper() } else { 0 } } }"
        result = parse_source("src/lib.rs", source, "rust")
        self.assertTrue(result.parse_complete)
        self.assertEqual({fact.kind for fact in result.facts}, {"struct", "field", "impl", "function", "behavior_contract", "algorithm_step"})
        method = next(f for f in result.facts if f.kind == "function" and f.name == "read")
        self.assertEqual(method.owner, "Item")
        self.assertEqual(method.layer, "E2")
        self.assertEqual(next(f for f in result.facts if f.name == "value").owner, "Item")
        contract = next(f for f in result.facts if f.kind == "behavior_contract")
        self.assertEqual(contract.name, "read")
        self.assertEqual(contract.claim_mode, "documentation")
        self.assertTrue(any(f.kind == "algorithm_step" and f.name == "if_expression" for f in result.facts))
        self.assertTrue(any(f.kind == "algorithm_step" and f.name == "call_expression" for f in result.facts))
        method_subject = next(f.subject_id for f in result.facts if f.kind == "function" and f.name == "read")
        self.assertEqual({f.subject_id for f in result.facts
                          if f.kind in {"function", "behavior_contract", "algorithm_step"}
                          and (f.name == "read" or f.owner == "Item.read")}, {method_subject})

    def test_python_function_contract_and_algorithm_facts_share_subject_identity(self):
        source = b'class Component:\n    def run(self):\n        """Return a value."""\n        return helper()\n'
        result = parse_source("api.py", source, "python")
        declaration = next(f for f in result.facts if f.kind == "function" and f.name == "run")
        related = [f for f in result.facts if f.kind in {"behavior_contract", "algorithm_step"}]
        self.assertTrue(related)
        self.assertTrue(all(f.subject_id == declaration.subject_id for f in related))

    def test_python_algorithm_facts_exclude_decorator_calls(self):
        source = b'@command("move")\n@option("--speed", default=10)\ndef move():\n    return helper()\n'
        result = parse_source("api.py", source, "python")
        calls = [fact.text for fact in result.facts if fact.kind == "algorithm_step" and fact.name == "Call"]
        self.assertEqual(calls, ["helper()"])

    def test_real_click_project_has_parse_coverage_for_every_python_source(self):
        root = Path(__file__).resolve().parents[2] / ".local/real-projects/click"
        require_real_project(self,root)
        report = scan_project(root)
        python_files = [path for path in root.rglob("*.py") if ".git" not in path.parts]
        self.assertEqual(report.source_files, len(python_files))
        self.assertEqual(report.parsed_files, len(python_files))
        self.assertGreater(report.fact_count, 0)

    def test_real_regex_project_has_parse_coverage_for_every_rust_source(self):
        root = Path(__file__).resolve().parents[2] / ".local/real-projects/regex"
        require_real_project(self,root)
        report = scan_project(root)
        rust_files = [path for path in root.rglob("*.rs") if ".git" not in path.parts]
        self.assertEqual(report.source_files, len(rust_files))
        self.assertEqual(report.parsed_files, len(rust_files))
        self.assertGreater(report.fact_count, 0)

    def test_scan_inventory_reports_unparsed_resources_and_tracks_them_in_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "module.py").write_text("value = 1\n", encoding="utf-8")
            (root / "notes.md").write_text("first", encoding="utf-8")
            outside = root.parent / f"{root.name}-outside.txt"
            outside.write_text("outside", encoding="utf-8")
            (root / "link.txt").symlink_to(outside)
            first = scan_project(root)
            inventory = {entry.path: entry for entry in first.inventory}
            self.assertEqual(inventory["notes.md"].state, "readable")
            self.assertEqual(inventory["link.txt"].state, "unfollowed")
            self.assertNotIn("outside.txt", inventory)
            (root / "notes.md").write_text("changed", encoding="utf-8")
            second = scan_project(root)
            self.assertNotEqual(first.source_digest, second.source_digest)
            outside.unlink()

    def test_fact_ids_are_namespaced_by_project_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first"
            second = Path(temporary) / "second"
            first.mkdir()
            second.mkdir()
            source = "def answer(): return 42\n"
            (first / "main.py").write_text(source, encoding="utf-8")
            (second / "main.py").write_text(source, encoding="utf-8")
            first_ids = {fact.id for parsed in scan_project(first).files for fact in parsed.facts}
            second_ids = {fact.id for parsed in scan_project(second).files for fact in parsed.facts}
            self.assertTrue(first_ids)
            self.assertTrue(first_ids.isdisjoint(second_ids))

    def test_source_construct_ids_are_namespaced_by_project_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first"
            second = Path(temporary) / "second"
            first.mkdir()
            second.mkdir()
            source = "class Box:\n    value: str\n"
            (first / "main.py").write_text(source, encoding="utf-8")
            (second / "main.py").write_text(source, encoding="utf-8")
            first_ids = {item.construct_id for parsed in scan_project(first).files for item in parsed.constructs}
            second_ids = {item.construct_id for parsed in scan_project(second).files for item in parsed.constructs}
            self.assertTrue(first_ids)
            self.assertTrue(first_ids.isdisjoint(second_ids))


if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()
