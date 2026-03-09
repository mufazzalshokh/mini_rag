from app.core import chunk_manager as cm


def test_ingest_builds_index(client, tmp_path, monkeypatch):
    # Create a real temp doc file
    doc = tmp_path / "sample.txt"
    doc.write_text("This is a test document for ingestion.")

    # Patch settings attributes directly on the already-cached instance
    from app.core.config import settings
    monkeypatch.setattr(settings, "docs_path", str(tmp_path))
    monkeypatch.setattr(settings, "index_path", str(tmp_path / "index.faiss"))
    monkeypatch.setattr(settings, "meta_path", str(tmp_path / "index.pkl"))

    r = client.post("/ingest", headers={"x-api-key": "test"})
    assert r.status_code == 200
    data = r.json()
    assert "docs" in data
    assert "chunks" in data
    assert "est_tokens" in data
    assert data["chunks"] >= 1