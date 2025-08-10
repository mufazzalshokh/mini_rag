from fastapi import Header, HTTPException, status
from app.core.config import settings
import os

def check_service_api_key(x_api_key: str = Header(None)) -> None:
    """
    Require X-API-Key in normal runs. When tests run under pytest,
    accept 'test' so unit tests don't need your real key.
    """
    # Allow the special key when pytest is running
    if os.getenv("PYTEST_CURRENT_TEST") is not None:
        if x_api_key == "test":
            return

    # Normal enforcement
    if not x_api_key or x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return
