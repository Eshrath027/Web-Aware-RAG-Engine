from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
import os
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="URL → FAISS Ingestion API")

# Initialize embeddings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

# In-memory FAISS index (you can persist this to disk)
faiss_index = None


class IngestRequest(BaseModel):
    url: str


@app.post("/ingest-url")
async def ingest_url(request: IngestRequest):
    """
    Fetches the web page content, splits it, embeds, and stores in FAISS.
    """
    global faiss_index
    try:
        loader = WebBaseLoader(request.url)
        docs = loader.load()

        if not docs:
            raise HTTPException(status_code=400, detail="No content found at the given URL.")

        # Split into smaller chunks
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(docs)

        # Create or update FAISS index
        if faiss_index is None:
            faiss_index = FAISS.from_documents(chunks, embeddings)
        else:
            faiss_index.add_documents(chunks)

        # Save index
        faiss_index.save_local("faiss_index")

        

        return {"status": "success", "message": f"Ingested {len(chunks)} chunks from {request.url}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class QueryRequest(BaseModel):
    query: str
    top_k: int = 3

@app.post("/query")
async def query_faiss(request: QueryRequest):
    """
    Searches the FAISS index for relevant content.
    """
    global faiss_index
    if faiss_index is None:
        raise HTTPException(status_code=400, detail="Vector index is empty. Ingest a URL first.")
    
    # Load index later
    faiss_index = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)


    results = faiss_index.similarity_search(request.query, k=request.top_k)
    
    return {
        "query": request.query,
        "results": [{"content": r.page_content, "metadata": r.metadata} for r in results],
    }


