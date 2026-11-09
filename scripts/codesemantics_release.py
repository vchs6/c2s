"""自包含Skill的白名单构建、完整性校验与事务安装。"""
import argparse
from contextlib import contextmanager
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

NAME='codesemantics'
VERSION='0.1.0'
MAX_BYTES=64*1024*1024
MAX_FILES=256


def _relative(name):
    if not isinstance(name,str) or not name or '\\' in name or ':' in name:
        raise ValueError('分发路径无效')
    path=PurePosixPath(name)
    if path.is_absolute() or any(p in {'..','.'} for p in name.split('/')) or path.as_posix()!=name:
        raise ValueError('分发路径不能逃逸目标')
    devices={'CON','PRN','AUX','NUL'}|{prefix+str(i) for prefix in ('COM','LPT') for i in range(1,10)}
    if any(part.rstrip(' .')!=part or part.split('.')[0].upper() in devices for part in path.parts):
        raise ValueError('分发路径不能使用设备名或不明确尾缀')
    return path


def validate_bundle(root,allow_environment=False):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ValueError('分发目录不能是链接')
    metadata=root/'manifest.json'
    if metadata.is_symlink() or metadata.stat().st_size>256*1024:raise ValueError('分发清单无效')
    manifest=json.loads(metadata.read_text(encoding='utf-8'))
    if not isinstance(manifest,dict):raise ValueError('分发清单必须是对象')
    if manifest.get('name')!=NAME or manifest.get('format')!=1 or manifest.get('version')!=VERSION:
        raise ValueError('分发清单名称或格式不符')
    files=manifest.get('files')
    if not isinstance(files,dict) or not files or len(files)>MAX_FILES:raise ValueError('分发文件数量无效')
    total=0
    for name,digest in files.items():
        _relative(name)
        if name=='manifest.json' or name.split('/')[0]=='.venv':raise ValueError('清单包含保留路径')
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):raise ValueError('文件摘要无效')
        path=root/name
        for parent in [path,*path.parents]:
            if parent==root.parent:break
            if parent.is_symlink():raise ValueError('分发不接受符号链接')
        if not path.is_file():raise ValueError('分发文件缺失：'+name)
        total+=path.stat().st_size
        if total>MAX_BYTES:raise ValueError('分发内容超过大小限制')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('分发文件摘要不符：'+name)
    required={'SKILL.md','README.md','install.py','scripts/codesemantics.py','scripts/check.py','requirements.txt'}
    if not required<=files.keys():raise ValueError('分发缺少必要入口')
    expected=set(files)|{'manifest.json'}
    actual=set()
    for parent,dirs,names in os.walk(root,followlinks=False):
        relative=Path(parent).relative_to(root)
        for directory in list(dirs):
            path=Path(parent)/directory
            if path.is_symlink():raise ValueError('分发目录不接受符号链接')
            if relative==Path('.') and directory=='.venv' and allow_environment:dirs.remove(directory)
        for name in names:actual.add((Path(parent)/name).relative_to(root).as_posix())
    if actual!=expected:raise ValueError('分发存在未登记文件')
    return manifest


