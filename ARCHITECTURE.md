# Architecture

![CI](https://github.com/mufazzalshokh/mini_rag/actions/workflows/ci.yml/badge.svg)

## Overview

Mini RAG is a lightweight document Q&A backend. The design prioritises three things:

- **Low operational complexity** — single process, local FAISS index, no external vector DB required
- **Cost transparency** — every response includes prompt tokens, completion tokens, and exact USD cost
- **Production patterns at minimal scale** — auth, rate limiting, retry with backoff, structured logging, budget guardrails

---

## Request Lifecycle

```
Client
  │
  ├─ POST /ingest
  │     │
  │     ├── Auth (X-API-Key)
  │     ├── Save uploaded files → DOCS_PATH
  │     ├── Load all files from DOCS_PATH
  │     ├── Chunk (size=512, overlap=64) + deduplicate
  │     ├── Embed (sentence-transformers all-MiniLM-L6-v2)
  │     ├── Build FAISS IndexFlatIP (cosine similarity)
  │     └── Persist index.faiss + index.pkl
  │
  └─ POST /ask
        │
        ├── Auth (X-API-Key)
        ├── Rate limiter (in-memory sliding window, RPM)
        ├── Hybrid Retriever
        │     ├── FAISS dense search (top_k * 2 candidates)
        │     └── Lexical scorer (word overlap)
        │           └── Merge + deduplicate → top_k chunks
        ├── Budget pre-check (estimate prompt cost vs budget_usd)
        ├── OpenAI streaming (gpt-4o-mini, stream=True)
        │     ├── Retry loop (exponential backoff + jitter, max 3 attempts)
        │     ├── Per-token budget tracking (stop mid-stream if exceeded)
        │     └── Disconnect detection (client gone → stop streaming)
        └── SSE response
              ├── data: {"event": "token", "data": "..."}  (per token)
              └── data: {"event": "done", "data": {answer, citations, usage}}
```

---

## Module Structure

```
mini_rag/
├── app/
│   ├── main.py              # FastAPI app, router registration, /health
│   ├── api/
│   │   ├── ask.py           # POST /ask — SSE streaming, budget, retry
│   │   ├── ingest.py        # POST /ingest — file upload, chunking, indexing
│   │   └── auth.py          # X-API-Key dependency injection
│   └── core/
│       ├── config.py        # pydantic-settings, all env vars, lru_cache singleton
│       ├── retrieval.py     # Hybrid FAISS + lexical retriever
│       ├── chunk_manager.py # Document loading, chunking, embedding, FAISS build
│       ├── rate_limit.py    # In-memory sliding window rate limiter
│       └── logger.py        # Structured JSON request logging
├── tests/                   # pytest suite — all use TestClient, no live server
├── eval/                    # Evaluation scripts + golden JSONL
├── docs/                    # Sample documents for ingestion
├── .github/workflows/ci.yml # GitHub Actions CI
├── docker-compose.yml       # One-command full stack
└── Makefile                 # Developer shortcuts
```

---

## Key Design Decisions

### Why FAISS instead of pgvector / Chroma / Qdrant?

For a single-process backend ingesting under 5 MB of documents, a local FAISS index eliminates all infrastructure dependencies. There is no database to provision, no connection pool to manage, and no network latency on retrieval. The retriever is abstracted behind a single function (`hybrid_retrieve`) — swapping to pgvector is a one-file change if scale requires it.

### Why SSE instead of WebSockets?

SSE is unidirectional, stateless, and HTTP/1.1 compatible. It works transparently through proxies and load balancers without special configuration. For token streaming from an LLM, it is strictly simpler than WebSockets — no handshake, no ping/pong, no connection state. The tradeoff is that SSE cannot receive messages after the connection is open, which is not needed here.

### Why hybrid retrieval?

Pure vector search fails on exact-match queries — model numbers, proper nouns, codes, and acronyms. The lightweight lexical scorer adds recall for these cases with near-zero latency overhead. In production this would be replaced with BM25 + a cross-encoder re-ranker, but the current design makes that a drop-in swap.

### Why sentence-transformers (all-MiniLM-L6-v2)?

This model produces 384-dimensional embeddings, runs on CPU with no GPU required, downloads once and caches locally (~80 MB), and matches the FAISS index dimensionality with no configuration change. It is the standard choice for lightweight semantic search. The embedding call is lazy-loaded and cached via a module-level singleton to avoid reloading on every request.

### Budget guardrails — two-phase

Cost is checked twice. Before the OpenAI call, prompt tokens are estimated and the cost is compared against `budget_usd`. If the prompt alone exceeds the budget, the request is rejected immediately without making an API call. During streaming, tokens are counted as they arrive and streaming is cancelled mid-response if the running cost exceeds the budget. This prevents runaway costs from large contexts or unexpectedly long responses.

### Rate limiting — in-memory sliding window

A simple `{api_key: [timestamps]}` dictionary tracks request times per key. The window slides on every request, discarding timestamps older than 60 seconds. This is appropriate for a single-process deployment. A multi-process or multi-instance deployment would require Redis with an atomic increment pattern instead.

### Retry logic — exponential backoff with jitter

OpenAI 429 and timeout errors are retried up to 3 times. Wait time is `min(2^attempt, 8) + random()` seconds. The jitter prevents thundering herd when multiple clients hit a rate limit simultaneously. Non-retryable errors (auth failures, unexpected status codes) are surfaced immediately without retrying.

### Configuration — pydantic-settings

All configuration is declared as typed fields in a `Settings(BaseSettings)` class. Missing required values (e.g. `OPENAI_API_KEY`) cause a loud `ValidationError` at startup rather than a silent `None` being passed to the OpenAI client. An `lru_cache` singleton ensures the `.env` file is parsed once. `frozen=False` allows test-time patching via `monkeypatch`.

---

## What I Would Change at Production Scale

| Current | Production upgrade | Reason |
|---|---|---|
| Local FAISS index | pgvector or Qdrant | Persistence, multi-process access, filtered search |
| In-memory rate limiter | Redis token bucket | Works across multiple processes and instances |
| Single Uvicorn process | Gunicorn + multiple Uvicorn workers | CPU parallelism, graceful restarts |
| Sync embedding call | Async with `run_in_executor` | Unblocks event loop during CPU-bound embedding |
| Basic lexical scorer | BM25 + cross-encoder re-ranker | Significantly better retrieval quality |
| No auth expiry | JWT with short-lived tokens | API keys never expire and can't be revoked per-session |
| `print()` based logging | `structlog` or `python-logging` with log aggregator | Searchable, filterable logs in production |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | required | OpenAI API key |
| `API_KEY` | `changeme` | X-API-Key for endpoint auth |
| `MODEL_NAME` | `gpt-4o-mini` | OpenAI model to use |
| `CHUNK_SIZE` | `512` | Tokens per chunk |
| `CHUNK_OVERLAP` | `64` | Overlap between chunks |
| `TOP_K` | `5` | Number of chunks to retrieve |
| `RATE_LIMIT_RPM` | `60` | Max requests per minute per key |
| `DOCS_PATH` | `./docs` | Path to documents folder |
| `INDEX_PATH` | `./faiss_index/index.faiss` | FAISS index file path |
| `META_PATH` | `./faiss_index/index.pkl` | Chunk metadata file path |