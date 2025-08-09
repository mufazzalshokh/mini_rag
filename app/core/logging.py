import json
import uuid
import time
from fastapi import Request

def log_event(event_type, data):
    print(json.dumps({"event_type": event_type, **data}, ensure_ascii=False))

def make_request_id():
    return str(uuid.uuid4())

def log_request(request_id, route, status, tokens=None, cost=None, latency=None):
    entry = {
        "request_id": request_id,
        "route": route,
        "status": status,
    }
    if tokens is not None:
        entry["tokens"] = tokens
    if cost is not None:
        entry["cost_usd"] = cost
    if latency is not None:
        entry["latency_ms"] = latency
    log_event("request_log", entry)
