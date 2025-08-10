import argparse, json, re, time
from pathlib import Path
import requests

CITATION_RE = re.compile(r"\[\d+\]")

def has_inline_citation(text: str) -> bool:
    return bool(CITATION_RE.search(text or ""))

def run_case(host: str, api_key: str, q: dict):
    url_ask = f"{host.rstrip('/')}/ask"
    headers = {
        "x-api-key": api_key or "your-secret-key",
        "accept": "text/event-stream",
        "Content-Type": "application/json",
    }
    payload = {
        "question": q["q"],
        "max_tokens": q.get("max_tokens", 80),
        "budget_usd": q.get("budget_usd", 0.02),
    }

    start = time.time()
    tokens = []
    final_answer = ""
    final_citations = []
    with requests.post(url_ask, json=payload, headers=headers, stream=True, timeout=60) as r:
        r.raise_for_status()
        for raw in r.iter_lines(decode_unicode=True):
            if not raw:
                continue
            line = raw[6:] if raw.startswith("data: ") else raw
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                tokens.append(line)
                continue

            if isinstance(obj, dict):
                ev = obj.get("event")
                data = obj.get("data")
                if ev == "token" and isinstance(data, str):
                    tokens.append(data)
                elif ev == "done":
                    if isinstance(data, dict):
                        final_answer = data.get("answer", "") or ""
                        final_citations = data.get("citations", []) or []
                    elif isinstance(data, str):
                        final_answer = data
                    break

    latency_ms = int((time.time() - start) * 1000)
    if not final_answer:
        final_answer = "".join(tokens).strip()

    return {"answer": final_answer, "citations": final_citations, "latency_ms": latency_ms}

def sim(a: str, b: str) -> float:
    a = (a or "").lower().strip()
    b = (b or "").lower().strip()
    if not a and not b: return 1.0
    if not a or not b: return 0.0
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb: return 0.0
    inter = len(sa & sb); union = len(sa | sb)
    return inter / union

def _normalize_gold_line(line: str):
    """Accepts flexible golden formats."""
    try:
        obj = json.loads(line)
    except Exception:
        # raw string -> question only
        return {"q": line.strip(), "ref": ""}

    if isinstance(obj, str):
        return {"q": obj.strip(), "ref": ""}

    if isinstance(obj, dict):
        q = obj.get("q") or obj.get("question") or obj.get("prompt") or obj.get("ask")
        ref = obj.get("ref") or obj.get("reference") or obj.get("answer") or ""
        if q:
            return {"q": str(q), "ref": str(ref)}
    return None

def main():
    p = argparse.ArgumentParser()
    p.add_argument("host", help="http://localhost:8000")
    p.add_argument("--api-key", default="your-secret-key")
    args = p.parse_args()

    golden_path = Path("eval/golden.jsonl")
    if not golden_path.exists():
        golden_path.write_text(
            "\n".join([
                json.dumps({"q": "What text was ingested?", "ref": "Hello from Docker ingest test"}),
                json.dumps({"q": "List the document filenames that were ingested.", "ref": "hello.txt test.txt.txt"}),
                json.dumps({"q": "Summarize the main ideas across the ingested documents.", "ref": "OpenAI mission GPT safety"}),
            ]), encoding="utf-8"
        )

    gold = []
    for l in golden_path.read_text(encoding="utf-8").splitlines():
        s = l.strip()
        if not s: continue
        norm = _normalize_gold_line(s)
        if norm: gold.append(norm)

    sims, cite_hits, latencies = [], [], []
    for g in gold:
        res = run_case(args.host, args.api_key, g)
        s = sim(res["answer"], g.get("ref", ""))
        cites = has_inline_citation(res["answer"])
        sims.append(s); cite_hits.append(1 if cites else 0); latencies.append(res["latency_ms"])
        print(f"[eval] Q: {g['q'][:30]}... | sim={s:.2f} | cites={cites} | {res['latency_ms']}ms")

    report = {
        "avg_similarity": round(sum(sims)/len(sims), 2) if sims else 0.0,
        "citation_pass_rate": round(sum(cite_hits)/len(cite_hits), 2) if cite_hits else 0.0,
        "avg_latency_ms": int(sum(latencies)/len(latencies)) if latencies else 0,
    }
    Path("eval/report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\n[eval] Wrote eval/report.json ✅")
    print(f"[eval] avg_similarity={report['avg_similarity']:.2f} | citation_rate={report['citation_pass_rate']:.2f} | avg_latency_ms={report['avg_latency_ms']}")

if __name__ == "__main__":
    main()
