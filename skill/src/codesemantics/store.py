"""仅缓存V2结果，缓存不是语义事实仓库。"""
import json
import sqlite3
from contextlib import contextmanager
from .sqlite_lifecycle import open_sqlite
from pathlib import Path

class QueryResultCache:
    def __init__(self, path: Path):
        self.path = path.resolve()
    @contextmanager
    def _connect(self):
        if self.path.is_file():
            with open_sqlite(self.path.as_uri()+'?mode=ro',uri=True) as check:
                tables={r[0] for r in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                old={'query_results','semantic_entity_archives','semantic_entity_registry','sessions','full_bundles','semantic_records'}
                if tables.intersection(old) and 'query_results_v2' not in tables:
                    raise ValueError('UNSUPPORTED_CACHE_PROFILE：不支持的档案不能作为V2缓存，原文件保持不变')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with open_sqlite(self.path) as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS query_results_v2(cache_key TEXT PRIMARY KEY,payload TEXT NOT NULL)')
            yield connection
    def validate_root(self, root: Path) -> None:
        root = root.resolve(strict=True)
        if self.path == root or root in self.path.parents:
            raise ValueError("fact store must be outside the analyzed project")

    def _v2_key(self, root, request, source_digest, profile_digest):
        self.validate_root(root)
        return json.dumps({'root':str(root.resolve()), 'requestProfile':request.get('profile'),
            'resultProfile':'semantic-fact-result-2','request':request,
            'inputFingerprint':source_digest,'configurationDigest':profile_digest},
            ensure_ascii=False,sort_keys=True,separators=(',',':'))

    def save_v2(self, root, request, source_digest, profile_digest, result):
        key=self._v2_key(root,request,source_digest,profile_digest)
        if result.get('profile')!='semantic-fact-result-2':raise ValueError('v2缓存不接受其他结果')
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
