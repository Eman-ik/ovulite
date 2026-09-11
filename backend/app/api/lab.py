"""Laboratory workflow: oocyte grading, IVM, culture timeline, embryo inventory.

Writes are restricted to ``LAB_WRITE_ROLES``; reads are open to any
authenticated role, matching the other clinical routers.

One thing to keep in mind reading anything here that joins through
``ivf_batches``: only 420 of this dataset's 489 embryos carry an
``ivf_batch_id``, and the 69 that do not are not missing at random — they run
36.2% pregnancy against 27.3% for the linked ones. Any rate computed across
that join is therefore biased, so the endpoints below report coverage rather
than presenting such a rate as if it covered everything.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import LAB_WRITE_ROLES, get_current_user, require_role
from app.database import get_db
from app.models.donor import Donor
from app.models.embryo import Embryo
from app.models.embryo_observation import EmbryoObservation, ObservationStageLabel
from app.models.et_transfer import ETTransfer
from app.models.ivf_batch import IVFBatch
from app.models.ivm_batch import IVMBatch
from app.models.opu_session import OPUSession
from app.models.technician import Technician
from app.models.user import User
from app.schemas.lab import (
    EmbryoObservationCreate,
    EmbryoObservationResponse,
    EmbryoObservationUpdate,
    EmbryoTimeline,
    InventoryResponse,
    InventoryRow,
    InventorySummary,
    IVMBatchCreate,
    IVMBatchResponse,
    IVMBatchUpdate,
    LabBoardResponse,
    LabCount,
    OocyteGradeSummary,
    OocyteGradeUpdate,
    StatusChange,
    WorkflowStage,
)

router = APIRouter()

# An embryo is gradeable from about day 6. Used to estimate "pending grading"
# from dates, since there is no explicit "awaiting grade" flag.
GRADING_WINDOW_DAYS = 14


def _owned_embryo(db: Session, embryo_id: int, org_id: int) -> Embryo:
    embryo = (
        db.query(Embryo)
        .filter(Embryo.embryo_id == embryo_id, Embryo.organization_id == org_id)
        .first()
    )
    if embryo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Embryo not found in your organization")
    return embryo


def _owned_opu(db: Session, opu_id: int, org_id: int) -> OPUSession:
    session = (
        db.query(OPUSession)
        .filter(OPUSession.opu_id == opu_id, OPUSession.organization_id == org_id)
        .first()
    )
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "OPU session not found in your organization")
    return session


def _ivm_response(batch: IVMBatch) -> IVMBatchResponse:
    rate = None
    if batch.oocytes_in and batch.mature_oocytes_out is not None:
        rate = round(batch.mature_oocytes_out / batch.oocytes_in * 100, 1)
    return IVMBatchResponse(
        **{c.name: getattr(batch, c.name) for c in IVMBatch.__table__.columns},
        embryologist_name=batch.embryologist.name if batch.embryologist else None,
        maturation_rate_pct=rate,
    )


def _observation_response(obs: EmbryoObservation) -> EmbryoObservationResponse:
    return EmbryoObservationResponse(
        **{c.name: getattr(obs, c.name) for c in EmbryoObservation.__table__.columns},
        stage_label=ObservationStageLabel.LABELS.get(obs.stage) if obs.stage else None,
        embryologist_name=obs.embryologist.name if obs.embryologist else None,
    )


# ── Lab board ────────────────────────────────────────────


@router.get("/board", response_model=LabBoardResponse)
def lab_board(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LabBoardResponse:
    """What is happening in the laboratory today, plus the workflow totals.

    Counts derived from dates rather than recorded state are flagged
    ``is_estimated``; a workflow stage whose backing field is entirely
    unrecorded reports ``count: null`` with the reason, rather than 0.
    """
    org_id = current_user.organization_id
    today = date.today()

    opu_today = (
        db.query(OPUSession)
        .filter(OPUSession.organization_id == org_id, OPUSession.opu_date == today)
        .all()
    )
    donors_today = len({s.donor_id for s in opu_today})
    oocytes_today = sum(s.oocytes_recovered or 0 for s in opu_today)

    ivf_today = (
        db.query(IVFBatch)
        .filter(IVFBatch.organization_id == org_id, IVFBatch.ivf_date == today)
        .count()
    )
    ivm_active = (
        db.query(IVMBatch)
        .filter(
            IVMBatch.organization_id == org_id,
            IVMBatch.ivm_date >= today - timedelta(days=2),
            IVMBatch.mature_oocytes_out.is_(None),
        )
        .count()
    )

    in_culture = (
        db.query(Embryo)
        .filter(Embryo.organization_id == org_id, Embryo.status == "In Culture")
        .count()
    )
    pending_grading = (
        db.query(Embryo)
        .filter(
            Embryo.organization_id == org_id,
            Embryo.grade.is_(None),
            Embryo.opu_date.isnot(None),
            Embryo.opu_date >= today - timedelta(days=GRADING_WINDOW_DAYS),
        )
        .count()
    )
    frozen = (
        db.query(Embryo).filter(Embryo.organization_id == org_id, Embryo.status == "Frozen").count()
    )
    transferable = (
        db.query(Embryo)
        .filter(Embryo.organization_id == org_id, Embryo.status == "Transferable")
        .count()
    )

    counts = [
        LabCount(key="opu_sessions_today", label="OPU Sessions Today", count=len(opu_today),
                 basis="opu_sessions dated today"),
        LabCount(key="donors_today", label="Donors Aspirated Today", count=donors_today,
                 basis="Distinct donors across today's OPU sessions"),
        LabCount(key="oocytes_today", label="Oocytes Collected Today", count=oocytes_today,
                 basis="Sum of oocytes_recovered on today's OPU sessions"),
        LabCount(key="ivm_active", label="Cohorts in IVM", count=ivm_active, is_estimated=True,
                 basis="IVM batches started in the last 2 days with no maturation result yet"),
        LabCount(key="ivf_today", label="IVF Batches Today", count=ivf_today,
                 basis="ivf_batches dated today"),
        LabCount(key="in_culture", label="Embryos In Culture", count=in_culture,
                 basis="Embryos with status 'In Culture'"),
        LabCount(key="pending_grading", label="Pending Grading", count=pending_grading,
                 is_estimated=True,
                 basis=f"Embryos with no grade and an OPU date in the last {GRADING_WINDOW_DAYS} days"),
        LabCount(key="transferable", label="Transferable", count=transferable,
                 basis="Embryos with status 'Transferable'"),
        LabCount(key="frozen", label="Frozen", count=frozen,
                 basis="Embryos with status 'Frozen'"),
    ]

    # The production workflow, end to end. A stage whose column is entirely
    # null says so instead of reporting zero — a zero here would read as "we
    # produced no blastocysts", which is a very different claim.
    def totals(column) -> tuple[int | None, str | None]:
        recorded = db.query(func.count(column)).filter(IVFBatch.organization_id == org_id).scalar()
        if not recorded:
            return None, "Never recorded in this dataset"
        return (
            db.query(func.coalesce(func.sum(column), 0))
            .filter(IVFBatch.organization_id == org_id)
            .scalar(),
            None,
        )

    opu_total = (
        db.query(func.coalesce(func.sum(OPUSession.oocytes_recovered), 0))
        .filter(OPUSession.organization_id == org_id)
        .scalar()
    )
    opu_recorded = (
        db.query(func.count(OPUSession.oocytes_recovered))
        .filter(OPUSession.organization_id == org_id)
        .scalar()
    )
    mature, mature_reason = totals(IVFBatch.mature_oocytes)
    cleaved, cleaved_reason = totals(IVFBatch.cleaved_embryos)
    blasts, blasts_reason = totals(IVFBatch.blastocysts)

    embryo_total = db.query(Embryo).filter(Embryo.organization_id == org_id).count()
    transferred = (
        db.query(Embryo).filter(Embryo.organization_id == org_id, Embryo.status == "Transferred").count()
    )

    workflow = [
        WorkflowStage(
            label="Oocytes Recovered",
            count=opu_total if opu_recorded else None,
            unavailable_reason=None if opu_recorded else "Never recorded in this dataset",
        ),
        WorkflowStage(label="Mature (IVM)", count=mature, unavailable_reason=mature_reason),
        WorkflowStage(label="Cleaved", count=cleaved, unavailable_reason=cleaved_reason),
        WorkflowStage(label="Blastocysts", count=blasts, unavailable_reason=blasts_reason),
        WorkflowStage(label="Embryos Recorded", count=embryo_total),
        WorkflowStage(label="Transferred", count=transferred),
    ]

    missing = [w.label for w in workflow if w.count is None]
    return LabBoardResponse(
        as_of=today,
        counts=counts,
        workflow=workflow,
        note=(
            "Counts marked 'est.' are inferred from dates rather than recorded state. "
            + (
                f"{', '.join(missing)} cannot be shown: those columns are null for every row in "
                "this dataset, so a zero would assert something the data does not say."
                if missing
                else "Every workflow stage has recorded data."
            )
        ),
    )


# ── Embryo inventory ─────────────────────────────────────


@router.get("/inventory", response_model=InventoryResponse)
def inventory(
    status_filter: str | None = Query(None, alias="status"),
    donor_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InventoryResponse:
    """The embryo bank, with a status breakdown over the whole filtered set.

    The summary is computed before pagination, so the counts describe the
    inventory rather than the current page.
    """
    org_id = current_user.organization_id
    base = (
        db.query(Embryo)
        .options(joinedload(Embryo.donor), joinedload(Embryo.sire))
        .filter(Embryo.organization_id == org_id)
    )
    if donor_id is not None:
        base = base.filter(Embryo.donor_id == donor_id)

    summary_rows = (
        base.with_entities(Embryo.status, func.count(Embryo.embryo_id)).group_by(Embryo.status).all()
    )
    summary = [InventorySummary(status=s, count=c) for s, c in summary_rows]

    if status_filter:
        base = base.filter(Embryo.status == status_filter)

    total = base.count()
    rows = (
        base.order_by(Embryo.embryo_id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    embryo_ids = [e.embryo_id for e in rows]
    transfers = {
        t.embryo_id: t.transfer_id
        for t in db.query(ETTransfer).filter(ETTransfer.embryo_id.in_(embryo_ids)).all()
    } if embryo_ids else {}
    obs_counts = {
        eid: n
        for eid, n in (
            db.query(EmbryoObservation.embryo_id, func.count(EmbryoObservation.observation_id))
            .filter(EmbryoObservation.embryo_id.in_(embryo_ids))
            .group_by(EmbryoObservation.embryo_id)
            .all()
        )
    } if embryo_ids else {}

    return InventoryResponse(
        rows=[
            InventoryRow(
                embryo_id=e.embryo_id,
                donor_tag=e.donor.tag_id if e.donor else None,
                sire_name=e.sire.name if e.sire else None,
                opu_date=e.opu_date,
                stage=e.stage,
                grade=e.grade,
                fresh_or_frozen=e.fresh_or_frozen,
                cane_number=e.cane_number,
                freezing_date=e.freezing_date,
                status=e.status,
                transfer_id=transfers.get(e.embryo_id),
                observation_count=obs_counts.get(e.embryo_id, 0),
            )
            for e in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
        summary=sorted(summary, key=lambda s: -s.count),
        note=(
            "Status is the embryo's position in the lab, distinct from its grade. Every embryo "
            "imported from the historical ET dataset is 'Transferred', because that dataset only "
            "contains embryos that were transferred — the other statuses appear as embryos are "
            "entered through the lab workflow."
        ),
    )


@router.patch("/embryos/{embryo_id}/status", response_model=InventoryRow)
def set_status(
    embryo_id: int,
    payload: StatusChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*LAB_WRITE_ROLES)),
) -> InventoryRow:
    """Move an embryo through the lifecycle.

    'Discarded' requires a reason: an embryo removed from the bank without one
    is unauditable, and this is the row a later review would need.
    """
    embryo = _owned_embryo(db, embryo_id, current_user.organization_id)

    if payload.status == "Discarded" and not (payload.discarded_reason or embryo.discarded_reason):
        raise HTTPException(422, "discarded_reason is required when discarding an embryo")

    transfer = (
        db.query(ETTransfer).filter(ETTransfer.embryo_id == embryo_id).first()
    )
    if transfer is not None and payload.status != "Transferred":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Embryo is recorded on transfer {transfer.transfer_id}; its status cannot be "
            "changed away from 'Transferred' while that transfer exists",
        )

    embryo.status = payload.status
    if payload.discarded_reason is not None:
        embryo.discarded_reason = payload.discarded_reason
    db.commit()
    db.refresh(embryo)

    return InventoryRow(
        embryo_id=embryo.embryo_id,
        donor_tag=embryo.donor.tag_id if embryo.donor else None,
        sire_name=embryo.sire.name if embryo.sire else None,
        opu_date=embryo.opu_date,
        stage=embryo.stage,
        grade=embryo.grade,
        fresh_or_frozen=embryo.fresh_or_frozen,
        cane_number=embryo.cane_number,
        freezing_date=embryo.freezing_date,
        status=embryo.status,
        transfer_id=transfer.transfer_id if transfer else None,
        observation_count=db.query(EmbryoObservation)
        .filter(EmbryoObservation.embryo_id == embryo_id)
        .count(),
    )


# ── Culture timeline ─────────────────────────────────────


@router.get("/embryos/{embryo_id}/timeline", response_model=EmbryoTimeline)
def timeline(
    embryo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmbryoTimeline:
    embryo = (
        db.query(Embryo)
        .options(
            joinedload(Embryo.donor),
            joinedload(Embryo.sire),
            joinedload(Embryo.observations).joinedload(EmbryoObservation.embryologist),
        )
        .filter(Embryo.embryo_id == embryo_id, Embryo.organization_id == current_user.organization_id)
        .first()
    )
    if embryo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Embryo not found in your organization")

    transfer = db.query(ETTransfer).filter(ETTransfer.embryo_id == embryo_id).first()
    observations = sorted(embryo.observations, key=lambda o: o.day_number)

    return EmbryoTimeline(
        embryo_id=embryo.embryo_id,
        donor_tag=embryo.donor.tag_id if embryo.donor else None,
        sire_name=embryo.sire.name if embryo.sire else None,
        status=embryo.status,
        final_stage=embryo.stage,
        final_grade=embryo.grade,
        fresh_or_frozen=embryo.fresh_or_frozen,
        observations=[_observation_response(o) for o in observations],
        transfer_id=transfer.transfer_id if transfer else None,
        note=(
            "Observations are the culture record; stage and grade on the embryo itself are its "
            "final assessment. Historical embryos have no observations — the timeline was not "
            "captured before this feature existed, and an empty timeline is not an arrest."
        ),
    )


@router.post(
    "/embryos/{embryo_id}/observations",
    response_model=EmbryoObservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_observation(
    embryo_id: int,
    payload: EmbryoObservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*LAB_WRITE_ROLES)),
) -> EmbryoObservationResponse:
    _owned_embryo(db, embryo_id, current_user.organization_id)
    duplicate = (
        db.query(EmbryoObservation)
        .filter(
            EmbryoObservation.embryo_id == embryo_id,
            EmbryoObservation.day_number == payload.day_number,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Day {payload.day_number} is already recorded for this embryo — edit it instead",
        )
    observation = EmbryoObservation(
        embryo_id=embryo_id, organization_id=current_user.organization_id, **payload.model_dump()
    )
    db.add(observation)
    db.commit()
    db.refresh(observation)
    return _observation_response(observation)


@router.patch("/observations/{observation_id}", response_model=EmbryoObservationResponse)
def update_observation(
    observation_id: int,
    payload: EmbryoObservationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*LAB_WRITE_ROLES)),
) -> EmbryoObservationResponse:
    observation = (
        db.query(EmbryoObservation)
        .filter(
            EmbryoObservation.observation_id == observation_id,
            EmbryoObservation.organization_id == current_user.organization_id,
        )
        .first()
    )
    if observation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Observation not found in your organization")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(observation, field, value)
    db.commit()
    db.refresh(observation)
    return _observation_response(observation)


# ── Oocyte grading and IVM, per recovery session ─────────


@router.get("/opu-sessions/{opu_id}/processing", response_model=OocyteGradeSummary)
def processing(
    opu_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OocyteGradeSummary:
    """Oocyte grading and IVM for one recovery session."""
    session = (
        db.query(OPUSession)
        .options(joinedload(OPUSession.donor), joinedload(OPUSession.ivm_batches))
        .filter(
            OPUSession.opu_id == opu_id,
            OPUSession.organization_id == current_user.organization_id,
        )
        .first()
    )
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "OPU session not found in your organization")

    graded = sum(
        v or 0
        for v in (
            session.grade_a_oocytes,
            session.grade_b_oocytes,
            session.grade_c_oocytes,
            session.degenerated_oocytes,
        )
    )
    return OocyteGradeSummary(
        opu_id=session.opu_id,
        donor_tag=session.donor.tag_id if session.donor else None,
        opu_date=session.opu_date,
        oocytes_recovered=session.oocytes_recovered,
        grade_a_oocytes=session.grade_a_oocytes,
        grade_b_oocytes=session.grade_b_oocytes,
        grade_c_oocytes=session.grade_c_oocytes,
        degenerated_oocytes=session.degenerated_oocytes,
        graded_total=graded,
        # Null rather than a negative when the recovery count itself is
        # missing, which it is for every historical session here.
        ungraded=(session.oocytes_recovered - graded) if session.oocytes_recovered is not None else None,
        ivm_batches=[_ivm_response(b) for b in session.ivm_batches],
    )


@router.post(
    "/opu-sessions/{opu_id}/ivm-batches",
    response_model=IVMBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ivm_batch(
    opu_id: int,
    payload: IVMBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*LAB_WRITE_ROLES)),
) -> IVMBatchResponse:
    _owned_opu(db, opu_id, current_user.organization_id)
    values = payload.model_dump()
    if values.get("embryologist_id") is not None:
        exists = (
            db.query(Technician)
            .filter(
                Technician.technician_id == values["embryologist_id"],
                Technician.organization_id == current_user.organization_id,
            )
            .first()
        )
        if not exists:
            raise HTTPException(422, "embryologist_id does not identify a technician in your organization")

    batch = IVMBatch(opu_id=opu_id, organization_id=current_user.organization_id, **values)
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return _ivm_response(batch)


@router.patch("/ivm-batches/{ivm_batch_id}", response_model=IVMBatchResponse)
def update_ivm_batch(
    ivm_batch_id: int,
    payload: IVMBatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*LAB_WRITE_ROLES)),
) -> IVMBatchResponse:
    batch = (
        db.query(IVMBatch)
        .filter(
            IVMBatch.ivm_batch_id == ivm_batch_id,
            IVMBatch.organization_id == current_user.organization_id,
        )
        .first()
    )
    if batch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "IVM batch not found in your organization")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(batch, field, value)
    db.commit()
    db.refresh(batch)
    return _ivm_response(batch)


@router.get("/donors/{donor_id}/summary")
def donor_summary(
    donor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recovery and embryo history for one donor.

    Deliberately returns counts and rates with their denominators rather than
    a single composite "donor score": weighting recovery, blastocyst rate and
    pregnancy rate into one number would be an invented metric, and this
    dataset cannot even supply the blastocyst term.
    """
    org_id = current_user.organization_id
    donor = (
        db.query(Donor).filter(Donor.donor_id == donor_id, Donor.organization_id == org_id).first()
    )
    if donor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Donor not found in your organization")

    sessions = (
        db.query(OPUSession)
        .filter(OPUSession.organization_id == org_id, OPUSession.donor_id == donor_id)
        .all()
    )
    embryos = (
        db.query(Embryo).filter(Embryo.organization_id == org_id, Embryo.donor_id == donor_id).all()
    )
    embryo_ids = [e.embryo_id for e in embryos]
    transfers = (
        db.query(ETTransfer).filter(ETTransfer.embryo_id.in_(embryo_ids)).all() if embryo_ids else []
    )
    resolved = [t for t in transfers if (t.pc1_result or "").strip() in ("Pregnant", "Open")]
    pregnant = sum(1 for t in resolved if t.pc1_result == "Pregnant")

    recovered = [s.oocytes_recovered for s in sessions if s.oocytes_recovered is not None]

    return {
        "donor_id": donor.donor_id,
        "tag_id": donor.tag_id,
        "breed": donor.breed,
        "age_years": donor.age_years,
        "parity": donor.parity,
        "reproductive_status": donor.reproductive_status,
        "opu_sessions": len(sessions),
        "oocytes_recovered_total": sum(recovered) if recovered else None,
        "oocytes_recovered_sessions_with_data": len(recovered),
        "mean_oocytes_per_session": round(sum(recovered) / len(recovered), 1) if recovered else None,
        "embryos": len(embryos),
        "transfers": len(transfers),
        "transfers_with_outcome": len(resolved),
        "pregnancies": pregnant,
        "pregnancy_rate_pct": round(pregnant / len(resolved) * 100, 1) if len(resolved) >= 5 else None,
        "note": (
            "No composite score is reported: weighting recovery, blastocyst and pregnancy rates "
            "into one number would be an invented metric, and blastocyst counts are null for "
            "every batch in this dataset. Pregnancy rate is withheld below 5 resolved transfers."
        ),
    }


