import requests
from sseclient import SSEClient

url = "http://127.0.0.1:8000/ask"
payload = {"question":"Summarize the first doc.","budget_usd":0.01}

# start the POST with streaming
resp = requests.post(url, json=payload, stream=True)
client = SSEClient(resp)

for event in client.events():
    print(event.event, event.data)
