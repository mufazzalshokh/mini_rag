from app.core import chunk_manager


def test_ingest_builds_index(client, tmp_path, monkeypatch):
    # Create ./docs relative to tmp_path so settings.docs_path ("./docs") resolves correctly
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "sample.txt").write_text("This is a test document for ingestion.")

    # Change CWD — now "./docs" points to our tmp docs_dir
    monkeypatch.chdir(tmp_path)

    # Mock build_index so no real embeddings are needed in CI
    monkeypatch.setattr(chunk_manager, "build_index", lambda paths: (3, 50))

    r = client.post("/ingest", headers={"x-api-key": "test"})
    assert r.status_code == 200
    data = r.json()
    assert data["chunks"] == 3
    assert "docs" in data
    assert "est_tokens" in data