"""将新请求和既有选择器规范化为唯一请求协议。"""
from copy import deepcopy
import json
from pathlib import Path
from jsonschema import Draft202012Validator


def normalize_fact_request(value: dict | str) -> dict:
    if isinstance(value,str):
        selector=value.strip()
        if selector.startswith('function:'):
            value={'view':'source','target':{'kind':'function','name':selector.split(':',1)[1]},
                   'facets':['implementation','algorithm'],'detail':'self'}
        elif selector.startswith('members:'):
            value={'view':'source','target':{'kind':'declaration','name':selector.split(':',1)[1]},'facets':['organization']}
        elif selector in {'project','workspace-members','classes','functions','definitions','all-declarations','all-supported-facts','modules','all-entities'}:
            kind={'project':'project','functions':'function','classes':'declaration','modules':'module'}.get(selector,'all')
            value={'view':'entity' if selector=='all-entities' else 'source','target':{'kind':kind},
                   'facets':['organization'],'conditions':{'legacySelector':selector}}
        else:
            raise ValueError('INVALID_REQUEST：不支持的查询选择器')
    if not isinstance(value,dict):raise ValueError('INVALID_REQUEST：请求必须是对象或选择器')
    result={'profile':'semantic-fact-request-2','scopeId':'default','view':'source',
            'target':{'kind':'all'},'facets':['organization'],'detail':'list','expandDepth':0,'conditions':{}}
    result.update(deepcopy(value))
    if result['view']=='entity' and result['detail']=='self' and isinstance(result['facets'],list):
        result['facets']=sorted(set(result['facets'])|{'attributes'})
    if isinstance(result['facets'],list):result['facets']=sorted(set(result['facets']))
    schema=json.loads((Path(__file__).resolve().parents[2]/'contracts/semantic-fact-request-2.schema.json').read_text())
    errors=list(Draft202012Validator(schema).iter_errors(result))
    if errors:raise ValueError('INVALID_REQUEST：'+'; '.join(e.message for e in errors))
    return result
