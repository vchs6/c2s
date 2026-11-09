"""SQLite档案的显式完整备份与一致性核验。"""
from pathlib import Path
from .sqlite_lifecycle import open_sqlite

def backup_entity_archive(store, destination: Path) -> dict:
    """使用SQLite在线备份及逐表回读，不覆盖既有文件。"""
    import os
    from pathlib import Path
    import sqlite3
    import hashlib
    if not store.path.is_file():raise ValueError("备份源档案必须已经存在")
    destination=Path(destination).resolve()
    if destination==store.path or destination.exists():raise ValueError('备份路径必须尚不存在且不同于原档案')
    destination.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(destination,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    try:
        with store._connect() as source, open_sqlite(destination) as target:
            source.execute('BEGIN')
            source.backup(target)
            if target.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('备份完整性检查失败')
            tables=[row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            for table in tables:
                name='"'+table.replace('"','""')+'"'
                left=source.execute('SELECT * FROM '+name).fetchall()
                right=target.execute('SELECT * FROM '+name).fetchall()
                if sorted(left,key=repr)!=sorted(right,key=repr):raise ValueError('备份逐表回读不一致')
        return {'status':'verified','path':str(destination),'tables':len(tables),
                'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()}
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
