.PHONY: run run-local docker-build docker-run docker-run-mount docker-run-win docker-stop docker-logs ingest test eval clean-index

# Run locally with hot-reload (uses your host Python env)
run-local:
	uvicorn app.main:app --reload

# Build Docker image
docker-build:
	docker build -t mini-rag-app .

# Run Docker (no volume mount)
docker-run:
	docker run --rm --name mini-rag \
	  --env-file .env -p 8000:8000 \
	  mini-rag-app

# Run Docker with docs mounted (Linux/macOS)
run: docker-run-mount
docker-run-mount:
	docker run --rm --name mini-rag \
	  --env-file .env -p 8000:8000 \
	  -v $$(pwd)/docs:/app/docs \
	  mini-rag-app

# Run Docker with docs mounted (Windows PowerShell)
docker-run-win:
	docker run --rm --name mini-rag ^
	  --env-file .env -p 8000:8000 ^
	  -v "$${PWD}\docs:/app/docs" mini-rag-app

# Stop & remove the running container if exists
docker-stop:
	- docker stop mini-rag
	- docker rm -f mini-rag

# Tail logs of the running container
docker-logs:
	docker logs -f mini-rag

# Quick ingest call (requires API_KEY in .env)
ingest:
	@if [ -z "$$API_KEY" ]; then echo "API_KEY not set (put it in .env)"; exit 1; fi
	curl -s -X POST http://localhost:8000/ingest -H "x-api-key: $$API_KEY" || true
	@echo

# Pytest (install dev deps if the file exists)
test:
	@if [ -f requirements-dev.txt ]; then python -m pip install -r requirements-dev.txt; fi
	pytest -q

# Eval script (install dev deps if present) — NOTE: positional host, no --host flag
eval:
	@if [ -f requirements-dev.txt ]; then python -m pip install -r requirements-dev.txt; fi
	python eval/run.py http://localhost:8000

# Clean local FAISS artifacts
clean-index:
	rm -rf index/*.index index/*.pkl index/*.bin || true
