"""验证连续失败重试的有效档案有界、恢复和响应复用；不限制操作审计历史。"""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time

if not __debug__:
    raise RuntimeError('验证器必须启用断言，不能使用Python优化模式')

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'skill/src')]
from codesemantics.fact_query import execute_fact_query, v2_configuration_digest
from codesemantics.semantic_store import SemanticEntityStore
from codesemantics.store import QueryResultCache


def verify(retries=128):
    if retries < 2:
        raise ValueError('至少连续重试两次')
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='c2s-retry-verification-') as tmp:
        base = Path(tmp); source = base/'project'; source.mkdir()
        (source/'m.py').write_text('def run():\n    return 1\n')
        store = SemanticEntityStore(base/'facts.sqlite')
        cache = QueryResultCache(base/'responses.sqlite')
        request = {'target': {'kind':'function', 'name':'run'}, 'facets':['relations']}
        snapshot = None
        for attempt in range(retries):
            result = execute_fact_query(source, request, store, cache=cache)
            assert result['items'], '重试未取得已存在的目标函数'
            assert len(result['coverage']) == 1, '响应覆盖按相同重试次数膨胀'
            model = store.read_request(result['request']['scopeId'], result['request'],
                                      result['cost']['inputFingerprint'], result['cost']['configurationDigest'])['model']
            assert len(model['sourceCoverage']) == len(model['acquisitionRuns']) == 1, '有效覆盖或等价取得运行膨胀'
            encoded = json.dumps(model, ensure_ascii=False, sort_keys=True)
            if snapshot is None:
                snapshot = encoded
            assert snapshot == encoded, '相同失败重试改变有效事实档案'
        graph = {'status':'error', 'error':'临时后端失败', 'pattern':'callees_of',
                 'target':'m.py::run', 'result_count':0, 'results_omitted':0, 'results':[], 'edges':[]}
        execute_fact_query(source, request, store, cache=cache,
                           tool_runner=lambda *args: {'response':graph, 'toolVersion':'2.3.9'})
        recovered = execute_fact_query(source, request, store, cache=cache,
                           tool_runner=lambda *args: {'response':{**graph,'status':'ok'}, 'toolVersion':'2.3.9'})
        codes = {d['code'] for d in recovered['diagnostics']}
        assert 'GRAPH_TOOL_FAILED' not in codes, '恢复输出仍被旧失败覆盖'
        assert 'GRAPH_INDEX_FRESHNESS_UNVERIFIED' in codes, '不可证明的新鲜度缺口被隐瞒'
        for _ in range(8):
            result = execute_fact_query(source, request, store, cache=cache)
            assert result['persistence']['status'] in {'reused', 'cache_hit'}, '恢复后未复用有效取得'
            assert len(result['coverage']) == 1
        with store._connect() as connection:
            operations = connection.execute('SELECT count(*) FROM semantic_entity_v2_operations').fetchone()[0]
        assert operations == retries + 2, '审计回执缺失或复用查询额外产生取得操作'
        return {'valid':True, 'retries':retries, 'sameFailureModelBytes':len(snapshot.encode()),
                'sameFailureCoverage':1, 'sameFailureAcquisitionRuns':1, 'recoveryVerified':True,
                'postRecoveryReuses':8, 'operations':operations,
                'configurationDigest':v2_configuration_digest(), 'elapsedSeconds':time.monotonic()-started,
                'limits':'操作回执保留历史；此结果不声称整个数据库有界或图索引新鲜度已证明。'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retries', type=int, default=128)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.retries)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
