import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./deadly_truth.db"

# Railway pode fornecer postgres://, ajustar para SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    
    # Migração: adiciona coluna nickname se não existir
    try:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'nickname' not in columns:
            print("🔄 Adicionando coluna 'nickname' à tabela 'users'...")
            with engine.connect() as conn:
                if DATABASE_URL.startswith('sqlite'):
                    conn.execute(text("ALTER TABLE users ADD COLUMN nickname VARCHAR(50)"))
                else:
                    # PostgreSQL
                    conn.execute(text("ALTER TABLE users ADD COLUMN nickname VARCHAR(50)"))
                conn.commit()
            print("✅ Coluna 'nickname' adicionada com sucesso!")
    except Exception as e:
        print(f"⚠️ Erro ao verificar/adicionar coluna nickname: {e}")
        # Não falha se a migração não funcionar