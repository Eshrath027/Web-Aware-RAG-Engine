import os
from celery import Celery
from utils import ingest_url_to_faiss
from dotenv import load_dotenv
load_dotenv()

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
app = Celery("tasks", broker=redis_url)

@app.task
def ingest_url_task(url: str):
    openai_key = os.getenv("OPENAI_API_KEY")
    index_path = os.getenv("FAISS_INDEX_PATH", "./faiss_index")
    chunk_count = ingest_url_to_faiss(url, index_path, openai_key)
    return f"Ingested {chunk_count} chunks from {url}"
