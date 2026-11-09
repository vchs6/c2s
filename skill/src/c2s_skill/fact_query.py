"""固定输入上的v2查询：来源、解释、存储读回和双输出共用同一结果。"""
from dataclasses import replace
from pathlib import Path
import hashlib
import json
import sqlite3
import time
from uuid import uuid4
from .acquisition import (scan_project, analysis_profile_digest, SourceConstruct, ParseResult, Fact, cargo_workspace_facts)
from .inventory import inventory_tree, source_fingerprint
from .fact_request import normalize_fact_request
from .source_records import collect_source_records, stable_id
from .construction_plan import matching_records, plan_fact_request
from .entity_construction import construct_requested_entities
from .semantic_store import _merge_v2_documents, _identity_key


def _empty_model(scope):
    return {'version':'2.0.0','profile':'semantic-entity-model-2','scopeId':scope,
            **{k:[] for k in ('entities','claims','relations','continuityCandidates','sourceMappings',
                             'evidence','coverage','sourceRecords','sourceCoverage','acquisitionRuns','artifacts')}}


def v2_configuration_digest() -> str:
    """解释器/工具配置加实际产品源码，避免代码升级后误复用旧结果。"""
    module_root=Path(__file__).resolve().parent
    files=sorted(module_root.glob('*.py'))
    files+=sorted((module_root.parents[1]/'contracts').glob('*2.schema.json'))
    files+=[module_root.parents[1]/'contracts/semantic-algorithm.schema.json']
    repo=module_root.parents[2]
    files+=sorted((repo/'contracts/semantic-model').glob('*.json'))
    files+=[repo/'src/c2s_semantic_contract/validation.py']
    digests=[(p.name,hashlib.sha256(p.read_bytes()).hexdigest()) for p in files if p.is_file()]
    return stable_id([analysis_profile_digest(),digests])


def prepare_fact_projection_index(model: dict) -> dict:
    """同一不可变档案上复用索引，不保留跨输入全局缓存。"""
    index={'sourceById':{s['recordId']:s for s in model.get('sourceRecords',[])},
           'entityById':{_identity_key(e['ref']):e for e in model.get('entities',[])},
           'evidenceById':{e['evidenceId']:e for e in model.get('evidence',[])},
           'claimById':{c['claimId']:c for c in model.get('claims',[])},
           'claims':{},'relations':{},'mappings':{},'sourcesByConstruct':{},'coverageDiagnostics':{}}
    for claim in model.get('claims',[]):index['claims'].setdefault(_identity_key(claim['subject']),[]).append(claim)
    for relation in model.get('relations',[]):
        refs=[relation['subject']]+([relation['target']] if 'identity' in relation['target'] else [])
        for ref in refs:index['relations'].setdefault(_identity_key(ref),[]).append(relation)
    for mapping in model.get('sourceMappings',[]):
        if 'identity' in mapping.get('target',{}):index['mappings'].setdefault(_identity_key(mapping['target']),[]).append(mapping)
    for source in model.get('sourceRecords',[]):
        for cid in source['sourceConstructIds']:index['sourcesByConstruct'].setdefault(cid,[]).append(source)
    for cov in model.get('sourceCoverage',[]):
        buckets={}
        for d in cov['diagnostics']:
            if 'identity' in d.get('entity',{}):key=('entity',_identity_key(d['entity']))
            elif d.get('candidateId'):key=('candidate',d['candidateId'])
            elif d.get('sourceConstructId'):key=('construct',d['sourceConstructId'])
            elif d.get('recordId'):key=('source',d['recordId'])
            elif d.get('path'):key=('path',d['path'])
            else:key=('global','*')
            buckets.setdefault(key,[]).append(d)
        index['coverageDiagnostics'][cov['coverageId']]=buckets
    return index


