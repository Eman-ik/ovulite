"""Bulk CSV import endpoint — upload CSV and ingest into database."""

import io
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.database import get_db
from app.models.et_transfer import ETTransfer
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/csv",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role("admin", "embryologist"))],
)
async def import_csv(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a CSV file and ingest ET data into the database.

    Expects the same format as 'ET Summary - ET Data.csv'.
    Only admin and embryologist roles can import data.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    # Check if data already exists
    existing = db.query(ETTransfer).count()
    if existing > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Database already has {existing} transfer records. "
            "Truncate first or use individual CRUD endpoints.",
        )

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    # Import the ingestion function
    import sys
    from pathlib import Path

    scripts_dir = str(Path(__file__).resolve().parent.parent.parent / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    from ingest_et_data import ingest_et_data

    # Write content to a temp file for the ingestion function
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
        tmp.write(text)
        tmp_path = tmp.name

    try:
        stats = ingest_et_data(tmp_path, db)
    finally:
        os.unlink(tmp_path)

    logger.info(
        "CSV import by user '%s': %d rows ingested, %d skipped",
        current_user.username,
        stats["rows_ingested"],
        stats["rows_skipped"],
    )

    return {
        "message": "CSV import complete",
        "rows_read": stats["rows_read"],
        "rows_ingested": stats["rows_ingested"],
        "rows_skipped": stats["rows_skipped"],
        "errors": stats["errors"][:20],  # limit error output
    }


@router.post(
    "/seed-from-disk",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role("admin"))],
)
def seed_from_disk(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger ingestion of the bundled ET Data CSV from docs/dataset/ on disk.

    Admin-only. Only works if database is empty.
    """
    import os
    from pathlib import Path

    csv_path = str(
        Path(__file__).resolve().parent.parent.parent.parent
        / "docs"
        / "dataset"
        / "ET Summary - ET Data.csv"
    )

    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail=f"CSV file not found at expected path")

    existing = db.query(ETTransfer).count()
    if existing > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Database already has {existing} transfer records.",
        )

    import sys

    scripts_dir = str(Path(__file__).resolve().parent.parent.parent / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    from ingest_et_data import ingest_et_data

    stats = ingest_et_data(csv_path, db)

    logger.info(
        "Disk seed by user '%s': %d rows ingested",
        current_user.username,
        stats["rows_ingested"],
    )

    return {
        "message": "Seed from disk complete",
        "rows_read": stats["rows_read"],
        "rows_ingested": stats["rows_ingested"],
        "rows_skipped": stats["rows_skipped"],
        "errors": stats["errors"][:20],
    }
