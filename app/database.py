from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

DATABASE_URL = "postgresql+pg8000://postgres.qrrdwlgxcevqhxogqbjn:Facu222!@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"

# Motor síncrono para la conexión a la base de datos
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Definición de la base
Base = declarative_base()

# Dependencia para obtener una sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
