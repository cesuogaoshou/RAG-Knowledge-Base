# RAG Knowledge Base

A backend-first RAG document question-answering project.

## Goal

Build a local document knowledge base that can upload documents, split text into chunks, store embeddings, retrieve relevant context, and generate answers with source citations.

## Planned Stack

- Backend: FastAPI
- Vector database: ChromaDB
- PDF parsing: PyMuPDF
- LLM: DeepSeek Chat
- Embedding: bge-m3
- Frontend: React + Vite + TypeScript

## First Milestone

The first milestone focuses on the backend RAG loop:

1. Upload PDF/TXT/Markdown documents.
2. Extract text.
3. Split text into chunks.
4. Generate embeddings.
5. Store vectors and metadata in ChromaDB.
6. Retrieve Top-K chunks for a user question.
7. Generate an answer with DeepSeek Chat.
8. Return source citations.

## Repository Status

Phase 1 backend closed loop is complete. The backend currently exposes health check, document upload, document list, search, and chat endpoints. Uploaded text is split into chunks, embedded, stored in a local ChromaDB collection, retrievable through semantic search, and usable as context for LLM answers. Document business metadata is stored in local SQLite through SQLAlchemy.

Phase 2 frontend demo flow is complete. The React app can connect to the local backend, show backend health, list uploaded documents, upload and delete PDF/TXT/Markdown files, inspect retrieval details, submit RAG questions, and render expandable answer citations.

Phase 3 engineering hardening is in progress. Runtime configuration is centralized, document business metadata is stored in SQLite through SQLAlchemy, and documents now carry an explicit lifecycle status.

## Backend Development

Create and activate the backend virtual environment:

```powershell
py -3.12 -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements-dev.txt
```

Configure DeepSeek credentials:

```powershell
Copy-Item backend\.env.example backend\.env
```

Then set `DEEPSEEK_API_KEY` in `backend\.env` or in your shell environment before calling `/api/chat`.

Backend runtime configuration is centralized in `backend/app/core/config.py`.
The `.env` file can override the SQLite database URL, storage paths, CORS origins, chunking parameters, the low-relevance threshold, and DeepSeek model settings.

Run tests:

```powershell
backend\.venv\Scripts\python.exe -m pytest -q
```

Run the API locally:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health check:

```text
GET http://127.0.0.1:8000/health
```

Upload a document:

```text
POST http://127.0.0.1:8000/api/documents/upload
Content-Type: multipart/form-data
file: PDF/TXT/MD
```

The upload response includes the generated document id, original filename, saved path, document type, lifecycle status, page count, chunk count, text length, and parsed page text.

List uploaded documents:

```text
GET http://127.0.0.1:8000/api/documents
```

The document list response includes document id, filename, type, created time, chunk count, and lifecycle status. The current synchronous upload flow marks successfully parsed and indexed documents as `indexed`; deleted documents are hidden from the normal list while their SQLite record is marked `deleted`.

Search document chunks:

```text
POST http://127.0.0.1:8000/api/search
Content-Type: application/json

{
  "question": "How does RAG work?",
  "top_k": 5
}
```

The search response includes the query, requested Top-K value, and matching chunks with filename, page number, chunk index, content, and score.

Similarity score direction:

- Current score is calculated as `1 / (1 + chroma_distance)`.
- Larger scores mean more similar chunks.
- `/api/chat` currently refuses to answer when no chunks are retrieved or the best retrieved score is below `0.5`.
- When this guard is triggered, the backend returns `根据当前知识库资料无法确定。` without calling DeepSeek.

Ask a question with retrieved context:

```text
POST http://127.0.0.1:8000/api/chat
Content-Type: application/json

{
  "question": "How does RAG work?",
  "top_k": 5
}
```

The chat response includes an LLM-generated answer and the retrieved sources used as context.
If the retrieved evidence is weak, the backend returns `根据当前知识库资料无法确定。` without calling the LLM.

In the frontend, each answer citation shows a readable preview by default. Expand a citation to inspect the exact chunk index, page, score, and full source text returned by the backend.

## Frontend Development

Install frontend dependencies:

```powershell
cd frontend
npm.cmd install
```

From the repository root, copy the frontend environment example if you need to override the API URL:

```powershell
Copy-Item frontend\.env.example frontend\.env
```

By default, the frontend expects the backend at:

```text
http://127.0.0.1:8000
```

Run the frontend locally:

```powershell
cd frontend
npm.cmd run dev -- --host 127.0.0.1
```

Open the app:

```text
http://127.0.0.1:5173/
```

Run frontend checks:

```powershell
cd frontend
npm.cmd run test
npm.cmd run build
npm.cmd run lint
```

## Local Demo Flow

Start the backend first, then start the frontend in a second terminal.

Confirm both services are reachable:

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing
Invoke-WebRequest -Uri "http://127.0.0.1:5173/" -UseBasicParsing
```

For a quick backend upload smoke test, use `curl.exe`:

```powershell
curl.exe -s -X POST -F "file=@D:\path\to\notes.txt;type=text/plain" "http://127.0.0.1:8000/api/documents/upload"
```

Then refresh the frontend, confirm the document appears in the document list, ask a question, and check that the answer includes source citations.
