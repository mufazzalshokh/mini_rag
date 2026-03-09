import app.api.ingest as ingest_mod


def test_ingest_builds_index(client, tmp_path, monkeypatch):
    # Create ./docs relative to tmp_path
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "sample.txt").write_text("This is a test document for ingestion.")

    # chdir so settings.docs_path ("./docs") resolves to our tmp dir
    monkeypatch.chdir(tmp_path)

    # Patch the name bound in ingest.py's namespace — NOT chunk_manager
    monkeypatch.setattr(ingest_mod, "build_index", lambda paths: (3, 50))

    r = client.post("/ingest", headers={"x-api-key": "test"})
    assert r.status_code == 200
    data = r.json()
    assert data["chunks"] == 3
    assert "docs" in data
    assert "est_tokens" in data