import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router

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


@app.on_event("startup")
def on_startup() -> None:
    logger.info("Ovulite API started")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ovulite-api"}
