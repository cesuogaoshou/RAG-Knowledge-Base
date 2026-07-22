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

Phase 0 repository setup is complete. Implementation starts with the FastAPI backend.
