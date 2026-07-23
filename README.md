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

Phase 1.2 document upload and parsing is complete. The backend currently exposes a health check endpoint and a document upload endpoint for PDF, TXT, and Markdown files.

## Backend Development

Create and activate the backend virtual environment:

```powershell
py -3.12 -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements-dev.txt
```

Run tests:

```powershell
backend\.venv\Scripts\python.exe -m pytest -q
```

Run the API locally:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
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

The upload response includes the generated document id, original filename, saved path, document type, page count, text length, and parsed page text.
