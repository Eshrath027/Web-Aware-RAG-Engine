from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from worker import ingest_url_task
import os
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from database import init_db, SessionLocal
from models import IngestionRecord, IngestionStatus, QueryLog

from dotenv import load_dotenv
load_dotenv()

init_db()


app = FastAPI(title="Async RAG Ingestion API")
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "./faiss_index")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class IngestRequest(BaseModel):
    url: str
    
@app.post("/ingest-url")
async def ingest_url(request: IngestRequest):
    db = SessionLocal()
    try:
        record = IngestionRecord(url=request.url, status=IngestionStatus.pending)
        db.add(record)
        db.commit()
        db.refresh(record)

        task = ingest_url_task.delay(request.url)

        return {
            "status": "accepted",
            "task_id": task.id,
            "record_id": record.id,
            "message": f"Ingestion queued for {request.url}",
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


class QueryRequest(BaseModel):
    query: str
    top_k: int = 3

@app.post("/query")
async def query(request: QueryRequest):
    db = SessionLocal()
    try:
        embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
        faiss_index = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
        results = faiss_index.similarity_search(request.query, k=request.top_k)

        # Combine into one response text (simulate LLM answer)
        response_text = "\n".join([r.page_content for r in results])

        # Store in database
        query_log = QueryLog(
            query_text=request.query,
            response_text=response_text,
            results_metadata=[r.metadata for r in results],
        )
        db.add(query_log)
        db.commit()

        return {
            "query": request.query,
            "response": response_text,
            "results": [{"content": r.page_content, "metadata": r.metadata} for r in results],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