def project_fact_result(model: dict, request: dict, *, index: dict | None = None) -> dict:
    """投影已取得的档案；不访问源码、不重建实体或算法。"""
    result={'profile':'semantic-fact-result-2','request':request,'items':[],
            'sourceRecords':[],'claims':[],'evidence':[],'coverage':[],
            'diagnostics':[],'artifacts':[],'persistence':{'status':'not_requested'},'cost':{}}
    view=request['view'];records=model.get('sourceRecords',[]) if view=='source' else model.get('entities',[])
    index=index or prepare_fact_projection_index(model)
    target=request['target'];match_request=request
    if view=='entity' and target.get('path'):
        records=[e for e in records if any(m['sourceConstruct']['path']==target['path']
                  for m in index['mappings'].get(_identity_key(e['ref']),[]))]
        match_request={**request,'target':{k:v for k,v in target.items() if k!='path'}}
    if target.get('ref'):
        ref=target['ref']
        candidate=index['sourceById'].get(ref.get('recordId')) if view=='source' else index['entityById'].get(_identity_key(ref))
        if view=='entity' and target.get('path') and candidate not in records:candidate=None
        candidates=matching_records(match_request,[candidate] if candidate else [])
    else:candidates=matching_records(match_request,records)
    if (target.get('name') or target.get('ref')) and len(candidates)>1:
        result['diagnostics']=[{'code':'AMBIGUOUS_TARGET','candidates':[
            {'name':r.get('name'),'path':r.get('path'),'ref':r.get('ref'),'recordId':r.get('recordId')} for r in candidates]}]
        return result
    if view=='source':
        if request['conditions'].get('legacySelector')=='members':
            parents={r['recordId'] for r in candidates}
            candidates=[r for r in records if r['kind'] in {'declaration','test_entry'} and parents.intersection(r['parentRecordIds'])]
        selected={r['recordId']:r for r in candidates}
        result['items']=list(candidates)
        if 'relations' in request['facets']:
            for candidate in model.get('sourceRecords',[]):
                if candidate['kind']=='call_candidate' and set(candidate['parentRecordIds']).intersection(selected):
                    selected[candidate['recordId']]=candidate
        by_id=index['sourceById']
        pending=list(selected.values())
        while pending:
            current=pending.pop()
            for rid in current['parentRecordIds']+[x['recordId'] for x in current['relatedRecords']]:
                if rid in by_id and rid not in selected:selected[rid]=by_id[rid];pending.append(by_id[rid])
        result['sourceRecords']=list(selected.values())
    else:
        selected={_identity_key(e['ref']):e for e in candidates}
        by_ref=index['entityById']
        visited=set(selected);pending=[(e,0) for e in candidates]
        while pending:
            entity,depth=pending.pop(0);key=_identity_key(entity['ref'])
            item=dict(entity)
            if request['detail']=='list':item={k:v for k,v in item.items() if k in {'ref','name','description','aliases'}}
            else:
                item['relations']=index['relations'].get(key,[])
                item['sourceMappings']=index['mappings'].get(key,[])
            result['items'].append(item)
            if request['expandDepth']==0:continue
            children=[r for r in index['relations'].get(key,[]) if r['subject']==entity['ref'] and r['predicate'] in {'defines','contains','groups'}]
            if depth>=request['expandDepth']:
                if children:result['diagnostics'].append({'code':'EXPANSION_DEPTH_LIMIT','entity':entity['ref']})
                continue
            for relation in children:
                child_key=_identity_key(relation['target'])
                if child_key in visited:
                    result['diagnostics'].append({'code':'ENTITY_RELATION_CYCLE','entity':relation['target']});continue
                if child_key in by_ref:
                    visited.add(child_key);selected[child_key]=by_ref[child_key];pending.append((by_ref[child_key],depth+1))
        refs=[e['ref'] for e in selected.values()]
        result['claims']=[c for ref in refs for c in index['claims'].get(_identity_key(ref),[])]
        mapped_ids={m['sourceConstruct']['constructId'] for ref in refs for m in index['mappings'].get(_identity_key(ref),[])}
        result['sourceRecords']=list({s['recordId']:s for cid in mapped_ids for s in index['sourcesByConstruct'].get(cid,[])}.values())
        # 来源父引用仍以同一来源索引补齐，不展开语义关系目标。
        source_ids={s['recordId'] for s in result['sourceRecords']};source_index=index['sourceById']
        pending=list(result['sourceRecords'])
        while pending:
            item=pending.pop()
            for parent in item['parentRecordIds']:
                if parent in source_index and parent not in source_ids:
                    source_ids.add(parent);result['sourceRecords'].append(source_index[parent]);pending.append(source_index[parent])
    relevant_keys=set()
    for item in result['items']:
        if 'ref' in item:relevant_keys.add(('entity',_identity_key(item['ref'])))
        for source_key in item.get('sourceKeys',[]):
            if source_key.startswith('candidate:'):relevant_keys.add(('candidate',source_key.rsplit(':',1)[-1]))
    relevant_paths={r['path'] for r in result['sourceRecords']}
    for source in result['sourceRecords']:
        relevant_keys.add(('source',source['recordId']))
        relevant_keys.add(('path',source['path']))
        relevant_keys.update(('construct',cid) for cid in source['sourceConstructIds'])
    for coverage in model.get('sourceCoverage',[]):
        if (coverage['view']==view and (coverage['target']==target or coverage['target']=={'kind':'all'})
                and coverage['conditions']==request.get('conditions',{})
                and set(coverage['facets']).intersection(request['facets'])):
            if coverage['target']==target:
                shown=coverage
            else:
                buckets=index['coverageDiagnostics'].get(coverage['coverageId'],{})
                scoped=[d for key in relevant_keys for d in buckets.get(key,[])]
                scoped.extend(d for d in buckets.get(('global','*'),[]) if d.get('code') in
                              {'INPUT_CHANGED','CONFIGURATION_CHANGED','ACQUISITION_UNFINISHED','GRAPH_INDEX_FRESHNESS_UNVERIFIED'})
                if coverage['status']!='obtained' and not scoped:
                    scoped=[{'code':'BROADER_COVERAGE_PARTIAL','coverageId':coverage['coverageId']}]
                shown={**coverage,'diagnostics':scoped,
                       'processedPaths':[p for p in coverage['processedPaths'] if p in relevant_paths],
                       'unprocessedPaths':[p for p in coverage['unprocessedPaths'] if p in relevant_paths]}
            result['coverage'].append(shown)
            result['diagnostics'].extend(shown['diagnostics'])
    covered={facet for cov in result['coverage'] for facet in cov['facets']}
    missing=set(request['facets'])-covered
    if missing:
        result['diagnostics'].append({'code':'FACET_NOT_ACQUIRED','facets':sorted(missing)})
    wanted=set()
    premises=[]
    def evidence_refs(value):
        if isinstance(value,dict):
            for key,child in value.items():
                if key == 'premiseIds':premises.extend(child)
                elif key in {'evidenceIds','evidence_refs'}:
                    wanted.update(child)
                elif key=='evidenceId' and isinstance(child,str):wanted.add(child)
                else:evidence_refs(child)
        elif isinstance(value,list):
            for child in value:evidence_refs(child)
    evidence_refs(result['items']);evidence_refs(result['sourceRecords']);evidence_refs(result['claims']);evidence_refs(result['diagnostics'])
    # 前提有来源、主张、证据三个合法引用域；只补证明依赖，不展开关联实体。
    seen_premises=set()
    source_ids={s['recordId'] for s in result['sourceRecords']}
    claim_ids={c['claimId'] for c in result['claims']}
    while premises:
        premise=premises.pop()
        if premise in seen_premises:continue
        seen_premises.add(premise)
        if premise in index['evidenceById']:
            wanted.add(premise)
        elif premise in index['sourceById']:
            pending_sources=[index['sourceById'][premise]]
            while pending_sources:
                source=pending_sources.pop()
                if source['recordId'] in source_ids:continue
                source_ids.add(source['recordId']);result['sourceRecords'].append(source)
                evidence_refs(source)
                pending_sources.extend(index['sourceById'][pid] for pid in source['parentRecordIds']
                                       if pid in index['sourceById'] and pid not in source_ids)
        elif premise in index['claimById']:
            claim=index['claimById'][premise]
            if premise not in claim_ids:
                claim_ids.add(premise);result['claims'].append(claim)
            evidence_refs(claim)
        else:
            result['diagnostics'].append({'code':'PREMISE_REFERENCE_MISSING','premiseId':premise})
    for eid in sorted(wanted-set(index['evidenceById'])):
        result['diagnostics'].append({'code':'EVIDENCE_REFERENCE_MISSING','evidenceId':eid})
    result['evidence']=[index['evidenceById'][eid] for eid in sorted(wanted) if eid in index['evidenceById']]
    artifact_ids=set()
    def artifact_refs(value):
        if isinstance(value,dict):
            for key,child in value.items():
                if key in {'artifactId','legacyPayloadArtifactId'} and isinstance(child,str):artifact_ids.add(child)
                else:artifact_refs(child)
        elif isinstance(value,list):
            for child in value:artifact_refs(child)
    artifact_refs(result)
    available_artifacts={a['artifactId'] for a in model.get('artifacts',[])}
    for aid in sorted(artifact_ids-available_artifacts):result['diagnostics'].append({'code':'ARTIFACT_REFERENCE_MISSING','artifactId':aid})
    result['artifacts']=[a for a in model.get('artifacts',[]) if a['artifactId'] in artifact_ids]
    # 同一范围多次补证的诊断去重；不让历史覆盖数量扩大响应。
    result['diagnostics']=list({json.dumps(d,sort_keys=True,ensure_ascii=False):d for d in result['diagnostics']}.values())
    return _finalize_status(result)


