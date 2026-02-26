import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.logging_config import setup_logging

# Initialize structured JSON logging before anything else
setup_logging()

logger = logging.getLogger(__name__)

app = FastAPI(title="Ovulite API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every request with method, path, status, duration, and a unique request_id."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    logger.info(
        "%s %s → %s (%.2fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        extra={"request_id": request_id},
    )

    response.headers["X-Request-ID"] = request_id
    return response


@app.on_event("startup")
def on_startup() -> None:
    logger.info("Ovulite API started")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ovulite-api"}
