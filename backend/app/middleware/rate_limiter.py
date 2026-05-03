import os
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse


RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
_WINDOW_SECONDS = 60
_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


_PROTECTED_PREFIXES = ("/predict", "/grade", "/analytics", "/qc")
_EXEMPT_PREFIXES = ("/health", "/docs", "/openapi.json", "/redoc")


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith(_EXEMPT_PREFIXES) or not path.startswith(_PROTECTED_PREFIXES):
        return await call_next(request)

    key = f"{_client_key(request)}:{path.split('/')[1]}"
    now = time.time()
    bucket = _BUCKETS[key]

    while bucket and now - bucket[0] > _WINDOW_SECONDS:
        bucket.popleft()

    if len(bucket) >= RATE_LIMIT_PER_MINUTE:
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "detail": "Too many requests. Please retry later.",
                "retry_after": _WINDOW_SECONDS,
                "status_code": 429,
            },
        )

    bucket.append(now)
    return await call_next(request)
