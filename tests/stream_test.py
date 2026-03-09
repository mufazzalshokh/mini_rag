import json
from app.api import ask as ask_mod


def fake_tokens():
    yield json.dumps({"event": "token", "data": "Hello"})
    yield json.dumps({"event": "token", "data": " world"})
    yield json.dumps({"event": "done", "data": {
        "answer": "Hello world [1]",
        "citations": [{"source_id": "sample.txt#0", "snippet": "Hello world"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2, "cost_usd": 0.0, "latency_ms": 5}
    }}), 2, 0.0, 5


def parse_sse_lines(r):
    return [
        line[6:] if line.startswith("data: ") else line
        for line in r.iter_lines()
        if line.strip() and line.strip() != "data:"
    ]


def test_ask_streams_tokens(client, monkeypatch):
    monkeypatch.setattr(ask_mod, "tokens_from_openai", lambda *a, **k: fake_tokens())
    payload = {"question": "What is in my documents?", "max_tokens": 50, "budget_usd": 0.01}
    headers = {"x-api-key": "test", "accept": "text/event-stream"}

    with client.stream("POST", "/ask", json=payload, headers=headers) as r:
        assert r.status_code == 200
        lines = parse_sse_lines(r)

    events = [json.loads(line) for line in lines]
    event_types = [e["event"] for e in events]
    assert "token" in event_types
    assert "done" in event_types


def test_ask_done_payload_has_required_fields(client, monkeypatch):
    monkeypatch.setattr(ask_mod, "tokens_from_openai", lambda *a, **k: fake_tokens())
    payload = {"question": "What is in my documents?", "max_tokens": 50, "budget_usd": 0.01}
    headers = {"x-api-key": "test", "accept": "text/event-stream"}

    with client.stream("POST", "/ask", json=payload, headers=headers) as r:
        lines = parse_sse_lines(r)

    done_event = next(e for e in [json.loads(l) for l in lines] if e["event"] == "done")
    data = done_event["data"]
    assert "answer" in data
    assert "citations" in data
    assert "usage" in data
    assert "cost_usd" in data["usage"]
    assert "latency_ms" in data["usage"]