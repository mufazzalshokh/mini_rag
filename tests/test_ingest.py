import os
from app.core import chunk_manager as cm


def test_ingest_builds_index(client, tmp_path, monkeypatch):
    # Create a real temp doc file
    doc = tmp_path / "sample.txt"
    doc.write_text("This is a test document for ingestion.")

    # Point settings at tmp dirs
    monkeypatch.setenv("DOCS_PATH", str(tmp_path))
    monkeypatch.setenv("INDEX_PATH", str(tmp_path / "index.faiss"))
    monkeypatch.setenv("META_PATH", str(tmp_path / "index.pkl"))

    # Re-load settings so monkeypatched env vars take effect
    from app.core.config import get_settings
    get_settings.cache_clear()

    r = client.post("/ingest", headers={"x-api-key": "test"})
    assert r.status_code == 200
    data = r.json()
    assert "docs" in data
    assert "chunks" in data
    assert "est_tokens" in data
    assert data["chunks"] >= 1