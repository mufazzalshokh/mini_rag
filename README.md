# Mini RAG Q&A FastAPI Service

A fast, streaming Retrieval-Augmented Generation (RAG) backend using FastAPI, OpenAI, and FAISS.
Streams answers with citations, budget guardrails, and hybrid retrieval.

## Features

- Ingest text/MD/PDF docs, chunked and indexed (FAISS)
- Hybrid retrieval: vector + lexical scoring (BM25/word overlap)
- POST /ask streams tokens (SSE), cites sources, and enforces budget
- Usage stats, rate limiting, and secure API key access
- Docker-ready, Makefile for dev and prod
- Pytest test suite and automated eval script

## Getting Started

### 1. Local Setup

```bash
git clone https://github.com/your/repo.git
cd mini_rag
python -m venv .venv
source .venv/bin/activate # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys etc.
make run