@router.patch("/opu-sessions/{opu_id}/oocyte-grades", response_model=OocyteGradeSummary)
def set_oocyte_grades(
    opu_id: int,
    payload: OocyteGradeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*LAB_WRITE_ROLES)),
) -> OocyteGradeSummary:
    """Record the oocyte grade tally for a recovery session.

    A focused endpoint rather than a full PUT on the session: grading happens
    after recovery, often by a different person, and making the caller resend
    donor_id and opu_date to change four counts invites clobbering a field
    that someone else edited in between.

    A partial tally is accepted — grading is frequently done in two passes.
    Only a tally exceeding the oocytes recovered is rejected, and only when
    that total is itself recorded.
    """
    session = _owned_opu(db, opu_id, current_user.organization_id)

    values = payload.model_dump(exclude_unset=True)
    for field, value in values.items():
        setattr(session, field, value)

    if session.oocytes_recovered is not None:
        graded = sum(
            v or 0
            for v in (
                session.grade_a_oocytes,
                session.grade_b_oocytes,
                session.grade_c_oocytes,
                session.degenerated_oocytes,
            )
        )
        if graded > session.oocytes_recovered:
            db.rollback()
            raise HTTPException(
                422,
                f"Graded oocytes ({graded}) exceed oocytes recovered ({session.oocytes_recovered})",
            )

    db.commit()
    db.refresh(session)
    return processing(opu_id, db, current_user)
