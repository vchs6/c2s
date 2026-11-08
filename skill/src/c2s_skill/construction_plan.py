"""为请求缺口选择必要来源和已点亮工具，不预构造全仓解释。"""
from .capability_matrix import load_tool_matrix, select_tools, detect_available_tools, host_environment


def matching_records(request: dict, records: list[dict]) -> list[dict]:
    target=request['target'];kind=target['kind'];out=[]
    for item in records:
        syntax=item.get('sourceConstruct',{}).get('syntaxKind','')
        match=(kind=='all' or item.get('kind',item.get('ref',{}).get('kind'))==kind or
               (kind=='module' and item.get('kind')=='source_module') or
               (kind=='project' and item.get('kind')=='project_manifest') or
               (kind=='function' and ('function' in syntax or 'method' in syntax)))
        if not match:continue
        if target.get('name') and item.get('name')!=target['name']:continue
        if target.get('path') and item.get('path')!=target['path']:continue
        if target.get('ref') and target['ref'] not in (item.get('ref'),{'recordId':item.get('recordId')}):continue
        legacy=request.get('conditions',{}).get('legacySelector')
        if legacy=='classes' and not any(x in syntax for x in ('class','struct','enum','trait')):continue
        if legacy=='workspace-members' and not any(v.get('nativeWorkspaceMember') for v in item.get('value',{}).get('observations',[])):continue
        out.append(item)
    return out


def plan_fact_request(request: dict, available: dict, inventory: list[dict]) -> dict:
    records=available.get('sourceRecords',[]) if request['view']=='source' else available.get('entities',[])
    candidates=matching_records(request,records)
    result={'request':request,'needs':[],'selectedTools':[],'sourcePaths':[],'stopReasons':[],'diagnostics':[], 'candidates':candidates}
    target=request['target']
    if (target.get('name') or target.get('ref')) and len(candidates)>1:
        result['diagnostics']=[{'code':'AMBIGUOUS_TARGET','candidates':[c.get('recordId',c.get('ref')) for c in candidates]}]
        return result
    allpaths=[x['path'] for x in inventory if x.get('kind')=='file' and x['path'].endswith(('.py','.rs'))]
    if not candidates and (target.get('name') or target.get('ref')):
        result['sourcePaths']=allpaths
        result['needs']=[{'target':target,'facet':'locate','prerequisites':[],
                          'reason':'仅建立必要声明定位索引，定位后重新计划'}]
        result['stopReasons']=['TARGET_NOT_LOCATED'];return result
    paths=sorted({c['path'] for c in candidates if c.get('path','').endswith(('.py','.rs'))})
    if not paths and request['view']=='entity':paths=allpaths
    if not paths and target['kind'] in {'all','module','function','declaration'}:paths=allpaths
    result['sourcePaths']=paths
    matrix=load_tool_matrix()
    available_tools=set(available['availableTools']) if 'availableTools' in available else detect_available_tools(matrix)
    for facet in request['facets']:
        if facet in available.get('reusedFacets',[]):continue
        capabilities=[]
        for lang,ext in [('python','.py'),('rust','.rs')]:
            if any(p.endswith(ext) for p in paths):
                suffix='algorithm_structure' if facet=='algorithm' else 'declarations'
                capabilities.append(f'source.{lang}.{suffix}')
        selected=select_tools(capabilities,matrix,available_tools=available_tools,environment=host_environment())
        result['selectedTools']=sorted(set(result['selectedTools'])|set(selected.tools))
        if selected.uncovered:
            result['diagnostics'].append({'code':'TOOL_UNAVAILABLE','facet':facet,'capabilities':list(selected.uncovered)})
            continue
        result['needs'].append({'target':target,'facet':facet,'prerequisites':[],
                                'reason':'请求描述面未在当前输入/配置取得覆盖'})
    return result
