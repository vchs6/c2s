"""解析CodeGraph 1.6.2公开JSON协议；只发布关系候选及明确覆盖缺口。"""
import json
from pathlib import Path
from .source_records import stable_id


def parse_codegraph_response(response: dict | list, root: Path, query_kind: str) -> dict:
    root=root.resolve(strict=True)
    raw=response
    wrapped=isinstance(response,dict) and 'payload' in response and 'toolVersion' in response
    version=response.get('toolVersion') if wrapped else None
    if wrapped:response=response['payload']
    diagnostics=[{'code':'GRAPH_INDEX_FRESHNESS_UNVERIFIED'}, {'code':'GRAPH_ENUMERATION_UNPROVEN'}]
    if wrapped and 'truncat' in str(raw.get('stderr','')).lower():
        diagnostics.append({'code':'GRAPH_RESULTS_TRUNCATED','message':raw['stderr']})
    if version!='1.6.2':diagnostics.append({'code':'GRAPH_VERSION_UNVERIFIED','version':version})
    artifact={'artifactId':stable_id(['codegraph',query_kind,raw]),'kind':'tool_output','payload':raw}
    candidates={};relations=[]
    def node(item):
        if not isinstance(item,dict):
            diagnostics.append({'code':'GRAPH_NODE_INVALID'});return None
        path=item.get('filePath',item.get('path'))
        if not isinstance(path,str) or not path or Path(path).is_absolute() or '..' in Path(path).parts or '\\' in path or ':' in path:
            diagnostics.append({'code':'GRAPH_PATH_INVALID','path':path});return None
        full=root/path
        if not full.resolve().is_relative_to(root) or not full.is_file() or full.is_symlink():
            diagnostics.append({'code':'GRAPH_PATH_INVALID','path':path});return None
        start=item.get('startLine',1);end=item.get('endLine',start)
        if type(start)!=int or type(end)!=int or start<1 or end<start:
            diagnostics.append({'code':'GRAPH_POSITION_INVALID','path':path});return None
        source=full.read_bytes();lines=source.splitlines(keepends=True)
        if start>max(1,len(lines)) or end>max(1,len(lines)):
            diagnostics.append({'code':'GRAPH_POSITION_INVALID','path':path});return None
        identifier=stable_id([path,start,end,item.get('qualifiedName',item.get('name')),item.get('kind')])
        result={'candidateId':identifier,'name':item.get('qualifiedName',item.get('name',path)),
            'kind':item.get('kind','file'),'path':path,'startByte':sum(len(x) for x in lines[:start-1]),
            'endByte':sum(len(x) for x in lines[:end]),'upstreamId':item.get('id'),
            'claimMode':'static_may','artifactId':artifact['artifactId']}
        candidates[identifier]=result;return result
    if query_kind in {'query','files'} and isinstance(response,list):
        for item in response:node(item.get('node',item) if isinstance(item,dict) else item)
    elif query_kind in {'callers','callees'} and isinstance(response,dict) and isinstance(response.get('definitions'),list):
        if response.get('ambiguous'):diagnostics.append({'code':'GRAPH_TARGET_AMBIGUOUS'})
        for definition in response['definitions']:
            if not isinstance(definition,dict) or not isinstance(definition.get(query_kind),list):
                diagnostics.append({'code':'GRAPH_OUTPUT_INVALID'});continue
            owner=node(definition.get('definition'))
            for other in definition[query_kind]:
                target=node(other)
                if not owner or not target:continue
                left,right=(owner,target) if query_kind=='callees' else (target,owner)
                relations.append({'subjectCandidateId':left['candidateId'],'targetCandidateId':right['candidateId'],
                    'predicate':'calls_candidate','claimMode':'static_may','artifactId':artifact['artifactId']})
    else:diagnostics.append({'code':'GRAPH_OUTPUT_INVALID'})
    return {'candidates':list(candidates.values()),'relations':relations,'artifact':artifact,
            'toolVersion':version,'coverage':{'complete':False,'returned':len(candidates)},'diagnostics':diagnostics}
