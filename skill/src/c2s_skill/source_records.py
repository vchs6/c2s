"""保留有证据的来源组织，不要求先建立语义映射。"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tomllib
from .acquisition import ProjectScan, analysis_profile_digest
from .inventory import source_fingerprint
from .entity_construction import _construct_evidence


def stable_id(value: object) -> str:
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,
                                    separators=(',',':')).encode()).hexdigest()


def collect_source_records(root: Path, scan: ProjectScan, request: dict) -> dict:
    root=root.resolve(strict=True)
    if Path(scan.root).resolve()!=root or source_fingerprint(root)!=scan.source_digest:
        raise ValueError('INPUT_CHANGED：来源扫描输入不匹配')
    scope=request.get('scopeId','project:'+stable_id(str(root)))
    records={}; evidence={}; diagnostics=[]
    def record(kind,path,name,start=0,end=0,slot='',ev=None,construct=None,value=None,status='obtained'):
        key=stable_id([scope,scan.source_digest,kind,path,start,end,slot])
        if key not in records:
            records[key]={'recordId':key,'kind':kind,'name':name,'path':path,
                'sourceConstructIds':[],'parentRecordIds':[],'relatedRecords':[],
                'evidenceIds':[],'status':status}
        item=records[key]
        if ev:
            evidence[ev['evidenceId']]=ev
            if ev['evidenceId'] not in item['evidenceIds']:item['evidenceIds'].append(ev['evidenceId'])
        if construct:
            if construct.construct_id not in item['sourceConstructIds']:item['sourceConstructIds'].append(construct.construct_id)
            item.setdefault('sourceConstruct',{'constructId':construct.construct_id,'sourceKey':construct.source_key,
                'language':construct.language,'syntaxKind':construct.syntax_kind,'name':construct.name,
                'path':construct.path,'sha256':construct.source_sha256,'startByte':construct.start_byte,
                'endByte':construct.end_byte,'parserId':construct.parser_id,'parserVersion':construct.parser_version,
                'opaque':construct.opaque,
                **({'declaredType':construct.declared_type} if construct.declared_type is not None else {}),
                **({'parentConstructId':construct.parent_id} if construct.parent_id else {})})
        if value is not None:
            observations=item.setdefault('value',{'observations':[]})['observations']
            if value not in observations:
                if observations:diagnostics.append({'code':'TOOL_DISAGREEMENT','recordId':key})
                observations.append(value)
        return item
    def file_evidence(path,source,method):
        return {'evidenceId':stable_id([path,hashlib.sha256(source).hexdigest(),method]),
            'source':'input','description':'来源直接记录','path':path,
            'sha256':hashlib.sha256(source).hexdigest(),'startByte':0,'endByte':len(source),'method':method}
    directory_ids={'.':record('directory','.','.')['recordId']}
    for entry in scan.inventory:
        if entry.kind=='directory':directory_ids[entry.path]=record('directory',entry.path,Path(entry.path).name)['recordId']
    parsed_by_path={f.path:f for f in scan.files}
    module_ids={}
    for entry in scan.inventory:
        if entry.kind!='file':continue
        path=entry.path; full=root/path
        if Path(path).suffix in {'.py','.rs'}:
            parsed=parsed_by_path.get(path)
            status='obtained' if parsed and parsed.parse_complete else 'partial' if parsed else 'not_acquired'
            ev=file_evidence(path,full.read_bytes(),'source_inventory')
            module_ids[path]=record('source_module',path,Path(path).stem,ev=ev,status=status)['recordId']
        if Path(path).name in {'Cargo.toml','pyproject.toml'}:
            source=full.read_bytes(); ev=file_evidence(path,source,'tomllib')
            try:
                metadata=tomllib.loads(source.decode());table=metadata.get('package',metadata.get('project',{}))
                name=table.get('name',Path(path).parent.name)
                record('project_manifest',path,str(name),ev=ev,value=metadata)
                if 'workspace' in metadata:record('workspace',path,'workspace',slot='workspace',ev=ev,value=metadata['workspace'])
                if table:record('package',path,str(name),slot='package',ev=ev,value=table)
            except (UnicodeError,tomllib.TOMLDecodeError) as error:
                diagnostics.append({'code':'MANIFEST_PARSE_ERROR','path':path,'message':str(error)})
    construct_records={}
    for parsed in scan.files:
        for construct in parsed.constructs:
            ev=_construct_evidence(root,construct,description='来源声明及解析器证据')
            rec=record('test_entry' if construct.name.startswith('test_') else 'declaration',
                construct.path,construct.name,construct.start_byte,construct.end_byte,construct.syntax_kind,
                ev,construct,{'declaredType':construct.declared_type})
            construct_records[construct.construct_id]=rec
    for parsed in scan.files:
        for construct in parsed.constructs:
            rec=construct_records[construct.construct_id]
            parent=construct_records.get(construct.parent_id)
            pid=parent['recordId'] if parent else module_ids.get(construct.path)
            if pid and pid not in rec['parentRecordIds']:rec['parentRecordIds'].append(pid)
    for item in records.values():
        if item['kind'] in {'declaration','test_entry'}:continue
        parent=str(Path(item['path']).parent)
        if item['path']!='.' and parent in directory_ids:item['parentRecordIds']=[directory_ids[parent]]
    processed=[f.path for f in scan.files if f.parse_complete]
    unprocessed=[e.path for e in scan.inventory if e.kind=='file' and e.path not in processed
                 and Path(e.path).name not in {'Cargo.toml','pyproject.toml'}]
    for f in scan.files:
        diagnostics.extend({'code':'SOURCE_PARSE_GAP','path':f.path,'message':d} for d in f.diagnostics)
    cov={'coverageId':stable_id([scope,scan.source_digest,request]),'inputFingerprint':scan.source_digest,
         'configurationDigest':analysis_profile_digest(),'view':'source','target':request.get('target',{'kind':'all'}),
         'facets':request.get('facets',['organization']),'conditions':request.get('conditions',{}),
         'status':'partial' if unprocessed or diagnostics else 'obtained',
         'processedPaths':processed,'unprocessedPaths':unprocessed,'diagnostics':diagnostics}
    return {'sourceRecords':list(records.values()),'evidence':list(evidence.values()),
            'sourceCoverage':[cov],'diagnostics':diagnostics}
