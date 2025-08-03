run:
	uvicorn app.main:app --reload

test:
	pytest

eval:
	python eval/run.py
