# Phase 3 Engineering Hardening

The backend uses centralized AppSettings configuration for storage paths, CORS origins, chunk parameters, default top_k, low relevance threshold, and DeepSeek settings.

Business document metadata is stored in SQLite through SQLAlchemy. The DocumentRecord model keeps filename, file type, storage path, chunk count, created_at, and lifecycle status.

Document lifecycle status values include uploaded, indexed, failed, and deleted. In the current synchronous upload flow, successful documents are stored as indexed. Delete operations mark SQLite records with deleted status, remove uploaded files when present, and remove matching Chroma vectors.

Normal document list and repository reads hide deleted status records so removed documents do not appear in the app or retrieval workflow.
