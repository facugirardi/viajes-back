import os
import pg8000.native as pg
from flask import g
from pg8000.native import Connection


def get_db():
    if 'db' not in g:
        g.db = Connection(
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            host=os.environ["DB_HOST"],
            port=int(os.environ.get("DB_PORT", 6543)),
            database=os.environ.get("DB_NAME", "postgres")
        )
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()
