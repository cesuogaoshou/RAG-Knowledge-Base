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

Phase 3 engineering hardening is complete. Runtime configuration is centralized, document business metadata is stored in SQLite through SQLAlchemy, and documents carry an explicit lifecycle status. Phase 5 has added lightweight asynchronous document processing and optional streaming chat output without introducing a queue, microservice split, or a second vector database. Phase 6 has started with SQLite-backed chat session, message, and answer-source history.

## Architecture

```text
Browser UI (React + Vite)
  -> FastAPI REST/SSE API
  -> SQLite document metadata and chat history
  -> File storage for uploaded documents
  -> bge-m3 embeddings
  -> ChromaDB vector store
  -> DeepSeek Chat for grounded answers
```

The backend keeps business document state, chat history, and saved answer citations in SQLite while vector chunks stay in ChromaDB. Uploads are accepted quickly, then parsed and indexed in a FastAPI background task. Chat first retrieves relevant chunks, applies a low-relevance refusal guard, and then calls DeepSeek only when the local knowledge base has enough evidence.

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

The upload response includes the generated document id, original filename, saved path, document type, and lifecycle status. Uploads are accepted first as `uploaded`; the backend then parses, chunks, embeds, and indexes the saved file in a local FastAPI background task.

List uploaded documents:

```text
GET http://127.0.0.1:8000/api/documents
```

The document list response includes document id, filename, type, created time, chunk count, and lifecycle status. Background processing marks completed documents as `indexed`; processing failures are visible as `failed`; deleted documents are hidden from the normal list while their SQLite record is marked `deleted`.

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
Each JSON chat request also creates a local chat session and stores the user question, assistant answer, and displayed answer citations in SQLite.

Stream a question response with Server-Sent Events:

```text
POST http://127.0.0.1:8000/api/chat/stream
Content-Type: application/json

{
  "question": "How does RAG work?",
  "top_k": 5
}
```

The streaming endpoint uses the same retrieval and low-relevance guard as `/api/chat`. It emits `token` events as answer text arrives, then a `sources` event with the final deduplicated citations, followed by a `done` event. The React frontend prefers this streaming endpoint for a more responsive demo and falls back to `/api/chat` if streaming is unavailable.
Streaming chat also stores the completed turn and displayed citations after the answer finishes, then emits a `session` event with the persisted chat session id.

In the frontend, each answer citation shows a readable preview by default. Expand a citation to inspect the exact chunk index, page, score, and full source text returned by the backend.

List saved chat sessions:

```text
GET http://127.0.0.1:8000/api/chat/sessions
```

Read one saved chat session, including messages and persisted answer citations:

```text
GET http://127.0.0.1:8000/api/chat/sessions/{session_id}
```

Delete one saved chat session:

```text
DELETE http://127.0.0.1:8000/api/chat/sessions/{session_id}
```

## RAG Evaluation

Run the offline retrieval baseline:

```powershell
cd backend
.\.venv\Scripts\python.exe -m evaluation.evaluate_retrieval
```

The report includes:

- `source_hit_rate`: whether the expected source file appeared in retrieved results.
- `marker_hit_rate`: whether the expected evidence text appeared in retrieved chunks.
- `refusal_accuracy`: whether unrelated questions are correctly treated as insufficient evidence.

Run a small retrieval parameter sweep:

```powershell
cd backend
.\.venv\Scripts\python.exe -m evaluation.evaluate_retrieval --chunk-sizes 400,800,1200 --chunk-overlaps 0,80,120 --top-ks 3,5 --min-relevance-scores 0.45,0.5,0.55
```

The sweep ranks configurations by source hit rate, marker hit rate, refusal accuracy, then smaller `top_k` and `chunk_size` for a leaner context.

The current expanded fixture has 15 cases covering upload chunking, low-evidence refusal, Docker demo notes, Phase 3 configuration/SQLite lifecycle behavior, frontend retrieval evidence, citation expansion, roadmap boundaries, an English lifecycle question, and unrelated-question refusal.

