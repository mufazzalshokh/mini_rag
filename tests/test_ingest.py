from app.core import chunk_manager


def test_ingest_builds_index(client, tmp_path, monkeypatch):
    doc = tmp_path / "sample.txt"
    doc.write_text("This is a test document for ingestion.")

    # Now works because frozen=False
    from app.core.config import settings
    monkeypatch.setattr(settings, "docs_path", str(tmp_path))
    monkeypatch.setattr(settings, "index_path", str(tmp_path / "index.faiss"))
    monkeypatch.setattr(settings, "meta_path", str(tmp_path / "index.pkl"))

    # Mock at source so the import inside the route handler gets the mock
    monkeypatch.setattr(chunk_manager, "build_index", lambda paths: (3, 50))

    r = client.post("/ingest", headers={"x-api-key": "test"})
    assert r.status_code == 200
    data = r.json()
    assert data["chunks"] == 3
    assert "docs" in data
    assert "est_tokens" in data