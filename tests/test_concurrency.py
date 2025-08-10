import json, threading
from app.api import ask as ask_mod

def fake_tokens():
    for t in ["A", "B"]:
        yield t
    yield json.dumps({"event":"done","data":{
        "answer":"AB [1]",
        "citations":[{"source_id":"sample.txt#0","snippet":"AB"}],
        "usage":{"prompt_tokens":5,"completion_tokens":2,"cost_usd":0.0,"latency_ms":5}
    }})

def test_five_parallel_calls(client, monkeypatch):
    monkeypatch.setattr(ask_mod, "tokens_from_openai", lambda *a, **k: fake_tokens())

    results = []
    def call():
        payload = {"question":"q","max_tokens":10,"budget_usd":0.02}
        with client.stream("POST","/ask", headers={"x-api-key":"test","accept":"text/event-stream"}, json=payload) as r:
            results.append(r.status_code)

    threads = [threading.Thread(target=call) for _ in range(5)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert all(code == 200 for code in results)
