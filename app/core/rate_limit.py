import time
from fastapi import HTTPException, status

# Simple in-memory: {api_key: [timestamps]}
rate_limits = {}

def rate_limiter(api_key: str, limit_per_minute: int = 60):
    now = time.time()
    window = 60  # seconds
    times = rate_limits.get(api_key, [])
    # Filter out timestamps older than window
    times = [t for t in times if now - t < window]
    if len(times) >= limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    times.append(now)
    rate_limits[api_key] = times
