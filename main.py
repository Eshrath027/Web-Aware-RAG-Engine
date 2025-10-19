from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from worker import ingest_url_task
import os
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="Async RAG Ingestion API")
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "./faiss_index")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class IngestRequest(BaseModel):
    url: str

@app.post("/ingest-url")
async def ingest_url(request: IngestRequest):
    """
    Queues ingestion job for the given URL.
    """
    try:
        task = ingest_url_task.delay(request.url)
        return {"status": "accepted", "task_id": task.id, "message": "Ingestion started."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class QueryRequest(BaseModel):
    query: str
    top_k: int = 3

@app.post("/query")
async def query(request: QueryRequest):
    """
    Searches FAISS vector DB.
    """
    try:
        embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
        faiss_index = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
        results = faiss_index.similarity_search(request.query, k=request.top_k)
        return {
            "query": request.query,
            "results": [{"content": r.page_content, "metadata": r.metadata} for r in results],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
