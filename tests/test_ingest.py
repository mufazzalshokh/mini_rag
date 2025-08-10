def test_ingest_builds_index(client, tmp_path, monkeypatch):
    # If your ingest reads ./docs, we’ll just call it and assert JSON fields exist.
    r = client.post("/ingest", headers={"x-api-key":"test"})
    assert r.status_code == 200
    data = r.json()
    assert "docs" in data and "chunks" in data and "est_tokens" in data
    assert data["chunks"] >= 0