def _scan_from_records(root, model, paths, inventory):
    """复用已取声明，只重新读取来源字节以核验；缺失文件才调用语法解析。"""
    constructs={};parsed_paths=set();contents={};source_facts={}
    for record in model.get('sourceRecords',[]):
        c=record.get('sourceConstruct')
        if not c or c['path'] not in paths:continue
        if c['path'] not in contents:contents[c['path']]=(root/c['path']).read_bytes()
        source=contents[c['path']]
        if hashlib.sha256(source).hexdigest()!=c['sha256']:raise ValueError('INPUT_CHANGED')
        construct=SourceConstruct(c['constructId'],c['sourceKey'],c['language'],c['syntaxKind'],c['name'],
            c['path'],c['startByte'],c['endByte'],c.get('parentConstructId'),c['sha256'],
            c['parserId'],c['parserVersion'],c.get('opaque',False),source[c['startByte']:c['endByte']].decode('utf-8',errors='replace'),
            c.get('declaredType'))
        if construct.source_key.startswith('source_fact:'):
            observation=next((v for v in record.get('value',{}).get('observations',[]) if 'factKind' in v),{})
            source_facts.setdefault(c['path'],[]).append(Fact(construct.source_key.removeprefix('source_fact:'),
                observation.get('factKind','constant'),construct.name,construct.path,construct.start_byte,
                construct.end_byte,observation.get('layer','E2'),observation.get('claimMode','syntax'),construct.text,observation.get('owner')))
        else:constructs[construct.construct_id]=construct
        parsed_paths.add(c['path'])
    missing=set(paths)-parsed_paths
    scan=scan_project(root,inventory=tuple(inventory),source_paths=frozenset(missing),include_implementation=False)
    files=list(scan.files)
    for path in sorted(parsed_paths):
        cs=tuple(c for c in constructs.values() if c.path==path)
        files.append(ParseResult(path,cs[0].language,cs[0].source_sha256,tuple(source_facts.get(path,[])),0,
                                 not any(c.opaque for c in cs),('OPAQUE_SOURCE_REUSED',) if any(c.opaque for c in cs) else (),cs))
    return replace(scan,files=tuple(files)),len(missing)


