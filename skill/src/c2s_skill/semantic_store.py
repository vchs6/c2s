"""V2语义档案的原子补证与持久查询；不提供旧档案接口。"""
from __future__ import annotations
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def _identity_key(ref: dict) -> str:
    identity = ref["identity"]
    return _json({"authority": identity["authority"], "domainId": identity["domainId"],
                  "localId": identity["localId"]})

class SemanticEntityStore:
    def __init__(self, path: Path | str):
        self.path = Path(path).resolve()
    def validate_root(self, root: Path | str) -> None:
        root = Path(root).resolve(strict=True)
        if self.path == root or root in self.path.parents:
            raise ValueError("semantic entity store must be outside the analyzed project")
    def _connect(self) -> sqlite3.Connection:
        if self.path.is_file():
            with sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True) as check:
                tables={row[0] for row in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                legacy=bool(tables.intersection({'semantic_entity_archives','sessions','full_bundles','semantic_records'}))
                if legacy and 'semantic_entity_v2_archives' not in tables:
                    raise ValueError('UNSUPPORTED_ARCHIVE_PROFILE：产品只支持V2档案，旧文件保持原样')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        connection=sqlite3.connect(self.path,timeout=30)
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute("""CREATE TABLE IF NOT EXISTS semantic_entity_registry(
            scope_id TEXT NOT NULL, source_key TEXT NOT NULL, identity_key TEXT NOT NULL,
            kind TEXT NOT NULL, payload TEXT NOT NULL,
            PRIMARY KEY(scope_id,source_key), UNIQUE(scope_id,identity_key))""")
        _v2_tables(connection)
        return connection
    def read_request(self, scope_id: str, request: dict, input_fingerprint: str,
                     configuration_digest: str) -> dict:
        return _read_request_v2(self, scope_id, request, input_fingerprint, configuration_digest)
    def commit_request(self, operation_id: str, document: dict, request: dict) -> dict:
        return _commit_request_v2(self, operation_id, document, request)

def _merge_entity_record(old: dict, new: dict, *, allow_refinement: bool = False) -> dict:
    result = json.loads(_json(old))
    for field in ("ref", "name", "description"):
        if old[field] != new[field]:
            raise ValueError(f"conflicting entity {field}: {_identity_key(old['ref'])}")
    for field in ("aliases", "sourceKeys", "observationViews"):
        result[field] = sorted(set(old[field]) | set(new[field]))
    attributes = {item["attributeId"]: item for item in result["attributes"]}
    for item in new["attributes"]:
        previous = attributes.get(item["attributeId"])
        if previous is None:
            attributes[item["attributeId"]] = item
        elif previous != item:
            left = {k: v for k, v in previous.items() if k not in {"evidenceIds", "valueRange"}}
            right = {k: v for k, v in item.items() if k not in {"evidenceIds", "valueRange"}}
            left_range = {k: v for k, v in previous["valueRange"].items() if k != "evidenceIds"}
            right_range = {k: v for k, v in item["valueRange"].items() if k != "evidenceIds"}
            if allow_refinement and left==right and left_range!=right_range:
                if left_range=={"kind":"unknown"}:
                    previous["valueRange"]=json.loads(_json(item["valueRange"]))
                    left_range=right_range
                elif right_range=={"kind":"unknown"}:
                    right_range=left_range
            if left != right or left_range != right_range:
                raise ValueError(f"conflicting attribute: {item['attributeId']}")
            previous["evidenceIds"] = sorted(set(previous["evidenceIds"]) | set(item["evidenceIds"]))
            if "evidenceIds" in previous["valueRange"] or "evidenceIds" in item["valueRange"]:
                previous["valueRange"]["evidenceIds"] = sorted(set(previous["valueRange"].get("evidenceIds", []))
                    | set(item["valueRange"].get("evidenceIds", [])))
    result["attributes"] = sorted(attributes.values(), key=lambda item: item["attributeId"])
    return result

def _v2_tables(connection):
    connection.execute('''CREATE TABLE IF NOT EXISTS semantic_entity_v2_archives(
        scope_id TEXT NOT NULL, fingerprint TEXT NOT NULL, config TEXT NOT NULL,
        generation INTEGER NOT NULL, payload TEXT NOT NULL,
        PRIMARY KEY(scope_id,fingerprint,config))''')
    connection.execute('''CREATE TABLE IF NOT EXISTS semantic_entity_v2_operations(
        scope_id TEXT NOT NULL, operation_id TEXT NOT NULL, digest TEXT NOT NULL,
        fingerprint TEXT NOT NULL, config TEXT NOT NULL, receipt TEXT NOT NULL,
        PRIMARY KEY(scope_id,operation_id))''')

def _merge_v2_documents(old: dict, new: dict) -> dict:
    """合并同一固定输入上的补证，语义冲突不以最后写入覆盖。"""
    result=json.loads(_json(old))
    ids={'entities':lambda x:_identity_key(x['ref']), 'claims':lambda x:x['claimId'],
         'relations':lambda x:x['relationId'],'continuityCandidates':lambda x:x['candidateId'],
         'sourceMappings':lambda x:x['mappingId'],'evidence':lambda x:x['evidenceId'],
         'coverage':lambda x:x['coverageId'],'sourceRecords':lambda x:x['recordId'],
         'sourceCoverage':lambda x:x['coverageId'],'acquisitionRuns':lambda x:x['runId'],
         'artifacts':lambda x:x['artifactId']}
    for collection,key in ids.items():
        records={key(x):x for x in result.get(collection,[])}
        for item in new.get(collection,[]):
            rid=key(item)
            if rid not in records:records[rid]=item;continue
            previous=records[rid]
            if previous==item:continue
            if collection=='entities':
                records[rid]=_merge_entity_record(previous,item,allow_refinement=True);continue
            if collection in {'claims','relations','sourceRecords','sourceMappings'}:
                merged=json.loads(_json(previous))
                for field,value in item.items():
                    if field in {'evidenceIds','sourceConstructIds','parentRecordIds','relatedRecords'}:
                        merged[field]=list({_json(x):x for x in merged.get(field,[])+value}.values())
                    elif field=='value' and collection=='sourceRecords':
                        merged[field]={'observations':list({_json(x):x for x in
                            merged.get(field,{}).get('observations',[])+value.get('observations',[])}.values())}
                    elif field=='status' and collection=='sourceRecords':
                        states={'not_acquired':0,'unsupported':0,'partial':1,'obtained':2}
                        merged[field]=max([value,merged[field]],key=lambda x:states[x])
                    elif field not in merged:merged[field]=value
                    elif merged[field]!=value:raise ValueError(f'v2记录内容冲突：{collection}:{rid}:{field}')
                records[rid]=merged
            else:raise ValueError(f'v2记录内容冲突：{collection}:{rid}')
        result[collection]=list(records.values())
    return result

def _read_request_v2(store, scope_id, request, fingerprint, config):
    with store._connect() as connection:
        _v2_tables(connection)
        row=connection.execute('SELECT generation,payload FROM semantic_entity_v2_archives WHERE scope_id=? AND fingerprint=? AND config=?',
                               (scope_id,fingerprint,config)).fetchone()
        any_row=connection.execute('SELECT fingerprint FROM semantic_entity_v2_archives WHERE scope_id=? LIMIT 1',(scope_id,)).fetchone()
    if row is None:
        return {'model':None,'generation':0,'reusedFacets':[],
                'diagnostics':[{'code':'INPUT_CHANGED' if any_row and any_row[0]!=fingerprint else 'CONFIGURATION_CHANGED'}] if any_row else []}
    model=json.loads(row[1]);reused=set()
    for cov in model['sourceCoverage']:
        applicable=cov['inputFingerprint']==fingerprint and cov['configurationDigest']==config
        applicable=applicable and cov['view']==request['view'] and (cov['target']==request['target'] or cov['target']=={'kind':'all'})
        applicable=applicable and cov['conditions']==request.get('conditions',{})
        if applicable and cov['status'] in {'obtained','partial'} and not any(d.get('retryable') for d in cov['diagnostics']):
            reused.update(cov['facets'])
    return {'model':model,'generation':row[0],'reusedFacets':sorted(reused),'diagnostics':[]}

def _commit_request_v2(store, operation_id, document, request):
    from c2s_semantic_contract.validation import validate_semantic_entity_model_v2
    document=json.loads(_json(document))
    if not operation_id or document.get('scopeId')!=request['scopeId']:
        raise ValueError('v2操作标识或范围不匹配')
    checked=validate_semantic_entity_model_v2(document)
    if not checked['valid']:raise ValueError('无效v2档案：'+_json(checked['diagnostics']))
    if not document['sourceCoverage']:raise ValueError('v2提交缺少请求覆盖记录')
    first=document['sourceCoverage'][0];fp=first['inputFingerprint'];cfg=first['configurationDigest'];scope=document['scopeId']
    if any(c['inputFingerprint']!=fp or c['configurationDigest']!=cfg for c in document['sourceCoverage']):
        raise ValueError('不能混合不同输入或配置的覆盖')
    digest=_sha(_json({'request':request,'document':document}).encode())
    if any(run['status'] in {'cancelled','failed'} for run in document['acquisitionRuns']):
        for cov in document['sourceCoverage']:
            cov['status']='not_acquired';cov['diagnostics'].append({'code':'ACQUISITION_UNFINISHED','retryable':True})
    for collection in ('coverage','sourceCoverage'):
        for cov in document[collection]:cov['coverageId']+=':'+_sha(operation_id.encode())[:16]
    run_id='operation:'+operation_id
    document['acquisitionRuns'].append({'runId':run_id,'inputFingerprint':fp,'configurationDigest':cfg,
        'status':'partial' if any(c['status']!='obtained' for c in document['sourceCoverage']) else 'completed',
        'tools':[],'sourceRecordIds':[x['recordId'] for x in document['sourceRecords']],
        'evidenceIds':[x['evidenceId'] for x in document['evidence']],
        'artifactIds':[x['artifactId'] for x in document['artifacts']]})
    with store._connect() as connection:
        _v2_tables(connection)
        connection.execute('BEGIN IMMEDIATE')
        old_op=connection.execute('SELECT digest,receipt FROM semantic_entity_v2_operations WHERE scope_id=? AND operation_id=?',
                                  (scope,operation_id)).fetchone()
        row=connection.execute('SELECT generation,payload FROM semantic_entity_v2_archives WHERE scope_id=? AND fingerprint=? AND config=?',
                               (scope,fp,cfg)).fetchone()
        if old_op:
            if old_op[0]!=digest:raise ValueError('同一操作标识不能提交不同内容')
            return {**json.loads(old_op[1]),'model':json.loads(row[1])}
        merged=_merge_v2_documents(json.loads(row[1]),document) if row else document
        checked=validate_semantic_entity_model_v2(merged)
        if not checked['valid']:raise ValueError('v2合并引用不合法：'+_json(checked['diagnostics']))
        for entity in merged['entities']:
            for key in entity['sourceKeys']:
                if not key.startswith('candidate:'):continue
                identity_key=_json(entity['ref']['identity'])
                existing=connection.execute('SELECT identity_key,kind FROM semantic_entity_registry WHERE scope_id=? AND source_key=?',
                                            (scope,key)).fetchone()
                if existing and (existing[0]!=identity_key or existing[1]!=entity['ref']['kind']):
                    raise ValueError('注册身份冲突，不能按名字或路径合并')
                if not existing:
                    payload={'ref':entity['ref'],'sourceKey':key,'name':entity['name'],'evidenceIds':[]}
                    connection.execute('INSERT INTO semantic_entity_registry VALUES(?,?,?,?,?)',
                        (scope,key,identity_key,entity['ref']['kind'],_json(payload)))
        generation=row[0]+1 if row else 1
        connection.execute('INSERT OR REPLACE INTO semantic_entity_v2_archives VALUES(?,?,?,?,?)',
                           (scope,fp,cfg,generation,_json(merged)))
        receipt={'status':'saved','generation':generation,'operationId':operation_id}
        connection.execute('INSERT INTO semantic_entity_v2_operations VALUES(?,?,?,?,?,?)',
                           (scope,operation_id,digest,fp,cfg,_json(receipt)))
    return {**receipt,'model':merged}
