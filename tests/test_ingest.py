from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_ingest_endpoint():
    test_file = ('file', open('docs/sample.pdf', 'rb'))
    response = client.post("/ingest", files=[test_file])
    assert response.status_code == 200
    assert response.json()['chunks'] > 0
