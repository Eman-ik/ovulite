"""Source-backed case chronology, independent of prediction and QC modules."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.embryo import Embryo
from app.models.et_transfer import ETTransfer
from app.models.intake_batch import IntakeBatch, TransferProvenance
from app.models.user import User
from app.models.case_metadata import CaseMetadata, CaseAudit

router = APIRouter()


@router.get("/{transfer_id}/timeline")
def timeline(transfer_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    org_id = user.organization_id
    if org_id is None:
        raise HTTPException(403, "An organization is required")
    transfer = db.query(ETTransfer).filter_by(transfer_id=transfer_id, organization_id=org_id).first()
    if transfer is None:
        raise HTTPException(404, "Case not found")
    events = []

    def add(kind, when, label, identifier):
        if when:
            events.append({"kind": kind, "date": when.isoformat(), "label": label, "record_id": identifier})

    embryo = transfer.embryo
    if embryo and embryo.organization_id != org_id:
        embryo = None
    donor_id = embryo.donor_id if embryo else None
    if embryo:
        opu = embryo.opu_session
        batch = embryo.ivf_batch
        if opu and opu.organization_id == org_id:
            add("opu", opu.opu_date, "Ovum pickup", opu.opu_id)
        elif embryo.opu_date:
            add("opu", embryo.opu_date, "OPU date recorded on embryo", embryo.embryo_id)
        if batch and batch.organization_id == org_id:
            add("ivf", batch.ivf_date, "IVF batch", batch.ivf_batch_id)
        add("cryopreservation", embryo.freezing_date, "Embryo freezing", embryo.embryo_id)
    add("transfer", transfer.et_date, "Embryo transfer", transfer.transfer_id)
    add("pregnancy_check", transfer.pc1_date, f"First pregnancy check: {transfer.pc1_result or 'result not recorded'}", transfer.transfer_id)
    add("pregnancy_check", transfer.pc2_date, f"Second pregnancy check: {transfer.pc2_result or 'result not recorded'}", transfer.transfer_id)
    metadata = db.query(CaseMetadata).filter_by(transfer_id=transfer_id, organization_id=org_id).first()
    if metadata:
        from datetime import date
        for field, label in (("pregnancy_loss_date", "Recorded pregnancy loss"), ("calving_date", "Recorded calving")):
            if metadata.data.get(field):
                add(field, date.fromisoformat(metadata.data[field]), label, transfer_id)
    events.sort(key=lambda event: event["date"])

    prior = db.query(ETTransfer).filter(ETTransfer.organization_id == org_id,
        ETTransfer.et_date < transfer.et_date, ETTransfer.transfer_id != transfer_id)

    def history(query):
        total = query.count()
        return {"total": total, "items": [{"transfer_id": row.transfer_id, "date": row.et_date,
                 "outcome": row.pc1_result, "checkpoint_date": row.pc1_date} for row in query.order_by(ETTransfer.et_date.desc(), ETTransfer.transfer_id.desc()).limit(100)]}

    provenance = db.query(TransferProvenance).filter_by(transfer_id=transfer_id, organization_id=org_id).first()
    source = None
    if provenance:
        imported = db.query(IntakeBatch).filter_by(batch_id=provenance.batch_id, organization_id=org_id).first()
        if imported:
            source = {"source_type": provenance.source_type, "source_row": provenance.source_row,
                      "filename": imported.filename, "reference": imported.source_reference,
                      "checksum": imported.checksum, "imported_by": imported.created_by}
    if source is None and metadata:
        source = {"source_type": metadata.source_type, "reference": metadata.source_reference,
                  "imported_by": metadata.updated_by, "filename": "Manual record", "source_row": None, "checksum": None}
    audit = db.query(CaseAudit).filter_by(transfer_id=transfer_id, organization_id=org_id).order_by(CaseAudit.created_at.desc(), CaseAudit.audit_id.desc()).limit(100).all()
    return {"events": events, "provenance": source,
            "canonical_record": metadata.data if metadata else None, "record_version": metadata.version if metadata else None,
            "audit": [{"action": row.action, "actor": row.actor, "timestamp": row.created_at, "details": row.details} for row in audit],
            "recipient_history": history(prior.filter(ETTransfer.recipient_id == transfer.recipient_id)) if transfer.recipient_id else {"total": 0, "items": []},
            "donor_history": history(prior.join(Embryo, ETTransfer.embryo_id == Embryo.embryo_id).filter(Embryo.donor_id == donor_id, Embryo.organization_id == org_id)) if donor_id else {"total": 0, "items": []},
            "limitations": "History includes earlier ET dates only, up to 100 most recent attempts per animal. Missing events and calving outcomes are not inferred."}
