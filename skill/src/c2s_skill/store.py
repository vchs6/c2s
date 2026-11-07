"""Transactional local persistence for source-bound query results."""

import json
import sqlite3
from pathlib import Path

from .acquisition import Fact
from .inventory import InventoryEntry
from .query import Gap, PersistenceResult, QueryResult, result_to_dict


class QueryResultCache:
    """Cache rendered query projections; this is not the semantic fact repository."""
    def __init__(self, path: Path):
        self.path = path.resolve()

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("""CREATE TABLE IF NOT EXISTS query_results (
            root TEXT NOT NULL, source_digest TEXT NOT NULL, selectors TEXT NOT NULL,
            result_json TEXT NOT NULL, PRIMARY KEY (root, source_digest, selectors)
        )""")
        return connection

    def validate_root(self, root: Path) -> None:
        root = root.resolve(strict=True)
        if self.path == root or root in self.path.parents:
            raise ValueError("fact store must be outside the analyzed project")

    def save(self, result: QueryResult, source_digest: str) -> None:
        root = Path(result.root).resolve()
        self.validate_root(root)
        selectors = json.dumps({"selectors": result.requested, "profile_digest": result.profile_digest},
                               ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        payload = json.dumps(result_to_dict(result), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute("INSERT OR REPLACE INTO query_results VALUES (?, ?, ?, ?)",
                               (str(root), source_digest, selectors, payload))

    def load(self, root: Path, selectors: list[str], source_digest: str,
             profile_digest: str) -> QueryResult | None:
        root = root.resolve()
        self.validate_root(root)
        key = json.dumps({"selectors": tuple(selectors), "profile_digest": profile_digest},
                         ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            row = connection.execute("SELECT result_json FROM query_results WHERE root=? AND source_digest=? AND selectors=?",
                                     (str(root), source_digest, key)).fetchone()
        if row is None:
            return None
        data = json.loads(row[0])
        facts = tuple(Fact(item["id"], item["kind"], item["name"], item["path"], item["start_byte"],
                           item["end_byte"], item["layer"], item["claim_mode"], item["text"], item.get("owner"),
                           item.get("subject_id", ""), item.get("evidence_included", True))
                      for item in data["facts"])
        gaps = tuple(Gap(item["selector"], item["reason"]) for item in data["gaps"])
        return QueryResult(data["root"], tuple(data["requested"]), facts, gaps, data["complete"],
                           data["coverage"]["source_files"], data["coverage"]["parsed_files"],
                           data["source_digest"], tuple(InventoryEntry(
                               item["path"], item["kind"], item["size_bytes"], item["state"], item["diagnostic"])
                               for item in data.get("inventory", [])), data["profile_digest"],
                           PersistenceResult(data.get("persistence", {}).get("status", "saved"),
                                             data.get("persistence", {}).get("diagnostic")),
                           tuple(data.get("tools_used", [])))


# Kept for source compatibility with early callers. New code should use the
# name that describes this table's actual contents.
FactStore = QueryResultCache