def execute_fact_query(root: Path, request: dict | str, store=None, *, tool_runner=None, cache=None) -> dict:
    root=root.resolve(strict=True);started=time.monotonic()
    if store is not None:store.validate_root(root)
    if cache is not None:cache.validate_root(root)
    try:q=normalize_fact_request(request)
    except (ValueError,TypeError) as error:
        q=normalize_fact_request('modules');result=project_fact_result(_empty_model(q['scopeId']),q)
        result['diagnostics']=[{'code':'INVALID_REQUEST','message':str(error),'request':request}];return result
    if q['scopeId']=='default':q['scopeId']='project:'+hashlib.sha256(str(root).encode()).hexdigest()
    fingerprint=source_fingerprint(root);config=v2_configuration_digest();diagnostics=[]
    refresh_graph=tool_runner is not None and 'relations' in q['facets']
    if q['conditions'].pop('legacyEntitySelector',False) and store is not None:
        try:
            prior=store.read_request(q['scopeId'],q,fingerprint,config)['model']
            matches=[e for e in (prior or {}).get('entities',[]) if e['ref']['identity']['localId']==q['target'].get('name')]
            if len(matches)==1:q['target']={'kind':matches[0]['ref']['kind'],'ref':matches[0]['ref']}
        except (ValueError,OSError,sqlite3.Error) as error:
            diagnostics.append({'code':'STORE_READ_FAILED','message':str(error)})
    if cache is not None and not refresh_graph:
        try:cached=cache.load_v2(root,q,fingerprint,config)
        except (ValueError,OSError,sqlite3.Error) as error:
            cached=None;diagnostics.append({'code':'CACHE_READ_FAILED','message':str(error)})
        if cached is not None and (cached['persistence']['status']=='failed' or any(d.get('retryable') for d in cached['diagnostics'])):
            cached=None
        if cached is not None and store is not None:
            try:
                stored=store.read_request(q['scopeId'],q,fingerprint,config)
                if stored['model'] is None or set(q['facets'])-set(stored['reusedFacets']):cached=None
            except (ValueError,OSError,sqlite3.Error):cached=None
        if cached is not None:
            cached['persistence']={'status':'cache_hit'};cached['cost']={'parsedFiles':0,'algorithmFunctions':0,'elapsedSeconds':time.monotonic()-started,'llmTokens':None,'llmStatus':'not_used','inputFingerprint':fingerprint,'configurationDigest':config}
            return cached
    available={'model':None,'reusedFacets':[],'diagnostics':[]}
    if store is not None:
        try:available=store.read_request(q['scopeId'],q,fingerprint,config)
        except (ValueError,OSError,sqlite3.Error) as error:diagnostics.append({'code':'STORE_READ_FAILED','message':str(error)})
    if refresh_graph:
        available['reusedFacets']=[f for f in available['reusedFacets'] if f!='relations']
    model=available['model'] or _empty_model(q['scopeId'])
    missing=set(q['facets'])-set(available['reusedFacets'])
    parsed_count=0;alg_count=0;persist={'status':'reused' if not missing else 'not_requested'}
    if missing:
        inventory=inventory_tree(root,excluded_dirs=frozenset({'.git'}))
        inventory_dicts=[{'path':e.path,'kind':e.kind} for e in inventory]
        known={'sourceRecords':model['sourceRecords'],'entities':model['entities'],'reusedFacets':available['reusedFacets']}
        # 实体路径只是来源定位线索，不作为语义确认；实际构造仍由证据规则决定。
        located_entities=[]
        for entity in known['entities']:
            mappings=[m for m in model['sourceMappings'] if m.get('target')==entity['ref']]
            located_entities.append({**entity,'path':mappings[0]['sourceConstruct']['path']} if mappings else entity)
        known['entities']=located_entities
        plan=plan_fact_request(q,known,inventory_dicts)
        scan=None
        if plan['stopReasons']==['TARGET_NOT_LOCATED']:
            scan=scan_project(root,inventory=tuple(inventory),source_paths=frozenset(plan['sourcePaths']),include_implementation=False)
            parsed_count=len(scan.files)
            index=collect_source_records(root,scan,{**q,'view':'source','target':{'kind':'all'},'facets':['organization']})
            known['sourceRecords']=index['sourceRecords']
            if q['view']=='entity':
                known['entities']=[{'kind':q['target']['kind'],'name':r['name'],'path':r['path']}
                                   for r in index['sourceRecords'] if r['name']==q['target'].get('name')]
            plan=plan_fact_request(q,known,inventory_dicts)
            if q['view']=='entity' and plan['stopReasons']:
                plan['needs']=[{'target':q['target'],'facet':f,'prerequisites':[],
                                'reason':'通过来源与文档寻找暂定实体映射'} for f in missing]
                plan['stopReasons']=[]
            if plan['stopReasons']:
                diagnostics.append({'code':'TARGET_NOT_ACQUIRED' if any(not f.parse_complete for f in scan.files) else 'SOURCE_TARGET_NOT_FOUND'})
                model={**model,'sourceRecords':index['sourceRecords'],'evidence':index['evidence']}
                plan['needs']=[]
        if plan['diagnostics']:
            diagnostics.extend(plan['diagnostics'])
        if plan['needs'] and not any(d['code']=='AMBIGUOUS_TARGET' for d in diagnostics):
            paths=[] if q['conditions'].get('legacySelector')=='workspace-members' else plan['sourcePaths']
            if q['view']=='entity' and set(q['facets']).intersection({'tests','relations'}):
                paths=[i['path'] for i in inventory_dicts if i['kind']=='file' and i['path'].endswith(('.py','.rs'))]
            selector=q['conditions'].get('legacySelector')
            if selector in {'local-bindings','behavior-contracts','all-supported-facts'}:
                scan=scan_project(root,inventory=tuple(inventory),source_paths=frozenset(paths),
                                  include_implementation=selector in {'local-bindings','all-supported-facts'})
                parsed_count=len(scan.files)
            elif scan is None:
                scan,parsed_count=_scan_from_records(root,model,paths,inventory)
            plan['request']=q
            plan['registry']={key.rsplit(':',1)[-1]:e['ref'] for e in model['entities'] for key in e['sourceKeys'] if key.startswith('candidate:')}
            new=construct_requested_entities(root,scan,plan)
            if q['conditions'].get('legacySelector')=='workspace-members' or (q['conditions'].get('legacySelector')=='all-supported-facts' and (root/'Cargo.toml').is_file()):
                _attach_workspace_members(new,q,root)
            if 'relations' in q['facets'] and q['view']=='source' and tool_runner is None:
                for coverage in new['sourceCoverage']:
                    coverage['status']='partial'
                    coverage['diagnostics'].append({'code':'RELATIONS_NOT_ACQUIRED','facet':'relations','retryable':True,
                        'reason':'未执行关系取得后端；声明解析不能证明调用关系覆盖'})
            if tool_runner is not None and 'relations' in q['facets']:
                _attach_graph_result(new,q,root,tool_runner)
            for cov in new['sourceCoverage']:cov['configurationDigest']=config
            observed_tools={(r['sourceConstruct']['parserId'],r['sourceConstruct']['parserVersion'])
                            for r in new['sourceRecords'] if 'sourceConstruct' in r}
            observed_tools.update((e['toolName'],e.get('toolVersion','unknown')) for e in new['evidence'] if e.get('toolName'))
            new['acquisitionRuns'].append({'runId':'acquisition:'+str(uuid4()),'inputFingerprint':fingerprint,
                'configurationDigest':config,'status':'partial' if any(c['status']!='obtained' for c in new['sourceCoverage']) else 'completed',
                'tools':[{'name':name,'version':version} for name,version in sorted(observed_tools)],
                'sourceRecordIds':[r['recordId'] for r in new['sourceRecords']],
                'evidenceIds':[e['evidenceId'] for e in new['evidence']],
                'artifactIds':[a['artifactId'] for a in new['artifacts']]})
            alg_count=sum('algorithm' in r for r in new['sourceRecords'])
            if source_fingerprint(root)!=fingerprint:raise ValueError('INPUT_CHANGED：查询期间输入发生变化')
            from c2s_semantic_contract.validation import validate_semantic_entity_model_v2
            valid=validate_semantic_entity_model_v2(new)
            if not valid['valid']:raise ValueError('v2构造契约不合法：'+json.dumps(valid['diagnostics'],ensure_ascii=False))
            model=_merge_v2_documents(model,new) if model['sourceRecords'] or model['entities'] else new
            if store is not None:
                try:
                    saved=store.commit_request(str(uuid4()),new,q)
                    readback=store.read_request(q['scopeId'],q,fingerprint,config)
                    if readback['model'] is None:raise ValueError('保存后无法规范回读')
                    model=readback['model'];persist={'status':'saved','generation':saved['generation']}
                    if saved.get('backup'):persist['backup']=saved['backup']
                except (ValueError,OSError,sqlite3.Error) as error:
                    persist={'status':'failed','diagnostic':str(error)}
                    diagnostics.append({'code':'PERSISTENCE_FAILED','message':str(error)})
    result=project_fact_result(model,q);result['diagnostics'].extend(diagnostics)
    known_empty=q['detail']=='list' and result['coverage'] and all(c['status']=='obtained' for c in result['coverage'])
    if not result['items'] and not known_empty and not any(d['code'] in {'AMBIGUOUS_TARGET','SOURCE_TARGET_NOT_FOUND','TARGET_NOT_ACQUIRED'} for d in result['diagnostics']):
        result['diagnostics'].append({'code':'TARGET_NOT_ACQUIRED'})
    result['persistence']=persist
    result['cost']={'parsedFiles':parsed_count,'algorithmFunctions':alg_count,'elapsedSeconds':time.monotonic()-started,'llmTokens':None,'llmStatus':'not_used','inputFingerprint':fingerprint,'configurationDigest':config}
    _finalize_status(result)
    if cache is not None and persist['status']!='failed' and not any(d.get('retryable') for d in result['diagnostics']):
        try:cache.save_v2(root,q,fingerprint,config,result)
        except (ValueError,OSError,sqlite3.Error) as error:result['diagnostics'].append({'code':'CACHE_WRITE_FAILED','message':str(error)})
    return result


