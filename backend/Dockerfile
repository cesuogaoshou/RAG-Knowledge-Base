FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV RAG_UPLOAD_DIR=/app/data/uploads
ENV RAG_VECTOR_STORE_DIR=/app/data/chroma_db
ENV RAG_DATABASE_URL=sqlite:////app/data/app.db
ENV RAG_CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
ENV HF_HOME=/app/data/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/app/data/sentence_transformers

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