On this expanded fixture, the best measured configuration is `chunk_size=400`, `chunk_overlap=0`, `top_k=3`, and `min_relevance_score=0.45`, with source hit rate, marker hit rate, and refusal accuracy all at `1.0`. These values are now the backend defaults and can still be overridden with `RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP`, `RAG_DEFAULT_TOP_K`, and `RAG_MIN_RELEVANCE_SCORE`.

Run a retrieval-only versus reranked comparison:

```powershell
cd backend
.\.venv\Scripts\python.exe -m evaluation.evaluate_retrieval --compare-reranker --top-k 3 --initial-top-k 5
```

The current comparison uses a lightweight keyword-overlap reranker only inside the offline evaluation script. On the 15-case fixture it produced no metric lift over the tuned retrieval-only baseline, so the production chat path keeps the simpler retrieval-only flow.

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

## Docker Compose Demo

Create the backend environment file and set your DeepSeek key:

```powershell
Copy-Item backend\.env.example backend\.env
```

Edit `backend\.env` and replace `DEEPSEEK_API_KEY` with your real key. The Compose setup overrides the runtime storage paths so SQLite, uploaded files, ChromaDB data, and local model cache live in the `rag_backend_data` Docker volume.

Make sure Docker Desktop is running before building or starting the Compose services.

Build the containers:

```powershell
docker compose build
```

Start the local Docker demo:

```powershell
docker compose up
```

Open the app:

```text
Frontend: http://127.0.0.1:5173/
Backend health: http://127.0.0.1:8000/health
```

Stop the containers:

```powershell
docker compose down
```

The first real embedding request can still be slow because `bge-m3` may need to download and load inside the backend container. The model cache is stored in the Docker volume after the first successful load.

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

## Demo Script

1. Start the backend and frontend.
2. Upload a small PDF, TXT, or Markdown document.
3. Watch the document status move from `uploaded` to `indexed`.
4. Ask a document-specific question in the chat panel.
5. Point out that the answer streams in progressively.
6. Expand a citation to show the exact chunk, page, score, and source text.
7. Ask an unrelated question and show the deterministic refusal: `根据当前知识库资料无法确定。`
8. Open the retrieval debug panel to show which chunks were retrieved before generation.

## Engineering Highlights

- Backend-first RAG loop with upload, parsing, chunking, embedding, retrieval, answer generation, and citations.
- SQLite stores business document metadata while ChromaDB stores vector chunks.
- Explicit lifecycle states make document processing observable: `uploaded`, `indexed`, `failed`, and `deleted`.
- Deletion keeps metadata, uploaded files, and vector chunks consistent.
- Retrieval quality is measured with a repeatable offline fixture and parameter sweep.
- Low-relevance refusal prevents weakly grounded LLM calls.
- Server-Sent Events stream answer tokens for a more responsive local demo.
- SQLite-backed chat sessions persist local question/answer history and displayed answer citations across backend restarts.
- Frontend tests cover upload/list behavior, deletion, retrieval debug, chat, streaming fallback, citations, and layout constraints.

## Key Tradeoffs

- ChromaDB remains the vector store because the current project has a narrow local retrieval surface and the evaluation fixture already reaches 1.0 on source hit, marker hit, and refusal accuracy.
- The production chat path stays retrieval-only because the evaluation-only reranker produced no metric lift on the current fixture.
- Document processing uses FastAPI `BackgroundTasks` instead of Celery or Redis to keep the first production-style version simple and runnable locally.
- Docker source files are present, but Docker runtime build/up verification is skipped until the local Docker Hub or registry mirror path is reliable.

## Resume Bullets

- Built a local RAG knowledge-base app with FastAPI, React, ChromaDB, SQLite, DeepSeek Chat, and `bge-m3` embeddings.
- Implemented document upload, asynchronous indexing, semantic retrieval, low-confidence refusal, streaming chat output, persisted chat history, and expandable source citations.
- Added repeatable RAG evaluation with fixture-based source-hit, marker-hit, and refusal-accuracy metrics, then tuned retrieval defaults from measured results.
- Hardened document lifecycle consistency across SQLite metadata, uploaded files, and vector-store chunks, including deletion and failed-processing states.
