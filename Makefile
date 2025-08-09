run:
	uvicorn app.main:app --reload

docker-build:
	docker build -t mini-rag-app .

docker-run:
	docker run -p 8000:8000 --env-file .env mini-rag-app

test:
	pytest tests/

eval:
	python eval/run.py --host http://localhost:8000
