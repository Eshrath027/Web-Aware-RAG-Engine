import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./rag_metadata.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def init_db():
    Base.metadata.create_all(bind=engine)
