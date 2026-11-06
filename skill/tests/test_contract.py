import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from jsonschema import Draft202012Validator

from c2s_skill.query import query_project, result_to_dict


class ContractTests(unittest.TestCase):
    def test_json_result_matches_the_public_semantic_fact_schema(self):
        schema_path = Path(__file__).resolve().parents[1] / "contracts/semantic-fact-query.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "main.py").write_text('def answer():\n    """Return the answer."""\n    return 42\n')
            result = result_to_dict(query_project(root, ["all-supported-facts"]))
        Draft202012Validator(schema).validate(result)

    def test_schema_rejects_unknown_layer_and_missing_fact_identity(self):
        schema_path = Path(__file__).resolve().parents[1] / "contracts/semantic-fact-query.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        fact_schema = schema["$defs"]["fact"]
        validator = Draft202012Validator(fact_schema)
        self.assertTrue(list(validator.iter_errors({"layer": "E5"})))


if __name__ == "__main__":
    unittest.main()
