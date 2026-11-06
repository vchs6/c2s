import unittest
import sqlite3
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from c2s_skill.acquisition import scan_project
from c2s_skill.query import query_project
from c2s_skill.store import FactStore


class FactStoreTests(unittest.TestCase):
    def test_store_write_failure_keeps_facts_and_reports_persistence_separately(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "main.py").write_text("def answer(): return 42\n")
            store = FactStore(root.parent / (root.name + ".sqlite"))
            with patch.object(store, "save", side_effect=sqlite3.OperationalError("database is full")):
                result = query_project(root, ["function:answer"], store)
            self.assertTrue(result.facts)
            self.assertTrue(result.complete)
            self.assertEqual(result.persistence.status, "write_failed")
            self.assertEqual(result.persistence.diagnostic, "OperationalError")

    def test_store_inside_project_is_rejected_before_creating_any_file(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "main.py").write_text("def answer(): return 42\n")
            store_path = root / "facts.sqlite"
            with self.assertRaisesRegex(ValueError, "outside the analyzed project"):
                query_project(root, ["functions"], FactStore(store_path))
            self.assertFalse(store_path.exists())

    def test_store_reuses_result_only_for_the_same_source_digest(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "main.py").write_text("def answer(): return 42\n")
            store = FactStore(root.parent / (root.name + ".sqlite"))
            result = query_project(root, ["function:answer"], store)
            with patch("c2s_skill.query.scan_project", side_effect=AssertionError("cache miss")):
                cached = query_project(root, ["function:answer"], store)
            self.assertEqual(cached.facts, result.facts)
            self.assertEqual(cached.persistence.status, "cache_hit")
            (root / "README.md").write_text("project documentation changed", encoding="utf-8")
            documentation_update = query_project(root, ["function:answer"], store)
            self.assertNotEqual(documentation_update.source_digest, result.source_digest)
            self.assertEqual(documentation_update.facts, result.facts)
            (root / "main.py").write_text("def answer(): return 43\n")
            updated = query_project(root, ["function:answer"], store)
            self.assertNotEqual(updated.source_digest, documentation_update.source_digest)
            self.assertNotEqual(updated.facts[0].text, result.facts[0].text)

    def test_store_recomputes_when_analyzer_profile_changes(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "main.py").write_text("def answer(): return 42\n")
            store = FactStore(root.parent / (root.name + ".sqlite"))
            with patch("c2s_skill.query.analysis_profile_digest", return_value="profile-a"):
                first = query_project(root, ["functions"], store)
            with patch("c2s_skill.query.analysis_profile_digest", return_value="profile-b"), \
                 patch("c2s_skill.query.scan_project", wraps=scan_project) as scan:
                second = query_project(root, ["functions"], store)
            self.assertEqual(scan.call_count, 1)
            self.assertNotEqual(first.profile_digest, second.profile_digest)


if __name__ == "__main__":
    unittest.main()
