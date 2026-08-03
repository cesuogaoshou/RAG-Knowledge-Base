# RAG Knowledge Base Baseline

This project is a local RAG knowledge base built with FastAPI, React, ChromaDB, bge-m3 embeddings, and DeepSeek Chat.

The backend accepts PDF, TXT, and Markdown uploads. Uploaded documents are parsed into text pages, split into overlapping chunks, embedded, and stored in ChromaDB.

The chat endpoint retrieves the top matching chunks before calling DeepSeek. If retrieval returns no chunks or the best similarity score is below the configured threshold, the backend returns a Chinese insufficient-evidence answer without calling the LLM.

The frontend shows a practical two-pane workspace with document upload, document list, deletion, retrieval debug results, chat answers, and expandable source citations.
