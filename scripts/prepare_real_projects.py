"""重建公开固定项目夹具；不覆盖已有检出或忽略本地修改。"""
from pathlib import Path
import argparse
import json
import subprocess

ROOT=Path(__file__).resolve().parents[1]
CASES=json.loads((ROOT/'skill/tests/fixtures/algorithm-source-checklists.json').read_text())
PROJECTS={'click':('https://github.com/pallets/click.git',CASES['P7']['commit']),
          'regex':('https://github.com/rust-lang/regex.git',CASES['R5']['commit']),
          'nlohmann-json':('https://github.com/nlohmann/json.git',CASES['C5']['commit'])}

def _git(path,*args):
    return subprocess.check_output(['git','-C',str(path),*args],text=True,timeout=180).strip()

def prepare_project(url,commit,destination):
    destination=Path(destination)
    if destination.exists():
        if not (destination/'.git').exists():raise ValueError('目标已存在且不是Git检出：'+str(destination))
        if _git(destination,'rev-parse','HEAD')!=commit:raise ValueError('已有夹具提交不符，不自动覆盖：'+str(destination))
        if _git(destination,'status','--porcelain'):raise ValueError('夹具有本地修改，不自动覆盖：'+str(destination))
    else:
        destination.mkdir(parents=True)
        _git(destination,'init','-q')
        _git(destination,'fetch','--quiet','--depth=1',url,commit)
        _git(destination,'checkout','--quiet','--detach','FETCH_HEAD')
        if _git(destination,'rev-parse','HEAD')!=commit:raise ValueError('取回的夹具提交与固定版本不同')
    return {'path':str(destination.resolve()),'commit':commit,'verified':True}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',type=Path,default=ROOT/'.local/real-projects')
    args=parser.parse_args(argv)
    results={name:prepare_project(url,commit,args.destination/name) for name,(url,commit) in PROJECTS.items()}
    print(json.dumps(results,ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())