def build_bundle(repo,destination):
    repo=Path(repo).resolve();destination=Path(destination)
    if destination.exists() or destination.is_symlink():raise FileExistsError(str(destination))
    mapping={
      'SKILL.md':repo/'skill/SKILL.md','README.md':repo/'skill/README.md',
      '使用说明.md':repo/'skill/使用说明.md','LICENSE':repo/'LICENSE',
      'requirements.txt':repo/'requirements-skill.txt','install.py':repo/'scripts/install_codesemantics.py',
      'scripts/codesemantics_release.py':repo/'scripts/codesemantics_release.py'}
    for path in (repo/'skill/scripts').glob('*.py'):mapping['scripts/'+path.name]=path
    for directory,target in ((repo/'skill/src/codesemantics','runtime/skill/src/codesemantics'),
                             (repo/'src/codesemantics_contract','runtime/src/codesemantics_contract')):
        for path in directory.glob('*.py'):mapping[target+'/'+path.name]=path
    for name in ('semantic-fact-request-2.schema.json','semantic-fact-result-2.schema.json',
                 'semantic-algorithm.schema.json','tool-capabilities.json'):
        mapping['runtime/skill/contracts/'+name]=repo/'skill/contracts'/name
    for name in ('semantic-entity-model-2.schema.json','semantic-entity-types.json',
                 'semantic-entity-predicates.json','semantic-entity-v2-catalog-manifest.json'):
        mapping['runtime/contracts/semantic-model/'+name]=repo/'contracts/semantic-model'/name
    destination.mkdir(parents=True)
    try:
        for name,source in sorted(mapping.items()):
            if source.is_symlink() or not source.is_file():raise ValueError('源文件缺失或为链接：'+str(source))
            target=destination/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        manifest={'name':NAME,'version':VERSION,'format':1,'files':{
            name:hashlib.sha256((destination/name).read_bytes()).hexdigest() for name in sorted(mapping)}}
        (destination/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        validate_bundle(destination)
    except BaseException:
        shutil.rmtree(destination)
        raise
    return manifest


def _unpack(archive,destination):
    if Path(archive).stat().st_size>MAX_BYTES:raise ValueError('压缩包超过大小限制')
    with zipfile.ZipFile(archive) as z:
        entries=z.infolist();seen=set();total=0
        if len(entries)>MAX_FILES+64:raise ValueError('压缩包文件数量超限')
        for entry in entries:
            name=entry.filename.rstrip('/')
            path=_relative(name)
            if path.parts[0]!=NAME or name in seen:raise ValueError('压缩包目录或重复路径无效')
            seen.add(name)
            mode=stat.S_IFMT(entry.external_attr>>16)
            if mode not in (0,stat.S_IFREG,stat.S_IFDIR):raise ValueError('压缩包包含链接或特殊文件')
            total+=entry.file_size
            if total>MAX_BYTES:raise ValueError('展开内容超过大小限制')
        for entry in entries:
            target=destination/entry.filename
            if entry.is_dir():target.mkdir(parents=True,exist_ok=True)
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                with z.open(entry) as source,target.open('wb') as output:shutil.copyfileobj(source,output)
    root=destination/NAME
    validate_bundle(root)
    return root


def _identity(path):
    try:
        value=Path(path).lstat()
        return value.st_dev,value.st_ino,stat.S_IFMT(value.st_mode)
    except FileNotFoundError:return None


def _rename_exclusive(source,target):
    """原子移动且绝不覆盖并发出现的目标。"""
    if os.name=='nt':
        os.rename(source,target)
        return
    import ctypes
    library=ctypes.CDLL(None,use_errno=True)
    if sys.platform.startswith('linux'):
        function=getattr(library,'renameat2',None)
        if function is None:raise OSError(errno.ENOTSUP,'平台没有原子不覆盖移动接口')
        function.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
        function.restype=ctypes.c_int
        result=function(-100,os.fsencode(source),-100,os.fsencode(target),1)
    elif sys.platform=='darwin':
        function=getattr(library,'renamex_np',None)
        if function is None:raise OSError(errno.ENOTSUP,'平台没有原子不覆盖移动接口')
        function.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_uint]
        function.restype=ctypes.c_int
        result=function(os.fsencode(source),os.fsencode(target),4)
    else:raise OSError(errno.ENOTSUP,'平台没有已适配的原子不覆盖移动接口')
    if result:
        code=ctypes.get_errno()
        raise OSError(code,os.strerror(code),str(target))


@contextmanager
def _installation_lock(target):
    key=hashlib.sha256(os.fsencode(target)).hexdigest()[:24]
    lock=target.parent/('.codesemantics-lock-'+key)
    try:lock.mkdir()
    except FileExistsError as error:
        raise FileExistsError('同目标安装正在进行或锁尚未核实清理：'+str(lock)) from error
    try:yield
    finally:lock.rmdir()


def _private_path(parent,prefix):
    path=Path(tempfile.mkdtemp(prefix=prefix,dir=parent));path.rmdir()
    return path


def _remove_owned(path,identity):
    if _identity(path)!=identity:return False
    retired=_private_path(path.parent,'.codesemantics-retired-')
    _rename_exclusive(path,retired)
    if _identity(retired)!=identity:
        try:_rename_exclusive(retired,path)
        except OSError:
            raise ValueError('并发对象保留于：'+str(retired))
        return False
    shutil.rmtree(retired)
    return True


def install_bundle(source,target,*,replace=False,prepare=None):
    source=Path(source);target=Path(os.path.abspath(target))
    with tempfile.TemporaryDirectory(prefix='codesemantics-input-') as temp:
        source_root=_unpack(source,Path(temp)) if source.is_file() else source
        manifest=validate_bundle(source_root,allow_environment=True)
        target.parent.mkdir(parents=True,exist_ok=True)
        with _installation_lock(target):
            original=_identity(target)
            if target.is_symlink():raise ValueError('安装目标不能为链接')
            if original is not None:
                if not replace:raise FileExistsError(str(target))
                validate_bundle(target,allow_environment=True)
                if _identity(target)!=original:raise ValueError('目标在校验期间发生变化')
            stage=Path(tempfile.mkdtemp(prefix='.codesemantics-stage-',dir=target.parent))
            stage_identity=_identity(stage)
            backup=None;published=False;retained=[]
            try:
                for name in [*manifest['files'],'manifest.json']:
                    path=stage/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source_root/name,path)
                validate_bundle(stage)
                if original is not None:
                    if _identity(target)!=original:raise ValueError('目标在准备期间发生变化')
                    validate_bundle(target,allow_environment=True)
                    backup=_private_path(target.parent,'.codesemantics-backup-')
                    _rename_exclusive(target,backup)
                    if _identity(backup)!=original:raise ValueError('目标在发布期间发生变化')
                    validate_bundle(backup,allow_environment=True)
                _rename_exclusive(stage,target);published=True
                if _identity(target)!=stage_identity:raise ValueError('目标在发布后发生变化')
                if prepare:prepare(target)
                if _identity(target)!=stage_identity:raise ValueError('目标在环境准备期间发生变化')
                validate_bundle(target,allow_environment=True)
            except BaseException as error:
                if published:
                    try:
                        if not _remove_owned(target,stage_identity):retained.append(str(target))
                    except (OSError,ValueError) as cleanup:retained.append(str(cleanup))
                if backup is not None and _identity(backup) is not None:
                    try:_rename_exclusive(backup,target)
                    except OSError:retained.append(str(backup))
                if retained:
                    raise ValueError('安装失败；未删除并发目标，需核实的保留路径：'+'；'.join(retained)) from error
                raise
            finally:
                if _identity(stage) is not None:
                    if not _remove_owned(stage,stage_identity):
                        raise ValueError('临时目录身份已变化，未删除：'+str(stage))
            if backup is not None:
                try:
                    if not _remove_owned(backup,original):retained.append(str(backup))
                except (OSError,ValueError):retained.append(str(backup))
    receipt={'installed':True,'name':NAME,'version':VERSION,'target':str(target),'runtimePrepared':prepare is not None}
    if retained:receipt['retainedPaths']=retained
    return receipt


