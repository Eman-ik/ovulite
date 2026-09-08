"""Persist one validated canonical record and its attributable source snapshot."""
from app.models.case_metadata import CaseAudit, CaseMetadata
from app.models.donor import Donor
from app.models.embryo import Embryo
from app.models.et_transfer import ETTransfer
from app.models.ivf_batch import IVFBatch
from app.models.opu_session import OPUSession
from app.models.protocol import Protocol
from app.models.recipient import Recipient
from app.models.sire import Sire
from app.models.technician import Technician
from app.models.intake_governance import EmbryoIdentifier


def entity(db, model, organization_id, **values):
    row = db.query(model).filter_by(organization_id=organization_id, **values).first()
    if row is None:
        row = model(organization_id=organization_id, **values)
        db.add(row)
        db.flush()
    return row


def fill_missing(row, **values):
    if row is not None:
        for key, value in values.items():
            if value is not None and getattr(row, key) is None:
                setattr(row, key, value)


def persist_case(db, value, organization_id, username, source_type, source_reference, action="import"):
    recipient = entity(db, Recipient, organization_id, tag_id=value.recipient_tag, farm_location=value.farm_location)
    fill_missing(recipient, cow_or_heifer=value.cow_or_heifer)
    donor = entity(db, Donor, organization_id, tag_id=value.donor_tag) if value.donor_tag else None
    sire = entity(db, Sire, organization_id, name=value.sire_name) if value.sire_name else None
    fill_missing(donor, breed=value.donor_breed)
    fill_missing(sire, breed=value.sire_breed, semen_type=value.semen_type)
    protocol = entity(db, Protocol, organization_id, name=value.protocol_name) if value.protocol_name else None
    tech = entity(db, Technician, organization_id, name=value.technician_name) if value.technician_name else None
    opu, batch = None, None
    if donor and value.opu_date:
        opu = entity(db, OPUSession, organization_id, donor_id=donor.donor_id, opu_date=value.opu_date)
    if opu and value.ivf_date:
        batch = entity(db, IVFBatch, organization_id, opu_id=opu.opu_id, ivf_date=value.ivf_date, sire_id=sire.sire_id if sire else None)
        fill_missing(batch, culture_media=value.culture_media)
    embryo = Embryo(organization_id=organization_id, donor_id=donor.donor_id if donor else None,
        sire_id=sire.sire_id if sire else None, stage=value.embryo_stage, grade=value.embryo_grade,
        fresh_or_frozen=value.fresh_or_frozen, opu_date=value.opu_date, freezing_date=value.freezing_date,
        opu_id=opu.opu_id if opu else None, ivf_batch_id=batch.ivf_batch_id if batch else None)
    db.add(embryo)
    db.flush()
    if value.embryo_identifier:
        db.add(EmbryoIdentifier(organization_id=organization_id, identifier=value.embryo_identifier, embryo_id=embryo.embryo_id))
        db.flush()
    transfer = ETTransfer(organization_id=organization_id, embryo_id=embryo.embryo_id, recipient_id=recipient.recipient_id,
        protocol_id=protocol.protocol_id if protocol else None, technician_id=tech.technician_id if tech else None,
        **value.model_dump(include={"et_number", "et_date", "farm_location", "bc_score", "cl_measure_mm", "cl_side", "heat_observed", "pc1_date", "pc1_result", "pc2_date", "pc2_result"}))
    db.add(transfer)
    db.flush()
    data = value.model_dump(mode="json")
    db.add(CaseMetadata(transfer_id=transfer.transfer_id, organization_id=organization_id, data=data,
        source_type=source_type, source_reference=source_reference, version=1, updated_by=username))
    db.add(CaseAudit(transfer_id=transfer.transfer_id, organization_id=organization_id, actor=username, action=action,
        details={"version": 1, "source_type": source_type, "source_reference": source_reference, "record": data}))
    return transfer