def render_fact_result(result: dict, output_format: str='json') -> str:
    encoded=json.dumps(result,ensure_ascii=False,indent=2)
    if output_format=='json':return encoded+'\n'
    if output_format!='markdown':raise ValueError('不支持的输出格式')
    parts=['# 上游事实查询',f"取得 {len(result['items'])} 个请求目标；缺口与证据见完整结果。"]
    for item in result['sourceRecords']:
        if 'pseudocode' in item:parts+=['## '+item['name'],'```text\n'+item['pseudocode']['text']+'\n```','伪代码为来源可追溯的部分静态投影。']
    parts+=['## 事实、证据与覆盖（与JSON相同）','```json\n'+encoded+'\n```']
    return '\n\n'.join(parts)+'\n'


def _attach_graph_result(model, request, root, runner):
    """仅执行显式请求的已点亮图解析；原始响应与新鲜度缺口一起保存。"""
    from dataclasses import asdict
    from .capability_matrix import load_tool_matrix,select_tools,detect_available_tools,host_environment,parse_selected_tool_output
    matrix=load_tool_matrix()
    selection=select_tools(['calls.cross_file.candidates'],matrix,
        available_tools={'code-review-graph'},environment=host_environment())
    diagnostics=[]
    if not selection.complete:
        diagnostics.append({'code':'GRAPH_TOOL_UNAVAILABLE','retryable':True})
    else:
        try:
            supplied=runner('code-review-graph',request)
            raw=supplied.get('response',supplied)
            version=supplied.get('toolVersion')
            parsed=parse_selected_tool_output(selection,'code-review-graph',raw,root,version,matrix)
            artifact_id=stable_id(['code-review-graph',raw,version])
            model['artifacts'].append({'artifactId':artifact_id,'kind':'tool_output','payload':raw})
            eid=stable_id(['tool_evidence',artifact_id])
            model['evidence'].append({'evidenceId':eid,'source':'tool_output','description':'图工具结构化响应：'+artifact_id,
                'method':'structured_output','toolName':'code-review-graph','toolVersion':version or 'unknown'})
            diagnostics.extend({'code':d.code,'message':d.message,'artifactId':artifact_id,
                                **({'retryable':True} if d.code!='GRAPH_INDEX_FRESHNESS_UNVERIFIED' else {})}
                               for d in parsed.diagnostics)
            diagnostics.append({'code':'GRAPH_TOOL_EVIDENCE','artifactId':artifact_id,'evidenceIds':[eid]})
            for call in parsed.call_sites:
                parents=[r for r in model['sourceRecords'] if r['path']==call.caller_path
                         and r.get('sourceConstruct',{}).get('name') in {call.caller_name,call.caller_name.rsplit('::',1)[-1]}]
                module=next((r for r in model['sourceRecords'] if r['kind']=='source_module' and r['path']==call.caller_path),None)
                parent=parents[0] if parents else module
                model['sourceRecords'].append({'recordId':stable_id(['graph_call',asdict(call),artifact_id]),
                    'kind':'call_candidate','name':call.caller_name+' → '+call.callee_name,'path':call.caller_path,
                    'sourceConstructIds':[],'parentRecordIds':[parent['recordId']] if parent else [],
                    'relatedRecords':[],'evidenceIds':[eid],'status':'partial',
                    'value':{'observations':[{**asdict(call),'claimMode':'static_may','artifactId':artifact_id}]}})
        except (OSError,ValueError,TypeError,KeyError) as error:
            diagnostics.append({'code':'GRAPH_TOOL_FAILED','retryable':True,'message':str(error)})
    for cov in model['sourceCoverage']:
        cov['status']='partial';cov['diagnostics'].extend(diagnostics)


