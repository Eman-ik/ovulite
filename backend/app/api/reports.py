"""Data export.

Produces a real file. The previous Reports page called nothing at all — it
ran a `setTimeout`, fired a confetti animation and told the user "Your report
has been downloaded successfully" while producing no file, which is worse than
having no export button because it teaches people the export works.

CSV rather than PDF: the rows here are what someone actually wants to analyse
or hand to a vet, and a generated PDF would be a second rendering of numbers
that already have a canonical presentation in the app.
"""

import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.api.transfers import _clean_pregnancy_result
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.embryo import Embryo
from app.models.et_transfer import ETTransfer
from app.models.opu_session import OPUSession
from app.models.user import User

router = APIRouter()

DATASETS = {
    "transfers": "Embryo transfers with recipient, donor, sire and outcome",
    "embryos": "Embryo bank with donor, sire, grade and status",
    "opu-sessions": "Ovum pick-up sessions with recovery and oocyte grading",
}


def _stream(rows: list[dict], filename: str) -> StreamingResponse:
    """Serialise rows to CSV. An empty result still yields a header row, so a
    zero-row export is visibly empty rather than an unreadable file."""
    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    else:
        buffer.write("no_rows_matched\n")
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/datasets")
def list_datasets(_current_user: User = Depends(get_current_user)) -> dict:
    """What can be exported, so the UI offers only real options."""
    return {"datasets": [{"key": k, "description": v} for k, v in DATASETS.items()]}


@router.get("/export/{dataset}")
def export(
    dataset: str,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export one dataset as CSV, scoped to the caller's organization."""
    if dataset not in DATASETS:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Unknown dataset '{dataset}'. Available: {', '.join(DATASETS)}",
        )
    org_id = current_user.organization_id
    stamp = date.today().isoformat()

    if dataset == "transfers":
        query = (
            db.query(ETTransfer)
            .options(
                joinedload(ETTransfer.recipient),
                joinedload(ETTransfer.protocol),
                joinedload(ETTransfer.technician),
                joinedload(ETTransfer.embryo).joinedload(Embryo.donor),
                joinedload(ETTransfer.embryo).joinedload(Embryo.sire),
            )
            .filter(ETTransfer.organization_id == org_id)
        )
        if date_from:
            query = query.filter(ETTransfer.et_date >= date_from)
        if date_to:
            query = query.filter(ETTransfer.et_date <= date_to)
        rows = [
            {
                "transfer_id": t.transfer_id,
                "et_number": t.et_number,
                "et_date": t.et_date,
                "farm_location": t.farm_location,
                "recipient_tag": t.recipient.tag_id if t.recipient else None,
                "donor_tag": t.embryo.donor.tag_id if t.embryo and t.embryo.donor else None,
                "sire_name": t.embryo.sire.name if t.embryo and t.embryo.sire else None,
                "embryo_stage": t.embryo.stage if t.embryo else None,
                "embryo_grade": t.embryo.grade if t.embryo else None,
                "fresh_or_frozen": t.embryo.fresh_or_frozen if t.embryo else None,
                "protocol": t.protocol.name if t.protocol else None,
                "technician": t.technician.name if t.technician else None,
                "bc_score": t.bc_score,
                "cl_side": t.cl_side,
                "cl_measure_mm": t.cl_measure_mm,
                # The normalised value, so an export cannot disagree with what
                # the app shows. Raw values that do not resolve become blank.
                "pc1_result": _clean_pregnancy_result(t.pc1_result),
                "pc1_date": t.pc1_date,
            }
            for t in query.order_by(ETTransfer.et_date.desc()).all()
        ]
        return _stream(rows, f"ovulite-transfers-{stamp}.csv")

    if dataset == "embryos":
        rows = [
            {
                "embryo_id": e.embryo_id,
                "donor_tag": e.donor.tag_id if e.donor else None,
                "sire_name": e.sire.name if e.sire else None,
                "opu_date": e.opu_date,
                "stage": e.stage,
                "grade": e.grade,
                "fresh_or_frozen": e.fresh_or_frozen,
                "cane_number": e.cane_number,
                "freezing_date": e.freezing_date,
                "status": e.status,
            }
            for e in db.query(Embryo)
            .options(joinedload(Embryo.donor), joinedload(Embryo.sire))
            .filter(Embryo.organization_id == org_id)
            .order_by(Embryo.embryo_id.desc())
            .all()
        ]
        return _stream(rows, f"ovulite-embryos-{stamp}.csv")

    rows = [
        {
            "opu_id": s.opu_id,
            "opu_date": s.opu_date,
            "donor_tag": s.donor.tag_id if s.donor else None,
            "farm_location": s.farm_location,
            "total_follicles": s.total_follicles,
            "oocytes_recovered": s.oocytes_recovered,
            "viable_oocytes": s.viable_oocytes,
            "grade_a_oocytes": s.grade_a_oocytes,
            "grade_b_oocytes": s.grade_b_oocytes,
            "grade_c_oocytes": s.grade_c_oocytes,
            "degenerated_oocytes": s.degenerated_oocytes,
        }
        for s in db.query(OPUSession)
        .options(joinedload(OPUSession.donor))
        .filter(OPUSession.organization_id == org_id)
        .order_by(OPUSession.opu_date.desc())
        .all()
    ]
    return _stream(rows, f"ovulite-opu-sessions-{stamp}.csv")
