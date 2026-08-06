# Phase 7 Advanced RAG Exploration

Phase 7 is for advanced RAG exploration after the core local demo is stable and measurable. Advanced RAG is evaluated before implementation so the project can explain why a feature exists.

The current vector store should keep ChromaDB until Phase 7 evidence shows a clear reason to migrate. Qdrant remains deferred because the local demo does not yet need a second vector database.

The primary embedding direction remains bge-m3. A smaller Chinese embedding model is only a fallback when bge-m3 setup is too slow or unstable.

Hybrid search should be considered when exact project terms or keyword-heavy questions are missed by vector retrieval. A hybrid feature should prove better retrieval metrics before it is added to production chat.

Query rewrite should be considered only after ambiguous question failures are measured. Short questions, vague follow-up wording, and missing nouns should first become evaluation cases.

Multi-turn conversational RAG should stay minimal if it becomes useful. The practical version is history-aware retrieval that rewrites a follow-up into a standalone retrieval question using saved local chat history.

Safe reset refuses document deletion. Local reset can clear chat and evaluation history, but document removal stays on the explicit document delete path.
