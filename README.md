A **Retrieval-Augmented Generation (RAG)** system that asynchronously ingests web content, stores embeddings in FAISS, and allows users to query the knowledge base for grounded answers. 

---

## Table of Contents

1. [Architecture](#architecture)
2. [Design Choices](#design-choices)
3. [Technology Stack](#technology-stack)
4. [API Endpoints](#api-endpoints)
5. [Setup Instructions](#setup-instructions)
6. [Demo](#api)

---

## Architecture

```text
                 +--------------------+
                 |      User/API       |
                 +--------------------+
                           |
                           v
                +----------------------+
                | FastAPI Application  |
                +----------------------+
                | /ingest-url          |
                | /query               |
                +----------------------+
                           |
                 ----------------------
                 |                    |
                 v                    v
         +----------------+   +----------------+
         |  Redis Queue   |   |  FAISS Index   |
         |  (Celery tasks)|   | stores embeddings |
         +----------------+   +----------------+
                 |
                 v
         +----------------+
         | Celery Worker  |
         | fetches URL,   |
         | splits text,   |
         | embeds, adds   |
         | to FAISS       |
         +----------------+
```

**Flow:**

1. User submits URL → FastAPI → Redis queue → Celery worker.
2. Worker fetches content, splits into chunks, creates embeddings, stores in FAISS.
3. Query endpoint: user query → embed → FAISS search → return top results.

> Note: In this version, ingestion metadata is **not persisted in a DB**; only logged to the console.

---

## Design Choices

| Component             | Reason                                                |
| --------------------- | ----------------------------------------------------- |
| **FastAPI**           | High-performance async API framework                  |
| **Celery + Redis**    | Async task queue; ensures ingestion is non-blocking   |
| **FAISS**             | Optimized for fast vector similarity search           |
| **LangChain**         | Simplifies FAISS integration with document embeddings |
| **OpenAI Embeddings** | Converts text chunks into vectors for semantic search |

---

## Technology Stack

| Layer            | Technology                                   |
| ---------------- | -------------------------------------------- |
| Web Framework    | FastAPI                                      |
| Background Jobs  | Celery                                       |
| Message Queue    | Redis                                        |
| Vector Store     | FAISS (via LangChain wrapper)                |
| Embeddings Model | OpenAI Embeddings (`text-embedding-3-large`) |
| Python Libraries | LangChain, requests, Celery, uvicorn         |

---

## API Endpoints

### 1. `POST /ingest-url`

**Description:** Submit a URL for ingestion.

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

---

### 2. `POST /query`

**Description:** Query the ingested content.

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
  "response": "transformers define ...",
  "results": [
    {"content": "Chunk text 1", "metadata": {...}},
    {"content": "Chunk text 2", "metadata": {...}}
  ]
}
```

---

## Setup Instructions

### 1. Clone the Repo

```bash
git clone https://github.com/Eshrath027/rag-engine.git
cd rag-engine
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv / virtualenv -p python3 .venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables (`.env`)

```env
OPENAI_API_KEY=your_openai_api_key
FAISS_INDEX_PATH=./faiss_index
REDIS_URL=redis://localhost:6379/0
```

### 5. Start Redis

```bash
redis-server
```

### 6. Start Celery Worker

```bash
celery -A worker.app worker --loglevel=info
```

### 7. Start FastAPI App

```bash
uvicorn main:app --reload
```

---

## API

* Ingest a URL:

```bash
curl -X POST http://127.0.0.1:8000/ingest-url -H "Content-Type: application/json" -d '{"url":"https://example.com/article"}'
```

* Query the content:

```bash
curl -X POST http://127.0.0.1:8000/query -H "Content-Type: application/json" -d '{"query":"Explain OCI IAM policies", "top_k":5}'
```


