import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.donors import router as donors_router
from app.api.embryos import router as embryos_router
from app.api.import_data import router as import_router
from app.api.grading import router as grading_router
from app.api.predictions import router as predictions_router
from app.api.protocols import router as protocols_router
from app.api.qc import router as qc_router
from app.api.recipients import router as recipients_router
from app.api.sires import router as sires_router
from app.api.technicians import router as technicians_router
from app.api.transfers import router as transfers_router
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
app.include_router(donors_router, prefix="/donors", tags=["donors"])
app.include_router(sires_router, prefix="/sires", tags=["sires"])
app.include_router(recipients_router, prefix="/recipients", tags=["recipients"])
app.include_router(embryos_router, prefix="/embryos", tags=["embryos"])
app.include_router(transfers_router, prefix="/transfers", tags=["transfers"])
app.include_router(technicians_router, prefix="/technicians", tags=["technicians"])
app.include_router(protocols_router, prefix="/protocols", tags=["protocols"])
app.include_router(import_router, prefix="/import", tags=["import"])
app.include_router(predictions_router, prefix="/predict", tags=["predictions"])
app.include_router(grading_router, prefix="/grade", tags=["grading"])
app.include_router(qc_router, prefix="/qc", tags=["qc"])


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
