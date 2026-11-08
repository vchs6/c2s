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


    def _v2_key(self, root, request, source_digest, profile_digest):
        self.validate_root(root)
        return json.dumps({'root':str(root.resolve()), 'requestProfile':request.get('profile'),
            'resultProfile':'semantic-fact-result-2','request':request,
            'inputFingerprint':source_digest,'configurationDigest':profile_digest},
            ensure_ascii=False,sort_keys=True,separators=(',',':'))

    def save_v2(self, root, request, source_digest, profile_digest, result):
        key=self._v2_key(root,request,source_digest,profile_digest)
        if result.get('profile')!='semantic-fact-result-2':raise ValueError('v2缓存不接受旧结果')
        with self._connect() as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS query_results_v2(cache_key TEXT PRIMARY KEY,payload TEXT NOT NULL)')
            connection.execute('INSERT OR REPLACE INTO query_results_v2 VALUES(?,?)',
                               (key,json.dumps(result,ensure_ascii=False,sort_keys=True)))

    def load_v2(self, root, request, source_digest, profile_digest):
        key=self._v2_key(root,request,source_digest,profile_digest)
        with self._connect() as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS query_results_v2(cache_key TEXT PRIMARY KEY,payload TEXT NOT NULL)')
            row=connection.execute('SELECT payload FROM query_results_v2 WHERE cache_key=?',(key,)).fetchone()
        if row is None:return None
        result=json.loads(row[0])
        from jsonschema import Draft202012Validator
        schema=json.loads((Path(__file__).resolve().parents[2]/'contracts/semantic-fact-result-2.schema.json').read_text())
        if list(Draft202012Validator(schema).iter_errors(result)):
            raise ValueError('v2缓存损坏或不符合当前协议')
        return result


# Kept for source compatibility with early callers. New code should use the
# name that describes this table's actual contents.
FactStore = QueryResultCache
