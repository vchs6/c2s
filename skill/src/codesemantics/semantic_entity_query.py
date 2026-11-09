"""只查询已存V2档案，不隐式重建事实。"""
def query_entity_store_v2(store, request: dict, input_fingerprint: str,
                          configuration_digest: str) -> dict:
    """只投影已保存的v2事实；输入适用性由调用方给定，不隐式重扫。"""
    from .fact_request import normalize_fact_request
    from .fact_query import project_fact_result, _empty_model
    q=normalize_fact_request(request)
    read=store.read_request(q['scopeId'],q,input_fingerprint,configuration_digest)
    result=project_fact_result(read['model'] or _empty_model(q['scopeId']),q)
    result['persistence']={'status':'reused' if read['model'] else 'not_found'}
    result['diagnostics'].extend(read['diagnostics'])
    if read['model'] is None:result['diagnostics'].append({'code':'FACT_ARCHIVE_NOT_FOUND'})
    return result
