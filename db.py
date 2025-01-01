import pg8000.native as pg
from flask import g
from pg8000.native import Connection

# Configura la conexión a tu base de datos
DATABASE_CONFIG = {
    "database": "postgres",
    "user": "postgres.qrrdwlgxcevqhxogqbjn",
    "password": "Facu222!",
    "host": "aws-0-sa-east-1.pooler.supabase.com",
    "port": 6543
}

def get_db():
    if 'db' not in g:
        g.db = Connection(
            user="postgres.qrrdwlgxcevqhxogqbjn",
            password="Facu222!",
            host="aws-0-sa-east-1.pooler.supabase.com",
            port=6543,
            database="postgres"
        )
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()
        
# Método para ejecutar consultas
def run_query(query, params=None):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(query, params)
    db.commit()
    return cursor.fetchall()
