import json
import re
from app.api import ask as ask_mod

def fake_tokens():
    # yield 2 token events and a final "done"
    for t in ["Hel", "lo"]:
        yield t
    yield json.dumps({
        "event":"done",
        "data":{
            "answer":"Hello [1]",
            "citations":[{"source_id":"sample.txt#0","snippet":"Hello world"}],
            "usage":{"prompt_tokens":10,"completion_tokens":2,"cost_usd":0.0001,"latency_ms":5}
        }
    })

def test_ask_streams_and_done(client, monkeypatch):
    monkeypatch.setattr(ask_mod, "tokens_from_openai", lambda *a, **k: fake_tokens())
    payload = {"question":"hi","max_tokens":10,"budget_usd":0.02}
    with client.stream("POST","/ask", headers={"x-api-key":"test","accept":"text/event-stream"}, json=payload) as r:
        assert r.status_code == 200
        r.read()  # consume the streaming body for httpx>=0.27
        r.read()  # consume streaming body for httpx>=0.27
        body = r.text
        # Normalize away optional "data: " SSE prefix per line
        body_norm = "\n".join(re.sub(r"^data:\s*", "", ln) for ln in body.splitlines())
        assert "Hel" in body_norm and "lo" in body_norm
        assert '"event": "done"' in body_norm
