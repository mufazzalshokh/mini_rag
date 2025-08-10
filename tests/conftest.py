import json
import pytest
from fastapi.testclient import TestClient

# Import your FastAPI app
from app.main import app

@pytest.fixture(scope="session")
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def require_api_key(monkeypatch):
    # Ensure header is always accepted in tests
    def _check_api_key(request):
        return True
    from app.api import auth as auth_mod
    monkeypatch.setattr(auth_mod, "check_service_api_key", lambda req: None)
