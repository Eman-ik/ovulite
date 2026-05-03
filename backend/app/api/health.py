import os
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User

router = APIRouter()

START_TIME = time.time()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ovulite-api",
        "version": "0.5.0",
        "timestamp": time.time(),
    }


@router.get("/health/db")
async def health_check_db(db: Session = Depends(get_db), _current_user: User = Depends(get_current_user)):
    try:
        db.execute(text("SELECT 1"))
        return {"database": "healthy"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"DB error: {exc}")


@router.get("/health/ml")
async def health_check_ml(_current_user: User = Depends(get_current_user)):
    model_path = Path(__file__).resolve().parents[3] / "ml" / "artifacts" / "pregnancy_model_v1.joblib"
    if model_path.exists():
        return {"ml_models": "healthy", "prediction_model": str(model_path.name)}
    raise HTTPException(status_code=503, detail="Prediction model artifact not found")


@router.get("/health/readiness")
async def readiness_check(db: Session = Depends(get_db), _current_user: User = Depends(get_current_user)):
    try:
        db.execute(text("SELECT 1"))
        return {"ready": True}
    except Exception:
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/metrics")
async def metrics(_current_user: User = Depends(get_current_user)):
    return {
        "uptime_seconds": int(time.time() - START_TIME),
        "env": os.getenv("ENVIRONMENT", "development"),
        "rate_limit_per_minute": int(os.getenv("RATE_LIMIT_PER_MINUTE", "120")),
    }
