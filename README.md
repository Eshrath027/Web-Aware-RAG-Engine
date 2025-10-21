A **Retrieval-Augmented Generation (RAG)** system that asynchronously ingests web content, stores embeddings in FAISS, and allows users to query the knowledge base for grounded answers.

---

##  Architecture

```text
                 +--------------------+
                 |      User/API      |
                 +--------------------+
                           |
                           v
                +----------------------+
                |  FastAPI Application |
                +----------------------+
                | /ingest-url          |
                | /query               |
                +----------------------+
                           |
         -------------------------------------------------
         |                    |                        |
         v                    v                        v
 +----------------+   +----------------+     +--------------------+
 |  Redis Queue   |   |  FAISS Index   |     |  SQLite Metadata   |
 | (Celery Tasks) |   | (Vector Store) |     |  (Ingest + Query)  |
 +----------------+   +----------------+     +--------------------+
         |
         v
 +----------------+
 | Celery Worker  |
 | Fetch, Chunk,  |
 | Embed, Store   |
 +----------------+
```

### **System Flow**

1. User submits a URL to `/ingest-url` → added to **Redis queue**.
2. **Celery Worker** fetches and processes the content → splits → embeds → stores in **FAISS Index**.
3. **SQLite DB** records ingestion status and metadata.
4. For `/query`, the user input is embedded → similar results fetched from FAISS → grounded response returned and logged in **SQLite**.

---

## Design Choices

| Component              | Reason                                                                       |
| ---------------------- | ---------------------------------------------------------------------------- |
| **FastAPI**            | High-performance, async-friendly API for scalable ingestion and querying.    |
| **Celery + Redis**     | Enables background task processing for non-blocking ingestion.               |
| **FAISS**              | Efficient vector similarity search for high-dimensional embeddings.          |
| **SQLite Metadata DB** | Lightweight relational store for ingestion logs and query tracking.          |
| **LangChain**          | Simplifies integration between FAISS, embeddings, and text processing.       |
| **OpenAI Embeddings**  | Converts text chunks into dense semantic vectors (`text-embedding-3-large`). |

---

## Database Schema

### **1. Ingestion Metadata Table (`ingestions`)**

Tracks every ingestion job.

| Field       | Type         | Description                        |
| ----------- | ------------ | ---------------------------------- |
| id          | INTEGER (PK) | Auto ID                            |
| url         | TEXT         | Ingested URL                       |
| status      | TEXT         | `pending` / `completed` / `failed` |
| chunk_count | INTEGER      | Number of text chunks generated    |
| created_at  | TIMESTAMP    | Time of ingestion request          |
| updated_at  | TIMESTAMP    | Last updated timestamp             |

### **2. Query Log Table (`query_logs`)**

Stores all user queries and responses.

| Field         | Type         | Description                       |
| ------------- | ------------ | --------------------------------- |
| id            | INTEGER (PK) | Auto ID                           |
| query_text    | TEXT         | Original query                    |
| response_text | TEXT         | Final generated answer            |
| top_sources   | JSON         | Retrieved text chunks or metadata |
| created_at    | TIMESTAMP    | Query timestamp                   |

---

## Technology Stack

| Layer            | Technology                                   | Reason                                      |
| ---------------- | -------------------------------------------- | ------------------------------------------- |
| Web Framework    | **FastAPI**                                  | Modern async API for ingestion & query      |
| Background Jobs  | **Celery**                                   | Handles async content ingestion             |
| Message Queue    | **Redis**                                    | Broker between FastAPI and Celery           |
| Vector Store     | **FAISS**                                    | Fast nearest-neighbor search                |
| Metadata Store   | **SQLite / PostgreSQL**                      | Tracks ingestion & query history            |
| Embeddings Model | **OpenAI (`text-embedding-3-large`)**        | Generates semantic vector representations   |
| Libraries        | **LangChain, requests, SQLAlchemy, uvicorn** | Simplify embedding, API, and database logic |

---

## API Documentation

### **1. `POST /ingest-url`**

**Description:**
Submit a URL for ingestion.

**Request Body:**

```json
{
  "url": "https://example.com/article"
}
```

**Response (202 Accepted):**

```json
{
  "status": "accepted",
  "task_id": "celery-task-id",
  "message": "Ingestion queued for https://example.com/article"
}
```

 **Example:**

```bash
curl -X POST http://127.0.0.1:8000/ingest-url \
     -H "Content-Type: application/json" \
     -d '{"url":"https://example.com/article"}'
```

---

### **2. `POST /query`**

**Description:**
Query the ingested knowledge base.

**Request Body:**

```json
{
  "query": "Explain transformers",
  "top_k": 5
}
```

**Response:**

```json
{
  "query": "Explain transformers",
  "response": "Transformers are deep learning models...",
  "results": [
    {"content": "Chunk 1 text...", "metadata": {...}},
    {"content": "Chunk 2 text...", "metadata": {...}}
  ]
}
```

 **Example:**

```bash
curl -X POST http://127.0.0.1:8000/query \
     -H "Content-Type: application/json" \
     -d '{"query":"Explain OCI IAM policies", "top_k":5}'
```

---

## Setup Instructions

### **1. Clone the Repository**

```bash
git clone https://github.com/Eshrath027/rag-engine.git
cd rag-engine
```

### **2. Create Virtual Environment**

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### **3. Install Dependencies**

```bash
pip install -r requirements.txt
```

### **4. Setup Environment Variables**

Create `.env` or copy from `.env.example`:

```env
OPENAI_API_KEY=your_openai_api_key
FAISS_INDEX_PATH=./faiss_index
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=sqlite:///rag_metadata.db
```

### **5. Run Services**

```bash
# Start Redis
redis-server

# Start Celery Worker
celery -A worker.app worker --loglevel=info
or 
celery -A divy worker --concurrency=1 --loglevel=INFO -Q celery

# Start FastAPI Server
uvicorn main:app --reload
```

---

## Docker Setup (Optional)

```bash
docker-compose up --build
```

This runs:

* FastAPI app on port `8000`
* Redis for Celery queue
* Celery worker
* SQLite volume (for metadata)

---
