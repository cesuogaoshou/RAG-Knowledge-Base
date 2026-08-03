# Roadmap Boundaries

Phase 4 focuses on measurable RAG quality. Evaluation and retrieval parameter tuning must come before reranker work so changes can be measured instead of guessed.

Reranker integration is deferred until baseline retrieval metrics and tuned retrieval numbers exist. Hybrid search is also deferred until after simpler retrieval quality work has evidence.

ChromaDB remains the vector store during Phase 3 and Phase 4. Qdrant migration belongs to a later production-style enhancement phase, after SQLite, configuration, lifecycle status, Docker source configuration, and RAG evaluation are already in place.

Docker runtime troubleshooting is paused unless explicitly requested because Docker Hub authentication, registry DNS, and mirror-backed builds timed out on this machine.

The project should stay practical and resume-oriented. It should not add auth, permissions, microservice split, agent tools, multimodal input, or enterprise administration in the first version.
