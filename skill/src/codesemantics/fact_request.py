"""将新请求和既有选择器规范化为唯一请求协议。"""
from copy import deepcopy
import json
from pathlib import Path
from jsonschema import Draft202012Validator


def normalize_fact_request(value: dict | str) -> dict:
    if isinstance(value,str):
        selector=value.strip()
        if selector.startswith('function:'):
            name=selector.split(':',1)[1].replace('::','.')
            owner,separator,simple=name.rpartition('.')
            value={'view':'source','target':{'kind':'function','name':simple if separator else name},
                   'facets':['implementation','algorithm'],'detail':'self','conditions':{'qualifiedOwner':owner} if separator else {}}
        elif selector.startswith('members:'):
            value={'view':'source','target':{'kind':'declaration','name':selector.split(':',1)[1]},'facets':['organization'],'conditions':{'selector':'members'}}
        elif selector in {'project','workspace-members','classes','functions','definitions','all-declarations','all-supported-facts','modules','all-entities','imports','constants','local-bindings','behavior-contracts','algorithm-structure'}:
            kind={'project':'project','functions':'function','classes':'declaration','modules':'module','algorithm-structure':'function'}.get(selector,'all')
            value={'view':'entity' if selector=='all-entities' else 'source','target':{'kind':kind},
                   'facets':(['implementation','algorithm'] if selector in {'algorithm-structure','all-supported-facts'}
                             else ['implementation'] if selector in {'definitions','local-bindings','behavior-contracts'}
                             else ['organization']),'conditions':{'selector':selector}}
        else:
            from .request_selectors import normalize_request
            mapped=normalize_request(selector)
            if len(mapped)==1 and not mapped[0].startswith('unrecognized:') and mapped[0]!=selector:
                return normalize_fact_request(mapped[0])
            raise ValueError('INVALID_REQUEST：不支持的查询选择器')
    if not isinstance(value,dict):raise ValueError('INVALID_REQUEST：请求必须是对象或选择器')
    result={'profile':'semantic-fact-request-2','scopeId':'default','view':'source',
            'target':{'kind':'all'},'facets':['organization'],'detail':'list','expandDepth':0,'conditions':{}}
    result.update(deepcopy(value))
    if isinstance(result['facets'],list) and not all(isinstance(f,str) for f in result['facets']):
        raise ValueError('INVALID_REQUEST：facets成员必须是字符串')
    if result['view']=='entity' and result['detail']=='self' and isinstance(result['facets'],list):
        result['facets']=sorted(set(result['facets'])|{'attributes'})
    if isinstance(result['facets'],list):result['facets']=sorted(set(result['facets']))
    schema=json.loads((Path(__file__).resolve().parents[2]/'contracts/semantic-fact-request-2.schema.json').read_text())
    errors=list(Draft202012Validator(schema).iter_errors(result))
    if errors:raise ValueError('INVALID_REQUEST：'+'; '.join(e.message for e in errors))
    return result
