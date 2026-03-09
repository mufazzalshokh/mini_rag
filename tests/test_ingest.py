import app.api.ingest as ingest_mod
from app.core import chunk_manager


def test_ingest_builds_index(client, tmp_path, monkeypatch):
    # Create a real temp doc
    doc = tmp_path / "sample.txt"
    doc.write_text("This is a test document for ingestion.")

    # Point settings at tmp_path so the endpoint finds the file
    monkeypatch.setattr(ingest_mod.settings, "docs_path", str(tmp_path))

    # Mock build_index so we don't need real embeddings in CI
    monkeypatch.setattr(chunk_manager, "build_index", lambda paths: (3, 50))

    r = client.post("/ingest", headers={"x-api-key": "test"})
    assert r.status_code == 200
    data = r.json()
    assert "docs" in data
    assert "chunks" in data
    assert "est_tokens" in data
    assert data["chunks"] == 3