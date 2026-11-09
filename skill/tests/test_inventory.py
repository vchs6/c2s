import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codesemantics.inventory import inventory_tree


class InventoryTests(unittest.TestCase):
    def test_inventories_ignored_nested_and_hidden_files_and_does_not_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".gitignore").write_text("ignored.py\n")
            for name in ["ignored.py", ".hidden.py", "tests/test_one.py", "nested/deep.py"]:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("value = 1\n")
            outside = root.parent / f"{root.name}-outside.py"
            outside.write_text("outside = True\n")
            (root / "linked.py").symlink_to(outside)

            entries = inventory_tree(root)
            by_path = {entry.path: entry for entry in entries}

            self.assertTrue({"ignored.py", ".hidden.py", "tests/test_one.py", "nested/deep.py"} <= by_path.keys())
            self.assertEqual(by_path["linked.py"].kind, "symlink")
            self.assertEqual(by_path["linked.py"].state, "unfollowed")
            self.assertNotIn("outside.py", by_path)
            outside.unlink()

    def test_can_exclude_repository_control_directories_without_following_them(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".git" / "objects").mkdir(parents=True)
            (root / ".git" / "objects" / "opaque").write_text("metadata")
            (root / "src.py").write_text("value = 1\n")
            entries = inventory_tree(root, excluded_dirs=frozenset({".git"}))
            self.assertEqual([entry.path for entry in entries], ["src.py"])

    def test_records_unreadable_directory_instead_of_dropping_its_subtree(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            blocked = root / "blocked"
            blocked.mkdir()
            original_iterdir = Path.iterdir

            def deny_blocked(path):
                if path == blocked:
                    raise PermissionError("synthetic unreadable directory")
                return original_iterdir(path)

            with patch.object(Path, "iterdir", deny_blocked):
                entries = inventory_tree(root)
            entry = next(item for item in entries if item.path == "blocked")
            self.assertEqual(entry.state, "unreadable")
            self.assertEqual(entry.diagnostic, "PermissionError")


if __name__ == "__main__":
    unittest.main()
