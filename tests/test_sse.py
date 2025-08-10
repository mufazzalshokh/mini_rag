import requests, json

url = "http://127.0.0.1:8000/ask"
headers = {
    "x-api-key": "your-secret-key",
    "Accept": "text/event-stream",
    "Content-Type": "application/json",
}
payload = {"question": "What text was ingested?", "max_tokens": 50, "budget_usd": 0.02}

with requests.post(url, json=payload, headers=headers, stream=True) as r:
    if r.status_code != 200:
        print("STATUS:", r.status_code)
        # Try to show JSON first; fall back to raw text
        try:
            print("BODY:", r.json())
        except Exception:
            print("BODY:", r.text)
        raise SystemExit(1)

    for raw in r.iter_lines(decode_unicode=True):
        if not raw:
            continue
        # EventSourceResponse prefixes with "data: "
        line = raw
        if line.startswith("data: "):
            line = line[6:]

        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            print(raw)  # show whatever came back
            continue

        if msg.get("event") == "token":
            print(msg["data"], end="", flush=True)
        elif msg.get("event") == "done":
            print("\n\n[DONE]", json.dumps(msg["data"], indent=2))
