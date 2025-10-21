from sqlalchemy import Column, String, Integer, DateTime, Text, Enum, ForeignKey, create_engine, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import enum

Base = declarative_base()


class IngestionStatus(enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"



class IngestionRecord(Base):
    __tablename__ = "ingestions"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False, unique=True)
    status = Column(Enum(IngestionStatus), default=IngestionStatus.pending)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    chunk_count = Column(Integer, nullable=True)


class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=True)
    results_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
