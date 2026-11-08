"""在固定Git副本上遍历v2已发布事实，并用独立语法盘点和字节证据对照。"""
from __future__ import annotations
import argparse
import ast
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'skill/src')]
from c2s_semantic_contract.validation import validate_semantic_entity_model_v2
from c2s_skill.fact_query import (execute_fact_query,project_fact_result,prepare_fact_projection_index)
from c2s_skill.fact_request import normalize_fact_request
from c2s_skill.inventory import inventory_tree,source_fingerprint
from c2s_skill.semantic_store import SemanticEntityStore
from c2s_skill.algorithm import validate_algorithms


def _native_declarations(root: Path, entries: list) -> tuple[set,list]:
    """直接使用原生AST/语法节点盘点类型和可调用定义，不调用产品构造器。"""
    declarations=set();gaps=[]
    for entry in entries:
        if entry.kind!='file' or Path(entry.path).suffix not in {'.py','.rs'}:continue
        source=(root/entry.path).read_bytes()
        if entry.path.endswith('.py'):
            try:tree=ast.parse(source,filename=entry.path)
            except (SyntaxError,UnicodeError):gaps.append(entry.path);continue
            lines=source.splitlines(keepends=True);offsets=[0]
            for line in lines:offsets.append(offsets[-1]+len(line))
            for node in ast.walk(tree):
                if isinstance(node,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
                    declarations.add((entry.path,node.name,offsets[node.lineno-1]+node.col_offset,
                                      offsets[node.end_lineno-1]+node.end_col_offset))
        else:
            from tree_sitter import Parser,Language
            import tree_sitter_rust
            tree=Parser(Language(tree_sitter_rust.language())).parse(source)
            if tree.root_node.has_error:gaps.append(entry.path)
            stack=[tree.root_node]
            while stack:
                node=stack.pop();stack.extend(node.named_children)
                if node.type in {'function_item','struct_item','enum_item','trait_item'}:
                    name=node.child_by_field_name('name')
                    if name:declarations.add((entry.path,source[name.start_byte:name.end_byte].decode(),node.start_byte,node.end_byte))
    return declarations,gaps


def verify_published_model(model: dict, root: Path, *, expected_fingerprint: str | None = None) -> dict:
    result={'valid':False,'diagnostics':[],'sourceDeclarationsVerified':0,
            'semanticInterpretationComplete':False,'sourceQueriesVerified':0,'entityQueriesVerified':0,
            'evidenceVerified':0,'algorithmsVerified':0,'claimsVerified':0,'relationsVerified':0,'mappingsVerified':0}
    if expected_fingerprint is not None and source_fingerprint(root)!=expected_fingerprint:
        result['diagnostics'].append({'code':'INPUT_CHANGED'});return result
    valid=validate_semantic_entity_model_v2(model)
    if not valid['valid']:
        result['diagnostics'].append({'code':'CONTRACT_INVALID','details':valid['diagnostics']});return result
    entries=inventory_tree(root,excluded_dirs=frozenset({'.git'}))
    expected_paths={e.path for e in entries if e.kind=='file' and Path(e.path).suffix in {'.py','.rs'}}
    modules={s['path'] for s in model['sourceRecords'] if s['kind']=='source_module'}
    for missing in sorted(expected_paths-modules):result['diagnostics'].append({'code':'SOURCE_MODULE_MISSING','path':missing})
    baseline,parse_gaps=_native_declarations(root,entries)
    actual={(s['path'],s['sourceConstruct']['name'],s['sourceConstruct']['startByte'],s['sourceConstruct']['endByte'])
            for s in model['sourceRecords'] if s.get('sourceConstruct',{}).get('syntaxKind') in
            {'class_declaration','function_declaration','struct_declaration','enum_declaration','trait_declaration'}}
    for missing in sorted(baseline-actual):result['diagnostics'].append({'code':'SOURCE_DECLARATION_MISSING','location':list(missing)})
    result['sourceDeclarationsVerified']=len(baseline&actual)
    result['nativeParseGaps']=parse_gaps
    result['baselineKinds']=['Python类与函数','Rust函数/结构体/枚举/trait']
    contents={};hashes={}
    for evidence in model['evidence']:
        if 'path' not in evidence:continue
        path=evidence['path'];full=root/path
        if not full.resolve().is_relative_to(root) or not full.is_file() or full.is_symlink():
            result['diagnostics'].append({'code':'SOURCE_EVIDENCE_PATH_INVALID','path':path});continue
        if path not in contents:
            contents[path]=full.read_bytes();hashes[path]=hashlib.sha256(contents[path]).hexdigest()
        if hashes[path]!=evidence['sha256']:
            result['diagnostics'].append({'code':'SOURCE_HASH_MISMATCH','path':path})
        if not 0<=evidence['startByte']<=evidence['endByte']<=len(contents[path]):
            result['diagnostics'].append({'code':'SOURCE_SPAN_INVALID','path':path})
        result['evidenceVerified']+=1
    index=prepare_fact_projection_index(model)
    checked_claims=set();checked_relations=set();checked_mappings=set()
    def canonical(values):return sorted(json.dumps(v,sort_keys=True,ensure_ascii=False) for v in values)
    for record in model['sourceRecords']:
        q=normalize_fact_request({'scopeId':model['scopeId'],'view':'source',
            'target':{'kind':'all','ref':{'recordId':record['recordId']}},'detail':'self','facets':['implementation']})
        projected=project_fact_result(model,q,index=index)
        if projected['items']!=[record]:result['diagnostics'].append({'code':'SOURCE_QUERY_LOSS','recordId':record['recordId']})
        result['sourceQueriesVerified']+=1
        if 'algorithm' in record:
            errors=validate_algorithms({'schema_version':'1.0.0','algorithms':[record['algorithm']]})
            if errors:result['diagnostics'].append({'code':'ALGORITHM_INVALID','recordId':record['recordId'],'details':errors})
            if record.get('pseudocode',{}).get('complete') is not False:
                result['diagnostics'].append({'code':'PSEUDOCODE_COMPLETENESS_INVALID','recordId':record['recordId']})
            evidence_ids={e['evidenceId'] for e in model['evidence']}
            if not set(record['algorithm'].get('evidence_refs',[])).issubset(evidence_ids):
                result['diagnostics'].append({'code':'ALGORITHM_EVIDENCE_MISSING','recordId':record['recordId']})
            result['algorithmsVerified']+=1
    for entity in model['entities']:
        q=normalize_fact_request({'scopeId':model['scopeId'],'view':'entity',
            'target':{'kind':entity['ref']['kind'],'ref':entity['ref']},'detail':'self','facets':['attributes','implementation','tests']})
        projected=project_fact_result(model,q,index=index)
        if len(projected['items'])!=1 or projected['items'][0]['attributes']!=entity['attributes']:
            result['diagnostics'].append({'code':'ENTITY_QUERY_LOSS','entity':entity['ref']})
        if projected['items']:
            from c2s_skill.semantic_store import _identity_key
            key=_identity_key(entity['ref']);item=projected['items'][0]
            expected_claims=index['claims'].get(key,[])
            expected_relations=index['relations'].get(key,[])
            expected_mappings=index['mappings'].get(key,[])
            if canonical(projected['claims'])!=canonical(expected_claims):
                result['diagnostics'].append({'code':'CLAIM_QUERY_LOSS','entity':entity['ref']})
            if canonical(item.get('relations',[]))!=canonical(expected_relations):
                result['diagnostics'].append({'code':'RELATION_QUERY_LOSS','entity':entity['ref']})
            if canonical(item.get('sourceMappings',[]))!=canonical(expected_mappings):
                result['diagnostics'].append({'code':'MAPPING_QUERY_LOSS','entity':entity['ref']})
            checked_claims.update(c['claimId'] for c in expected_claims)
            checked_relations.update(v['relationId'] for v in expected_relations)
            checked_mappings.update(v['mappingId'] for v in expected_mappings)
        result['entityQueriesVerified']+=1
    for mapping in model.get('sourceMappings',[]):
        if 'identity' not in mapping.get('target',{}):
            if mapping['sourceConstruct']['constructId'] not in index['sourcesByConstruct']:
                result['diagnostics'].append({'code':'UNMAPPED_SOURCE_LOSS','mappingId':mapping['mappingId']})
            checked_mappings.add(mapping['mappingId'])
    result.update(claimsVerified=len(checked_claims),relationsVerified=len(checked_relations),
                  mappingsVerified=len(checked_mappings),evidenceRecordsTraversed=len(model['evidence']),
                  diagnosticsTraversed=sum(len(c['diagnostics']) for c in model['sourceCoverage']))
    if len(checked_claims)!=len(model['claims']) or len(checked_relations)!=len(model['relations']):
        result['diagnostics'].append({'code':'PUBLISHED_FACT_NOT_TRAVERSED'})
    result['publishedCollections']={k:len(model[k]) for k in ['entities','sourceRecords','claims','relations','evidence','coverage','sourceCoverage','acquisitionRuns','artifacts']}
    result['analysisGapCount']=sum(len(c['diagnostics']) for c in model['sourceCoverage'])
    result['valid']=not result['diagnostics']
    return result


def run_verification(project: Path, expected_commit: str, store_path: Path, algorithms: list[str]) -> dict:
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=project,text=True).strip()
    if actual!=expected_commit:raise ValueError('真实项目提交与指定版本不同')
    if store_path.exists():raise ValueError('冷启动验证要求使用尚不存在的独立数据库')
    if store_path.resolve().is_relative_to(project.resolve()):raise ValueError('验证数据库必须位于分析项目外')
    original=source_fingerprint(project)
    raw=subprocess.check_output(['git','archive',expected_commit],cwd=project)
    with tempfile.TemporaryDirectory(prefix='c2s-v2-verification-') as temp:
        root=Path(temp)/'source';root.mkdir()
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:archive.extractall(root,filter='data')
        fingerprint=source_fingerprint(root);store=SemanticEntityStore(store_path)
        scope='verification:'+project.name+':'+expected_commit
        requests=[normalize_fact_request({'scopeId':scope,'view':'source','target':{'kind':'all'},'facets':['organization'],'detail':'list'}),
                  normalize_fact_request({'scopeId':scope,'view':'entity','target':{'kind':'all'},'facets':['attributes','relations','implementation','tests'],'detail':'list'})]
        if (root/'Cargo.toml').is_file():
            workspace_request=normalize_fact_request('workspace-members');workspace_request['scopeId']=scope
            requests.insert(1,workspace_request)
        for specification in algorithms:
            path,separator,name=specification.partition('::')
            if not separator:raise ValueError('算法参数格式为相对路径::函数名')
            requests.append(normalize_fact_request({'scopeId':scope,'view':'entity',
                'target':{'kind':'ComputationEntity','name':name,'path':path},'facets':['algorithm','implementation'],'detail':'self'}))
        metrics=[];model=None;target_first=None;query_order_checks=[]
        for request in requests:
            cold=execute_fact_query(root,request,store)
            hot=execute_fact_query(root,request,store)
            same=(cold['items']==hot['items'] and cold['sourceRecords']==hot['sourceRecords'] and cold['diagnostics']==hot['diagnostics'])
            metrics.append({'request':request,'first':cold['cost'],'repeat':hot['cost'],
                            'sameFactsAndGaps':same,'firstPersistence':cold['persistence'],
                            'repeatPersistence':hot['persistence'],'itemCount':len(cold['items'])})
            if not same:raise ValueError('重复查询的事实或缺口不一致')
            if not cold['items']:raise ValueError('指定验证请求未取得目标：'+json.dumps(cold['diagnostics'],ensure_ascii=False)[:1000])
            model=store.read_request(scope,request,fingerprint,cold['cost']['configurationDigest'])['model']
            if len(metrics)==1 and request['view']=='source' and request['target']=={'kind':'all'}:
                sources=model['sourceRecords']
                field_parents={r['sourceConstruct'].get('parentConstructId') for r in sources
                               if r.get('sourceConstruct',{}).get('syntaxKind')=='field_declaration'}
                sample=next((r for r in sources if r.get('sourceConstruct',{}).get('syntaxKind') in
                             {'class_declaration','struct_declaration'} and
                             r['sourceConstruct']['constructId'] in field_parents),None)
                if sample:
                    targeted=normalize_fact_request({'scopeId':scope,'view':'entity','detail':'self',
                        'target':{'kind':'DataEntity','name':sample['name'],'path':sample['path']},'facets':['attributes']})
                    requests.insert(1,targeted)
            elif request['view']=='entity' and request['target']['kind']=='DataEntity':
                target_first=(request,cold['items'][0]['attributes'])
            elif request['view']=='entity' and request['target']=={'kind':'all'} and target_first:
                after=execute_fact_query(root,target_first[0],store)
                same=bool(after['items']) and target_first[1]==after['items'][0]['attributes']
                query_order_checks.append({'target':target_first[0]['target'],'sameAttributes':same,
                    'targetedBeforeBroader':True,'afterBroaderParsedFiles':after['cost']['parsedFiles']})
                if not same:raise ValueError('定向→全范围→定向查询的属性发生不一致')
        checked=verify_published_model(model,root,expected_fingerprint=fingerprint)
        if source_fingerprint(root)!=fingerprint:raise ValueError('隔离源项目被分析修改')
        if source_fingerprint(project)!=original:raise ValueError('原始输入项目发生变化')
        import platform,importlib.metadata
        environment={'host':platform.platform(),'python':platform.python_version(),
                     'treeSitter':importlib.metadata.version('tree-sitter'),
                     'rustGrammar':importlib.metadata.version('tree-sitter-rust'),'target':'未验证；不由host推定'}
        return {'project':project.name,'commit':expected_commit,'inputFingerprint':fingerprint,
                'environment':environment,'sourceTreeUnchanged':True,
                'verification':checked,'requests':metrics,'queryOrderChecks':query_order_checks,'databaseBytes':store_path.stat().st_size,
                'llmUsage':'未使用；不宣称词元节省','coverageScope':'全部已发布来源/实体/证据/关系和显式请求算法；未请求算法未展开，语义解释不视为已证明完整。'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True);parser.add_argument('--expected-commit',required=True)
    parser.add_argument('--store',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--algorithm',action='append',default=[])
    args=parser.parse_args(argv)
    if args.output.resolve().is_relative_to(args.project.resolve()):raise ValueError('输出必须在输入项目外')
    result=run_verification(args.project.resolve(),args.expected_commit,args.store.resolve(),args.algorithm)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'project':result['project'],'valid':result['verification']['valid'],
                      'collections':result['verification']['publishedCollections']},ensure_ascii=False))
    return 0 if result['verification']['valid'] else 2

if __name__=='__main__':raise SystemExit(main())
