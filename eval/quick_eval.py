import requests, json, re, time

HOST = "http://127.0.0.1:8000"
HEADERS = {
    "x-api-key": "your-secret-key",
    "Accept": "text/event-stream",
    "Content-Type": "application/json",
}

QUESTIONS = [
    {"question": "What text was ingested?", "max_tokens": 60, "budget_usd": 0.05},
    {"question": "List the document filenames that were ingested.", "max_tokens": 80, "budget_usd": 0.05},
    {"question": "Summarize the main ideas across the ingested documents.", "max_tokens": 120, "budget_usd": 0.05},
]

def sse_ask(payload):
    url = f"{HOST}/ask"
    answer_tokens = []
    final_done = None
    t0 = time.time()
    with requests.post(url, json=payload, headers=HEADERS, stream=True) as r:
        r.raise_for_status()
        for raw in r.iter_lines(decode_unicode=True):
            if not raw:
                continue
            line = raw[6:] if raw.startswith("data: ") else raw  # strip SSE 'data: ' if present
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                # not a json line; ignore
                continue
            if msg.get("event") == "token":
                answer_tokens.append(msg["data"])
            elif msg.get("event") == "done":
                final_done = msg["data"]
                break
    latency_ms = int((time.time() - t0) * 1000)
    answer_text = "".join(answer_tokens).strip()
    return answer_text, final_done, latency_ms

def valid_citation(answer_text, citations):
    if not citations:
        return False
    m = re.findall(r"\[(\d+)\]", answer_text)
    return any(1 <= int(x) <= len(citations) for x in m)

def main():
    # ensure ingest ran
    ing = requests.post(f"{HOST}/ingest", headers={"x-api-key": HEADERS["x-api-key"]})
    print("INGEST:", ing.status_code, ing.text)

    passes = 0
    for q in QUESTIONS:
        ans, done, lat = sse_ask(q)
        cites_ok = valid_citation(ans, (done or {}).get("citations", []))
        print("\nQ:", q["question"])
        print("Answer:", ans)
        print("Citations:", (done or {}).get("citations"))
        print("Latency:", lat, "ms")
        print("CITATION CHECK:", "PASS ✅" if cites_ok else "FAIL ❌")
        passes += int(cites_ok)

    print(f"\nSummary: {passes}/{len(QUESTIONS)} with valid inline citations.")

if __name__ == "__main__":
    main()