def default_target(assistant,scope,user_home,project):
    user_home=Path(user_home);project=Path(project)
    if assistant=='codex':
        base=Path(os.environ.get('CODEX_HOME',str(user_home/'.agents'))) if scope=='user' else project/'.agents'
    elif assistant=='codearts':base=(user_home if scope=='user' else project)/'.codeartsdoer'
    else:raise ValueError('此助手未核实默认目录，请用--target指定完整Skill目标目录')
    return base/'skills'/NAME


def prepare_runtime(root,python=None):
    root=Path(root);environment=root/'.venv'
    candidates=[python] if python else [sys.executable,shutil.which('python3.12')]
    selected=None
    for candidate in candidates:
        if not candidate:continue
        try:
            check=subprocess.run([str(candidate),'-c',
                "import sys;raise SystemExit(0 if sys.version_info[:2]==(3,12) and sys.version_info.releaselevel=='final' else 1)"],
                capture_output=True,timeout=10)
            if check.returncode==0:selected=str(candidate);break
        except (OSError,subprocess.SubprocessError):continue
    if selected:
        subprocess.run([selected,'-m','venv',str(environment)],check=True,capture_output=True,timeout=120)
    elif python:raise ValueError('--python须指向可运行的正式版Python3.12')
    elif shutil.which('uv'):
        subprocess.run(['uv','venv','--python','3.12',str(environment)],check=True,capture_output=True,timeout=300)
        subprocess.run(['uv','pip','install','--python',str(environment/('Scripts/python.exe' if os.name=='nt' else 'bin/python')),
                        '-r',str(root/'requirements.txt')],check=True,capture_output=True,timeout=300)
        _check_installed(root,environment);return
    else:raise ValueError('未找到正式版Python3.12或uv；请先准备运行时，或用--python指定、--no-runtime仅部署文件')
    executable=environment/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    try:
        subprocess.run([str(executable),'-m','pip','install','-r',str(root/'requirements.txt')],check=True,capture_output=True,timeout=300)
        _check_installed(root,environment)
    except subprocess.SubprocessError as error:raise ValueError('依赖安装或自检未通过，请检查网络、包索引及Python环境') from error


def _check_installed(root,environment):
    executable=environment/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    subprocess.run([str(executable),str(root/'scripts/check.py')],check=True,capture_output=True,timeout=60)


def main_install():
    parser=argparse.ArgumentParser(description='安装codesemantics标准Skill；仅写目标目录')
    parser.add_argument('--assistant',choices=['codex','codearts','atomcode','qcode','generic'],default='codex')
    parser.add_argument('--scope',choices=['user','project'],default='user')
    parser.add_argument('--project-dir',type=Path,default=Path.cwd())
    parser.add_argument('--target',type=Path,help='完整目标目录，末级通常为codesemantics')
    parser.add_argument('--archive',type=Path,help='本地codesemantics.zip')
    parser.add_argument('--python',help='正式版Python3.12可执行文件')
    parser.add_argument('--no-runtime',action='store_true',help='只部署文件，不下载或准备依赖')
    parser.add_argument('--replace',action='store_true',help='显式替换经核验的本产品目录')
    args=parser.parse_args()
    try:
        target=args.target or default_target(args.assistant,args.scope,Path.home(),args.project_dir)
        prepare=None if args.no_runtime else lambda path:prepare_runtime(path,args.python)
        if args.archive:receipt=install_bundle(args.archive,target,replace=args.replace,prepare=prepare)
        else:
            base=Path(__file__).resolve().parents[1]
            if (base/'manifest.json').is_file():receipt=install_bundle(base,target,replace=args.replace,prepare=prepare)
            else:
                with tempfile.TemporaryDirectory(prefix='codesemantics-build-') as temp:
                    bundle=Path(temp)/NAME;build_bundle(base,bundle)
                    receipt=install_bundle(bundle,target,replace=args.replace,prepare=prepare)
        print(json.dumps(receipt,ensure_ascii=False));return 0
    except (OSError,ValueError,subprocess.SubprocessError,zipfile.BadZipFile) as error:
        print('安装失败：'+str(error),file=sys.stderr);return 1
