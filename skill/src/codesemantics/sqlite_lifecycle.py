"""分离SQLite事务边界和连接生命周期，正常与异常退出均关闭。"""
from contextlib import contextmanager
import sqlite3

@contextmanager
def open_sqlite(*args,**kwargs):
    connection=sqlite3.connect(*args,**kwargs)
    try:
        with connection:
            yield connection
    finally:
        connection.close()
