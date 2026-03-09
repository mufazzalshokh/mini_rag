import json
from app.api import ask as ask_mod


def fake_tokens():
    yield json.dumps({"event": "token", "data": "The"})
    yield json.dumps({"event": "token", "data": " ingested"})
    yield json.dumps({"event": "token", "data": " text"})
    yield json.dumps({"event": "done", "data": {
        "answer": "The ingested text [1]",
        "citations": [{"source_id": "sample.txt#0", "snippet": "The ingested text"}],
        "usage": {"prompt_tokens": 8, "completion_tokens": 3, "cost_usd": 0.0, "latency_ms": 3}
    }}), 3, 0.0, 3


def parse_sse_lines(r):
    return [
        line[6:] if line.startswith("data: ") else line
        for line in r.iter_lines()
        if line.strip() and line.strip() != "data:"
    ]


def test_sse_response_is_valid_json_lines(client, monkeypatch):
    monkeypatch.setattr(ask_mod, "tokens_from_openai", lambda *a, **k: fake_tokens())
    payload = {"question": "What text was ingested?", "max_tokens": 50, "budget_usd": 0.02}
    headers = {"x-api-key": "test", "accept": "text/event-stream"}

    with client.stream("POST", "/ask", json=payload, headers=headers) as r:
        assert r.status_code == 200
        lines = parse_sse_lines(r)

    for line in lines:
        parsed = json.loads(line)
        assert "event" in parsed
        assert "data" in parsed


def test_sse_token_events_contain_strings(client, monkeypatch):
    monkeypatch.setattr(ask_mod, "tokens_from_openai", lambda *a, **k: fake_tokens())
    payload = {"question": "What text was ingested?", "max_tokens": 50, "budget_usd": 0.02}
    headers = {"x-api-key": "test", "accept": "text/event-stream"}

    with client.stream("POST", "/ask", json=payload, headers=headers) as r:
        lines = parse_sse_lines(r)

    token_events = [json.loads(l) for l in lines if json.loads(l)["event"] == "token"]
    assert len(token_events) > 0
    for e in token_events:
        assert isinstance(e["data"], str)