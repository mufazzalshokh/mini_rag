import requests

url = "http://127.0.0.1:8000/ask"
headers = {
    "x-api-key": "your-secret-key",    # put your real key here
    "accept": "text/event-stream",
    "Content-Type": "application/json"
}
payload = {
    "question": "What is in my documents?",
    "max_tokens": 50,
    "budget_usd": 0.01
}

with requests.post(url, json=payload, headers=headers, stream=True) as resp:
    for line in resp.iter_lines(decode_unicode=True):
        if line:
            print(line)
