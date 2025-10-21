import os
from celery import Celery
from utils import ingest_url_to_faiss
from database import SessionLocal
from models import IngestionRecord, IngestionStatus

from dotenv import load_dotenv
load_dotenv()

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
app = Celery("tasks", broker=redis_url)

@app.task
def ingest_url_task(url: str):
    db = SessionLocal()
    record = db.query(IngestionRecord).filter_by(url=url).first()
    try:
        if record:
            record.status = IngestionStatus.processing
            db.commit()

        openai_key = os.getenv("OPENAI_API_KEY")
        index_path = os.getenv("FAISS_INDEX_PATH", "./faiss_index")
        chunk_count = ingest_url_to_faiss(url, index_path, openai_key)

        if record:
            record.status = IngestionStatus.completed
            record.chunk_count = chunk_count
            db.commit()

        return f" Ingested {chunk_count} chunks from {url}"

    except Exception as e:
        if record:
            record.status = IngestionStatus.failed
            record.error_message = str(e)
            db.commit()
        raise
    finally:
        db.close()
