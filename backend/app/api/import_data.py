"""Production data-intake endpoints with validation and quarantine gates."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.database import get_db
from app.models.user import User
from app.services.data_intake import DATA_ROOT, DataIntakeService

logger = logging.getLogger(__name__)
router = APIRouter()
intake_service = DataIntakeService()


async def _process_upload(file: UploadFile, db: Session, current_user: User, csv_only: bool = False) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Upload must include a filename")
    suffix = Path(file.filename).suffix.lower()
    allowed = {".csv"} if csv_only else {".csv", ".zip"}
    if suffix not in allowed:
        label = "CSV" if csv_only else "CSV or ZIP"
        raise HTTPException(status_code=400, detail=f"Only {label} files are accepted")
    if suffix == ".csv":
        raise HTTPException(status_code=410, detail="CSV uploads now require column mapping and source provenance. Use Data Import (/intake/preview, then commit).")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > 250 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Upload exceeds the 250 MB intake limit")

    result = intake_service.process(file.filename, content, uploaded_by=current_user.username, organization_id=current_user.organization_id)
    response = result.response()
    response.update({"message": "File quarantined" if result.quarantined else "Validation complete"})
    if result.quarantined:
        return response
    return response


@router.post("/file", status_code=status.HTTP_200_OK, dependencies=[Depends(require_role("admin", "embryologist"))])
async def import_file(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Accept CSV clinical datasets or blastocyst image ZIP archives."""
    return await _process_upload(file, db, current_user)


@router.post("/csv", status_code=status.HTTP_200_OK, dependencies=[Depends(require_role("admin", "embryologist"))])
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Backward-compatible CSV-only route using the full validation pipeline."""
    return await _process_upload(file, db, current_user, csv_only=True)


@router.get("/reports", dependencies=[Depends(require_role("admin", "embryologist"))])
def ingestion_reports(current_user: User = Depends(get_current_user)):
    ledger = DATA_ROOT / "reports" / "ingestion_report.csv"
    if not ledger.exists():
        return {"items": [], "total": 0}
    with ledger.open(encoding="utf-8") as stream:
        items = list(csv.DictReader(stream))
    authorized = []
    for item in items:
        report_id = item.get("intake_id", "")
        if not report_id or not all(c.isalnum() or c == "-" for c in report_id):
            continue
        path = DATA_ROOT / "reports" / f"{report_id}_summary.json"
        if path.exists():
            metadata = json.loads(path.read_text(encoding="utf-8")).get("metadata", {})
            if current_user.organization_id is not None and metadata.get("organization_id") == current_user.organization_id:
                authorized.append(item)
    items = authorized
    items.reverse()
    return {"items": items[:200], "total": len(items)}


@router.get("/reports/{intake_id}", dependencies=[Depends(require_role("admin", "embryologist"))])
def ingestion_report(intake_id: str, current_user: User = Depends(get_current_user)):
    if not all(character.isalnum() or character == "-" for character in intake_id):
        raise HTTPException(status_code=400, detail="Invalid intake identifier")
    path = DATA_ROOT / "reports" / f"{intake_id}_summary.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Ingestion report not found")
    report = json.loads(path.read_text(encoding="utf-8"))
    if current_user.organization_id is None or report.get("metadata", {}).get("organization_id") != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Ingestion report not found")
    return report


@router.post("/seed-from-disk", status_code=status.HTTP_200_OK, dependencies=[Depends(require_role("admin", "embryologist"))])
def seed_from_disk(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    raise HTTPException(status_code=410, detail="Disk seeding has been retired. Import the file through the mapped intake with an explicit source classification.")
