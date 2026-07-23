from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(
        title="RAG Knowledge Base API",
        version="0.1.0",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "rag-knowledge-base-api",
        }

    return app


app = create_app()
