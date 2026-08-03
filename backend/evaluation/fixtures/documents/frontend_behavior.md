# Frontend RAG Workspace Behavior

The React frontend is a practical two-pane RAG workspace, not a landing page. It shows backend health, document upload, document list, document deletion, chat, and source evidence.

The retrieval debug panel calls the search API before generation. It displays filename, page, chunk index, similarity score, and chunk text so a demo can explain which chunks were retrieved.

Chat answers render source citations below the response. Citation cards keep a short readable preview by default, and expandable source citations reveal chunk index, page, score, and full source text.

The layout uses fixed viewport panels with internal scrolling for the document list, chat transcript, and source list. The chat transcript auto-scrolls to new messages while still allowing users to scroll back to older turns.
