# Mini RAG Q&A — FastAPI + FAISS + OpenAI

A small, fast RAG (Retrieval-Augmented Generation) backend built with **FastAPI**, **FAISS**, and **OpenAI**.  
It ingests local documents, streams answers over **SSE**, **cites sources**, and **enforces a per-request budget**.

---

## Features

- Ingest text/markdown/PDF (≤ ~2 MB total), split into chunks with overlap, **deduped**, and indexed in **FAISS**
- **Hybrid retrieval**: vector similarity + lightweight lexical scoring
- **POST `/ask`** streams tokens (SSE), returns final **answer + citations + usage/cost**
- **Budget guardrails**: estimate cost from tokens; stop early if the budget is exceeded
- Handles **429** with exponential backoff + jitter; timeout handling
- **X-API-Key** auth (from `.env`), in-memory **rate limit** (RPM)
- Structured **JSON logs** with request id, tokens, cost, latency
- Dockerfile + Make targets, **pytest** tests, and **eval** scripts

---

## Getting Started

### 1) Local dev

```bash
git clone https://github.com/mufazzalshokh/mini_rag.git
cd mini_rag

python -m venv .venv
# mac/linux
source .venv/bin/activate
# windows
# .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env (minimum):
# OPENAI_API_KEY=sk-...
# API_KEY=your-secret-key
# (optional) MODEL, TOP_K, CHUNK_SIZE, RATE_LIMIT_RPM, etc.

# run the API
uvicorn app.main:app --reload