def _finalize_status(result):
    operational={'PERSISTENCE_FAILED','CACHE_READ_FAILED','CACHE_WRITE_FAILED','GRAPH_TOOL_EVIDENCE','WORKSPACE_TOOL_EVIDENCE'}
    codes={d['code'] for d in result['diagnostics'] if d['code'] not in operational}
    if 'AMBIGUOUS_TARGET' in codes:status='ambiguous'
    elif 'SOURCE_TARGET_NOT_FOUND' in codes:status='not_found'
    elif codes.intersection({'INVALID_REQUEST','TARGET_NOT_ACQUIRED','FACT_ARCHIVE_NOT_FOUND'}):status='not_acquired'
    elif codes or any(c['status']!='obtained' for c in result['coverage']):status='partial'
    else:status='obtained' if result['items'] or result['coverage'] else 'not_acquired'
    result.update(status=status,complete=status=='obtained')
    return result


def _attach_workspace_members(model,request,root):
    from .entity_construction import _fact_evidence
    raw=[];facts,gap=cargo_workspace_facts(root,raw_output=raw)
    for payload in raw:
        artifact_id=stable_id(['cargo_metadata',payload])
        model['artifacts'].append({'artifactId':artifact_id,'kind':'tool_output','payload':payload})
    parents=[r['recordId'] for r in model['sourceRecords'] if r['kind']=='workspace' and r['path']=='Cargo.toml']
    for fact in facts:
        ev=_fact_evidence(root,fact);ev['source']='tool_output';ev['toolName']='cargo'
        ev['toolVersion']=raw[0].get('toolVersion','unknown') if raw else 'unknown'
        if not any(e['evidenceId']==ev['evidenceId'] for e in model['evidence']):model['evidence'].append(ev)
        path=fact.owner or 'Cargo.toml'
        observation={'nativeWorkspaceMember':True,'packageName':fact.name,'manifestPath':path}
        if raw:observation['artifactId']=stable_id(['cargo_metadata',raw[0]])
        model['sourceRecords'].append({'recordId':stable_id([request['scopeId'],model['sourceCoverage'][0]['inputFingerprint'],fact.id,'native_workspace_member']),
            'kind':'package','name':fact.name,'path':path,'sourceConstructIds':[],
            'parentRecordIds':parents,'relatedRecords':[],'evidenceIds':[ev['evidenceId']],
            'status':'obtained','value':{'observations':[observation]}})
    for cov in model['sourceCoverage']:
        workspace_only=request['conditions'].get('legacySelector')=='workspace-members'
        if workspace_only:cov['diagnostics']=[];cov['status']='obtained'
        if gap:
            cov['status']='not_acquired' if workspace_only else 'partial'
            cov['diagnostics'].append({'code':'WORKSPACE_NOT_ACQUIRED','message':gap,'retryable':True})
        for payload in raw:
            cov['diagnostics'].append({'code':'WORKSPACE_TOOL_EVIDENCE','artifactId':stable_id(['cargo_metadata',payload])})
