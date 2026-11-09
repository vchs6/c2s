"""按文件白名单构建自包含codesemantics.zip。"""
import argparse
from pathlib import Path
import tempfile
import zipfile
from codesemantics_release import build_bundle

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(str(args.output))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='codesemantics-build-') as temp:
        root=Path(temp)/'codesemantics';manifest=build_bundle(Path(__file__).resolve().parents[1],root)
        with zipfile.ZipFile(args.output,'x',zipfile.ZIP_DEFLATED) as archive:
            for name in sorted([*manifest['files'],'manifest.json']):archive.write(root/name,'codesemantics/'+name)
    print(str(args.output.resolve()))
if __name__=='__main__':main()
