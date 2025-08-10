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

### 2) Docker

# build
docker build -t mini-rag-app .

# run (Windows PowerShell)
docker run --rm --name mini-rag `
  --env-file .env -p 8000:8000 `
  -v "${PWD}\docs:/app/docs" mini-rag-app

# (mac/linux bind mount: -v "${PWD}/docs:/app/docs")

Endpoints
POST /ingest
Re-ingests everything from ./docs (or accepts multipart uploads) and rebuilds the index.
Avoids duplicate chunk inflation on re-ingest.

Headers

X-API-Key: your-secret-key

Examples
# bash
curl -s -X POST http://localhost:8000/ingest -H "x-api-key: your-secret-key"
# PowerShell (use curl.exe, not the alias)
curl.exe -s -X POST http://localhost:8000/ingest -H "x-api-key: your-secret-key"

Response
#json
{
  "docs": 3,
  "chunks": 42,
  "est_tokens": 9000
}

Multipart upload is supported (files are saved into DOCS_PATH then indexed).

POST /ask (SSE streaming)
Headers

X-API-Key: your-secret-key
Accept: text/event-stream
Content-Type: application/json

Body
#json
{
  "question": "What text was ingested?",
  "max_tokens": 50,
  "budget_usd": 0.02
}

Stream format (SSE)
Each line is a JSON object sent as a data: line:
#css
data: {"event":"token","data":"Hel"}
data: {"event":"token","data":"lo"}
data: {"event":"done","data":{"answer":"Hello [1]","citations":[...],"usage":{...}}}

Python Consumer
#python
import requests, json

url = "http://127.0.0.1:8000/ask"
headers = {
    "x-api-key": "your-secret-key",
    "Accept": "text/event-stream",
    "Content-Type": "application/json",
}
payload = {"question":"What text was ingested?","max_tokens":50,"budget_usd":0.02}

with requests.post(url, json=payload, headers=headers, stream=True) as r:
    r.raise_for_status()
    for raw in r.iter_lines(decode_unicode=True):
        if not raw:
            continue
        line = raw[6:] if raw.startswith("data: ") else raw
        msg = json.loads(line)
        if msg["event"] == "token":
            print(msg["data"], end="", flush=True)
        elif msg["event"] == "done":
            print("\n\n[FINAL]", json.dumps(msg["data"], indent=2))

Final done payload

#json
{
  "answer": "string with inline [1] [2]...",
  "citations": [
    {"source_id":"filename#chunk_or_page","snippet":"short excerpt"}
  ],
  "usage": {
    "prompt_tokens": 862,
    "completion_tokens": 120,
    "cost_usd": 0.0045,
    "latency_ms": 3078
  }
}

Retrieval & Prompting
Hybrid retrieval: FAISS vector similarity blended with a lightweight lexical scorer.
Prompt instructs the model to answer only from provided context and include inline references [1] [2] … matching the returned citations.

Budget guardrails:
Estimate prompt cost; if it exceeds budget_usd, return a budget message.
Track tokens during streaming; stop mid-generation if exceeding budget.
Resilience: exponential backoff on 429; timeout handling.

Security & Ops
Auth: X-API-Key required (API_KEY in .env).
In tests (pytest), the header value test is accepted.

Rate limit: in-memory RPM (RATE_LIMIT_RPM).

Logging: structured JSON logs per request: {request_id, route, status, tokens, cost, latency_ms}.
No secrets logged.

Configuration
Create .env (see .env.example):

OPENAI_API_KEY=sk-...
API_KEY=your-secret-key

# Optional (defaults exist)
CHUNK_SIZE=500
TOP_K=5
MODEL_NAME=gpt-4o
RATE_LIMIT=60
DOCS_PATH=./docs
INDEX_PATH=./index/faiss.index


Make targets
#bash
make run            # uvicorn app.main:app --reload
make docker-build
make docker-run
make ingest         # calls /ingest using API_KEY from .env
make test           # installs dev reqs, runs pytest
make eval           # installs dev reqs, runs eval/run.py
make clean-index    # remove local FAISS index


Tests

from repo root
#powershell
# Windows: ensure local imports resolve
$env:PYTHONPATH = (Get-Location).Path
pytest -q


Covers:

ingestion builds a non-empty index and avoids duplicate chunks on re-ingest
/ask streams tokens and finishes with a valid done payload
off-topic fallback without fabricated citations
prompt-injection attempt is neutralized
5 parallel /ask calls succeed


Evaluation

Quick eval (3 Qs)
#bash
python eval/quick_eval.py

Scripted eval (JSONL)
eval/golden.jsonl contains the questions. Run:
#bash
python eval/run.py http://127.0.0.1:8000

Writes eval/report.json with:
avg_similarity (answer vs. reference)
citation_rate (>= 1 inline [n])
avg_latency_ms

Make sure the server is running and /ingest has been called at least once before eval


Troubleshooting
401 Unauthorized: missing/incorrect X-API-KEY . Use the value from .env
In tests, "test" is allowed.

500 on /ask: check that
1. /ingest ran successfully,
2. OPENAI_API_KEY is set,
3. budget_usd isn't too small.

PowerShell curl quirks: use curl.exe (not the alias)

Port already allocated:
#powershell
docker rm -f mini-rag


Known limitations

Small local dataset by design; FAISS index is local only.
Cost estimation uses a simple per-model map.
Lexical scorer is lightweight; swap in stronger BM25 or a re-ranker for better quality.
SSE lines carry JSON (single data: lines), not named SSE event fields.
