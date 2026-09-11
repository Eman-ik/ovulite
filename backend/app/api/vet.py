"""Veterinarian / ET workflow: screening, pregnancy diagnosis, calving.

Writes are restricted to ``ET_WRITE_ROLES``; reads are open to any
authenticated role, matching the split used by the other clinical routers.

The one piece of coupling worth stating plainly: creating or editing a
pregnancy check keeps ``et_transfers.pc1_result``/``pc1_date`` in sync with
the earliest check for that transfer. Those columns are read by the
dashboard, the research surface, the analytics pipeline and the ML feature
builder, so they cannot simply be abandoned — but they are a derived view,
not a second place to record a diagnosis.
"""

from dataclasses import asdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import ET_WRITE_ROLES, get_current_user, require_role
from app.database import get_db
from app.models.calving_record import CalvingRecord
from app.models.et_transfer import ETTransfer
from app.models.pregnancy_check import PregnancyCheck
from app.models.protocol import Protocol
from app.models.protocol_log import ProtocolLog
from app.models.protocol_step import ProtocolStep
from app.models.recipient import Recipient
from app.models.recipient_evaluation import RecipientEvaluation
from app.models.synchronization_enrollment import SynchronizationEnrollment
from app.models.technician import Technician
from app.models.user import User
from app.services.synchronization import build_schedule
from app.schemas.vet import (
    BoardCount,
    CalvingRecordCreate,
    CalvingRecordResponse,
    CalvingRecordUpdate,
    PregnancyCheckCreate,
    PregnancyCheckResponse,
    PregnancyCheckUpdate,
    RecipientEvaluationCreate,
    RecipientEvaluationResponse,
    RecipientEvaluationUpdate,
    EnrollmentCreate,
    EnrollmentScheduleResponse,
    EnrollmentUpdate,
    ProtocolStepCreate,
    ProtocolStepResponse,
    ProtocolStepUpdate,
    RetentionResponse,
    RetentionStage,
    TransferOutcomeChain,
    TreatmentLogCreate,
    VetBoardResponse,
)

router = APIRouter()

# A bovine pregnancy check outside this window is a data-entry error, not a
# late check. Migration 013's backfill surfaced 7 such rows (5 dated before
# their own transfer). Flagged on read rather than rejected on write, so an
# existing bad row stays visible instead of becoming uneditable.
PLAUSIBLE_CHECK_WINDOW = (0, 120)

# Nominal diagnosis milestones, used to bucket checks for retention. Bounds
# are midpoints between the conventional day-28/45/60 checks.
RETENTION_STAGES = (
    ("Day 28 (initial)", 0, 36),
    ("Day 45 (confirm)", 37, 52),
    ("Day 60+ (ongoing)", 53, 120),
)

# Same guard as the research surface: below this, a proportion is reported as
# null rather than as a percentage computed from a handful of animals.
MIN_RETENTION_N = 5


def _owned_transfer(db: Session, transfer_id: int, org_id: int) -> ETTransfer:
    transfer = (
        db.query(ETTransfer)
        .filter(ETTransfer.transfer_id == transfer_id, ETTransfer.organization_id == org_id)
        .first()
    )
    if transfer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transfer not found in your organization")
    return transfer


def _owned_recipient(db: Session, recipient_id: int, org_id: int) -> Recipient:
    recipient = (
        db.query(Recipient)
        .filter(Recipient.recipient_id == recipient_id, Recipient.organization_id == org_id)
        .first()
    )
    if recipient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipient not found in your organization")
    return recipient



def _owned_protocol(db: Session, protocol_id: int, org_id: int) -> Protocol:
    protocol = (
        db.query(Protocol)
        .filter(Protocol.protocol_id == protocol_id, Protocol.organization_id == org_id)
        .first()
    )
    if protocol is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Protocol not found in your organization")
    return protocol


def _owned_step(db: Session, step_id: int, org_id: int) -> ProtocolStep:
    step = (
        db.query(ProtocolStep)
        .filter(ProtocolStep.step_id == step_id, ProtocolStep.organization_id == org_id)
        .first()
    )
    if step is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Protocol step not found in your organization")
    return step


def _owned_enrollment(db: Session, enrollment_id: int, org_id: int) -> SynchronizationEnrollment:
    enrollment = (
        db.query(SynchronizationEnrollment)
        .options(
            joinedload(SynchronizationEnrollment.recipient),
            joinedload(SynchronizationEnrollment.protocol),
            joinedload(SynchronizationEnrollment.logs),
        )
        .filter(
            SynchronizationEnrollment.enrollment_id == enrollment_id,
            SynchronizationEnrollment.organization_id == org_id,
        )
        .first()
    )
    if enrollment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Enrollment not found in your organization")
    return enrollment


def _steps_by_protocol(db: Session, org_id: int) -> dict[int, list[ProtocolStep]]:
    """All step templates for the org, grouped — one query for the whole board."""
    grouped: dict[int, list[ProtocolStep]] = {}
    for step in db.query(ProtocolStep).filter(ProtocolStep.organization_id == org_id).all():
        grouped.setdefault(step.protocol_id, []).append(step)
    return grouped


def _schedule_response(
    db: Session, enrollment: SynchronizationEnrollment, org_id: int
) -> EnrollmentScheduleResponse:
    steps = (
        db.query(ProtocolStep)
        .filter(
            ProtocolStep.protocol_id == enrollment.protocol_id,
            ProtocolStep.organization_id == org_id,
        )
        .all()
    )
    return EnrollmentScheduleResponse(**asdict(build_schedule(enrollment, steps)))


def _check_response(check: PregnancyCheck) -> PregnancyCheckResponse:
    low, high = PLAUSIBLE_CHECK_WINDOW
    offset = check.days_post_transfer
    return PregnancyCheckResponse(
        check_id=check.check_id,
        transfer_id=check.transfer_id,
        check_date=check.check_date,
        days_post_transfer=offset,
        result=check.result,
        method=check.method,
        technician_id=check.technician_id,
        technician_name=check.technician.name if check.technician else None,
        notes=check.notes,
        implausible_offset=offset is not None and not (low <= offset <= high),
        created_at=check.created_at,
        updated_at=check.updated_at,
    )


def _sync_pc1(db: Session, transfer: ETTransfer) -> None:
    """Mirror the earliest check onto the legacy pc1 columns.

    Called after every write. Keeps the denormalised view consistent without
    making callers of those columns aware the new table exists.
    """
    earliest = (
        db.query(PregnancyCheck)
        .filter(PregnancyCheck.transfer_id == transfer.transfer_id)
        .order_by(PregnancyCheck.check_date)
        .first()
    )
    if earliest is None:
        # Deliberately leaves pc1_* alone rather than nulling it. Migration
        # 013 could only backfill transfers that had a pc1_*date*, and 180 of
        # this dataset's rows carry a pc1_result with no date — so "no checks"
        # does not imply "no diagnosis was ever recorded". Clearing the column
        # here would destroy those results the first time someone added and
        # then removed a check.
        return

    transfer.pc1_date = earliest.check_date
    # "Lost" has no legacy equivalent; the earliest check is never a loss in
    # practice, but map it to Open rather than writing a value the legacy
    # readers' normaliser would silently drop.
    transfer.pc1_result = "Open" if earliest.result == "Lost" else earliest.result


# ── Recipient evaluations ────────────────────────────────


@router.get("/recipients/{recipient_id}/evaluations", response_model=list[RecipientEvaluationResponse])
def list_evaluations(
    recipient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Screening history for one recipient, newest first."""
    _owned_recipient(db, recipient_id, current_user.organization_id)
    rows = (
        db.query(RecipientEvaluation)
        .options(joinedload(RecipientEvaluation.technician), joinedload(RecipientEvaluation.recipient))
        .filter(
            RecipientEvaluation.recipient_id == recipient_id,
            RecipientEvaluation.organization_id == current_user.organization_id,
        )
        .order_by(RecipientEvaluation.evaluation_date.desc())
        .all()
    )
    return [
        RecipientEvaluationResponse(
            **{c.name: getattr(r, c.name) for c in RecipientEvaluation.__table__.columns},
            recipient_tag=r.recipient.tag_id if r.recipient else None,
            technician_name=r.technician.name if r.technician else None,
        )
        for r in rows
    ]


@router.post(
    "/recipients/{recipient_id}/evaluations",
    response_model=RecipientEvaluationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_evaluation(
    recipient_id: int,
    payload: RecipientEvaluationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ET_WRITE_ROLES)),
):
    """Record a pre-transfer assessment.

    Valid with no transfer attached — that is the screened-and-rejected case,
    and losing it would make screening effectiveness unmeasurable.
    """
    _owned_recipient(db, recipient_id, current_user.organization_id)
    values = payload.model_dump()

    if values.get("transfer_id") is not None:
        _owned_transfer(db, values["transfer_id"], current_user.organization_id)
    if values.get("technician_id") is not None:
        exists = (
            db.query(Technician)
            .filter(
                Technician.technician_id == values["technician_id"],
                Technician.organization_id == current_user.organization_id,
            )
            .first()
        )
        if not exists:
            raise HTTPException(422, "technician_id does not identify a technician in your organization")

    evaluation = RecipientEvaluation(
        recipient_id=recipient_id, organization_id=current_user.organization_id, **values
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return RecipientEvaluationResponse(
        **{c.name: getattr(evaluation, c.name) for c in RecipientEvaluation.__table__.columns},
        recipient_tag=evaluation.recipient.tag_id if evaluation.recipient else None,
        technician_name=evaluation.technician.name if evaluation.technician else None,
    )


@router.patch("/evaluations/{evaluation_id}", response_model=RecipientEvaluationResponse)
def update_evaluation(
    evaluation_id: int,
    payload: RecipientEvaluationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ET_WRITE_ROLES)),
):
    evaluation = (
        db.query(RecipientEvaluation)
        .filter(
            RecipientEvaluation.evaluation_id == evaluation_id,
            RecipientEvaluation.organization_id == current_user.organization_id,
        )
        .first()
    )
    if evaluation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evaluation not found in your organization")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(evaluation, field, value)
    db.commit()
    db.refresh(evaluation)
    return RecipientEvaluationResponse(
        **{c.name: getattr(evaluation, c.name) for c in RecipientEvaluation.__table__.columns},
        recipient_tag=evaluation.recipient.tag_id if evaluation.recipient else None,
        technician_name=evaluation.technician.name if evaluation.technician else None,
    )


# ── Pregnancy checks ─────────────────────────────────────


@router.get("/transfers/{transfer_id}/pregnancy-checks", response_model=list[PregnancyCheckResponse])
def list_checks(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _owned_transfer(db, transfer_id, current_user.organization_id)
    rows = (
        db.query(PregnancyCheck)
        .options(joinedload(PregnancyCheck.technician))
        .filter(PregnancyCheck.transfer_id == transfer_id)
        .order_by(PregnancyCheck.check_date)
        .all()
    )
    return [_check_response(r) for r in rows]


@router.post(
    "/transfers/{transfer_id}/pregnancy-checks",
    response_model=PregnancyCheckResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_check(
    transfer_id: int,
    payload: PregnancyCheckCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ET_WRITE_ROLES)),
):
    """Record a pregnancy diagnosis.

    ``days_post_transfer`` is computed here from the transfer date rather than
    accepted from the caller, so it cannot disagree with the two dates.
    """
    transfer = _owned_transfer(db, transfer_id, current_user.organization_id)

    duplicate = (
        db.query(PregnancyCheck)
        .filter(
            PregnancyCheck.transfer_id == transfer_id,
            PregnancyCheck.check_date == payload.check_date,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A check already exists for this transfer on that date — edit it instead",
        )

    offset = (payload.check_date - transfer.et_date).days if transfer.et_date else None
    check = PregnancyCheck(
        transfer_id=transfer_id,
        organization_id=current_user.organization_id,
        days_post_transfer=offset,
        **payload.model_dump(),
    )
    db.add(check)
    db.flush()
    _sync_pc1(db, transfer)
    db.commit()
    db.refresh(check)
    return _check_response(check)


@router.patch("/pregnancy-checks/{check_id}", response_model=PregnancyCheckResponse)
def update_check(
    check_id: int,
    payload: PregnancyCheckUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ET_WRITE_ROLES)),
):
    check = (
        db.query(PregnancyCheck)
        .filter(
            PregnancyCheck.check_id == check_id,
            PregnancyCheck.organization_id == current_user.organization_id,
        )
        .first()
    )
    if check is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Check not found in your organization")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(check, field, value)

    transfer = _owned_transfer(db, check.transfer_id, current_user.organization_id)
    if transfer.et_date and check.check_date:
        check.days_post_transfer = (check.check_date - transfer.et_date).days
    db.flush()
    _sync_pc1(db, transfer)
    db.commit()
    db.refresh(check)
    return _check_response(check)


@router.delete("/pregnancy-checks/{check_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_check(
    check_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ET_WRITE_ROLES)),
):
    check = (
        db.query(PregnancyCheck)
        .filter(
            PregnancyCheck.check_id == check_id,
            PregnancyCheck.organization_id == current_user.organization_id,
        )
        .first()
    )
    if check is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Check not found in your organization")
    transfer = _owned_transfer(db, check.transfer_id, current_user.organization_id)
    db.delete(check)
    db.flush()
    _sync_pc1(db, transfer)
    db.commit()


# ── Calving ──────────────────────────────────────────────


@router.post(
    "/transfers/{transfer_id}/calving",
    response_model=CalvingRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_calving(
    transfer_id: int,
    payload: CalvingRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ET_WRITE_ROLES)),
):
    transfer = _owned_transfer(db, transfer_id, current_user.organization_id)
    if transfer.calving_record is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This transfer already has a calving record — edit it instead"
        )

    values = payload.model_dump()
    if values.get("gestation_days") is None and transfer.et_date:
        values["gestation_days"] = (values["calving_date"] - transfer.et_date).days

    record = CalvingRecord(
        transfer_id=transfer_id, organization_id=current_user.organization_id, **values
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.patch("/calving/{calving_id}", response_model=CalvingRecordResponse)
def update_calving(
    calving_id: int,
    payload: CalvingRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ET_WRITE_ROLES)),
):
    record = (
        db.query(CalvingRecord)
        .filter(
            CalvingRecord.calving_id == calving_id,
            CalvingRecord.organization_id == current_user.organization_id,
        )
        .first()
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Calving record not found in your organization")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record


# ── Read models ──────────────────────────────────────────


@router.get("/transfers/{transfer_id}/outcome-chain", response_model=TransferOutcomeChain)
def outcome_chain(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Every diagnosis for one transfer, in order, plus its calving if any."""
    transfer = (
        db.query(ETTransfer)
        .options(
            joinedload(ETTransfer.recipient),
            joinedload(ETTransfer.pregnancy_checks).joinedload(PregnancyCheck.technician),
            joinedload(ETTransfer.calving_record),
        )
        .filter(
            ETTransfer.transfer_id == transfer_id,
            ETTransfer.organization_id == current_user.organization_id,
        )
        .first()
    )
    if transfer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transfer not found in your organization")

    checks = sorted(transfer.pregnancy_checks, key=lambda c: c.check_date)
    if transfer.calving_record:
        current = transfer.calving_record.outcome
    elif checks:
        current = {"Pregnant": "Pregnant (ongoing)", "Open": "Open", "Lost": "Pregnancy lost"}.get(
            checks[-1].result, checks[-1].result
        )
    else:
        current = "No diagnosis recorded"

    return TransferOutcomeChain(
        transfer_id=transfer.transfer_id,
        et_date=transfer.et_date,
        recipient_tag=transfer.recipient.tag_id if transfer.recipient else None,
        checks=[_check_response(c) for c in checks],
        calving=transfer.calving_record,
        current_status=current,
    )


@router.get("/retention", response_model=RetentionResponse)
def retention(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pregnancy retention across diagnosis milestones, then calving.

    Each stage's denominator is transfers that actually have a diagnosis in
    that window — not all transfers — so a stage nobody has checked yet reads
    as absent rather than as a wave of losses.
    """
    query = db.query(PregnancyCheck).join(ETTransfer).filter(
        PregnancyCheck.organization_id == current_user.organization_id
    )
    if date_from:
        query = query.filter(ETTransfer.et_date >= date_from)
    if date_to:
        query = query.filter(ETTransfer.et_date <= date_to)
    checks = query.all()

    # Bucket each transfer's checks by stage. Retention has to follow the same
    # animals: dividing one stage's rate by the previous stage's rate compares
    # two different cohorts and can exceed 100%, which is meaningless.
    by_stage: list[dict[int, PregnancyCheck]] = []
    for _, low, high in RETENTION_STAGES:
        stage_map: dict[int, PregnancyCheck] = {}
        for c in checks:
            offset = c.days_post_transfer
            if offset is None or not (low <= offset <= high):
                continue
            # Keep the earliest check in the window if a transfer has several.
            existing = stage_map.get(c.transfer_id)
            if existing is None or c.check_date < existing.check_date:
                stage_map[c.transfer_id] = c
        by_stage.append(stage_map)

    stages: list[RetentionStage] = []
    for index, (label, _, _) in enumerate(RETENTION_STAGES):
        stage_map = by_stage[index]
        n = len(stage_map)
        pregnant = sum(1 for c in stage_map.values() if c.result == "Pregnant")
        rate = round(pregnant / n * 100, 1) if n >= MIN_RETENTION_N else None

        retained = None
        if index > 0:
            previous = by_stage[index - 1]
            # Transfers pregnant at the previous stage AND re-checked at this
            # one — the only population for which retention is defined.
            paired = [
                tid
                for tid, prev in previous.items()
                if prev.result == "Pregnant" and tid in stage_map
            ]
            if len(paired) >= MIN_RETENTION_N:
                still = sum(1 for tid in paired if stage_map[tid].result == "Pregnant")
                retained = round(still / len(paired) * 100, 1)

        stages.append(
            RetentionStage(
                label=label, n=n, pregnant=pregnant, rate_pct=rate, retained_from_previous_pct=retained
            )
        )

    calvings = (
        db.query(CalvingRecord)
        .filter(CalvingRecord.organization_id == current_user.organization_id)
        .all()
    )
    live_birth = None
    if calvings:
        live = sum(1 for c in calvings if c.outcome == "Live Birth")
        live_birth = RetentionStage(
            label="Live Birth",
            n=len(calvings),
            pregnant=live,
            rate_pct=round(live / len(calvings) * 100, 1) if len(calvings) >= MIN_RETENTION_N else None,
            retained_from_previous_pct=None,
        )

    return RetentionResponse(
        stages=stages,
        live_birth_tracked=bool(calvings),
        live_birth=live_birth,
        note=(
            "Each stage counts only transfers with a diagnosis in that window, so an "
            "unchecked cohort does not appear as a loss. Retention is computed on the "
            "transfers that were pregnant at the previous stage AND re-checked at this one "
            "— dividing one stage's rate by another's would compare different animals and "
            f"can exceed 100%. Rates from fewer than {MIN_RETENTION_N} animals are withheld. "
            + (
                f"Live birth is computed from {len(calvings)} calving records."
                if calvings
                else "Live birth is not yet tracked: no calving records have been entered."
            )
        ),
    )


# ── Protocol step templates ──────────────────────────────


@router.get("/protocols/{protocol_id}/steps", response_model=list[ProtocolStepResponse])
def list_protocol_steps(
    protocol_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The step template for one protocol, in day order.

    An empty list is a real answer: this database's protocol names encode the
    drugs but not the days, so no protocol has a schedule until a vet enters
    one. Ovulite does not guess treatment days.
    """
    _owned_protocol(db, protocol_id, current_user.organization_id)
    return (
        db.query(ProtocolStep)
        .filter(
            ProtocolStep.protocol_id == protocol_id,
            ProtocolStep.organization_id == current_user.organization_id,
        )
        .order_by(ProtocolStep.day_offset, ProtocolStep.step_name)
        .all()
    )


@router.post(
    "/protocols/{protocol_id}/steps",
    response_model=ProtocolStepResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_protocol_step(
    protocol_id: int,
    payload: ProtocolStepCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ET_WRITE_ROLES)),
):
    _owned_protocol(db, protocol_id, current_user.organization_id)
    duplicate = (
        db.query(ProtocolStep)
        .filter(
            ProtocolStep.protocol_id == protocol_id,
            ProtocolStep.day_offset == payload.day_offset,
            ProtocolStep.step_name == payload.step_name,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This protocol already has a step with that name on that day",
        )
    step = ProtocolStep(
        protocol_id=protocol_id, organization_id=current_user.organization_id, **payload.model_dump()
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


@router.patch("/protocol-steps/{step_id}", response_model=ProtocolStepResponse)
def update_protocol_step(
    step_id: int,
    payload: ProtocolStepUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ET_WRITE_ROLES)),
):
    step = _owned_step(db, step_id, current_user.organization_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(step, field, value)
    db.commit()
    db.refresh(step)
    return step


@router.delete("/protocol-steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_protocol_step(
    step_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ET_WRITE_ROLES)),
):
    """Remove a step from the template.

    Refused while treatments have been logged against it: deleting would
    orphan a record of something that was actually administered.
    """
    step = _owned_step(db, step_id, current_user.organization_id)
    logged = db.query(ProtocolLog).filter(ProtocolLog.step_id == step_id).count()
    if logged:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{logged} treatment(s) are logged against this step; it cannot be deleted",
        )
    db.delete(step)
    db.commit()


# ── Enrollments ──────────────────────────────────────────


@router.post(
    "/enrollments", response_model=EnrollmentScheduleResponse, status_code=status.HTTP_201_CREATED
)
def create_enrollment(
    payload: EnrollmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ET_WRITE_ROLES)),
):
    """Place a recipient on a protocol from a start date.

    Returns the derived schedule immediately, so the caller sees the treatment
    days without a second request — and sees at once if the protocol has no
    template defined.
    """
    _owned_recipient(db, payload.recipient_id, current_user.organization_id)
    _owned_protocol(db, payload.protocol_id, current_user.organization_id)

    active = (
        db.query(SynchronizationEnrollment)
        .filter(
            SynchronizationEnrollment.recipient_id == payload.recipient_id,
            SynchronizationEnrollment.organization_id == current_user.organization_id,
            SynchronizationEnrollment.status == "Active",
        )
        .first()
    )
    if active:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Recipient is already on an active enrollment (id {active.enrollment_id}); "
            "complete or withdraw it first",
        )

    enrollment = SynchronizationEnrollment(
        organization_id=current_user.organization_id, status="Active", **payload.model_dump()
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return _schedule_response(db, enrollment, current_user.organization_id)


@router.patch("/enrollments/{enrollment_id}", response_model=EnrollmentScheduleResponse)
def update_enrollment(
    enrollment_id: int,
    payload: EnrollmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ET_WRITE_ROLES)),
):
    enrollment = _owned_enrollment(db, enrollment_id, current_user.organization_id)
    values = payload.model_dump(exclude_unset=True)
    if values.get("transfer_id") is not None:
        _owned_transfer(db, values["transfer_id"], current_user.organization_id)
    if values.get("status") == "Withdrawn" and not (
        values.get("withdrawn_reason") or enrollment.withdrawn_reason
    ):
        raise HTTPException(422, "withdrawn_reason is required when withdrawing an enrollment")
    for field, value in values.items():
        setattr(enrollment, field, value)
    db.commit()
    db.refresh(enrollment)
    return _schedule_response(db, enrollment, current_user.organization_id)


@router.get("/enrollments/{enrollment_id}", response_model=EnrollmentScheduleResponse)
def get_enrollment(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    enrollment = _owned_enrollment(db, enrollment_id, current_user.organization_id)
    return _schedule_response(db, enrollment, current_user.organization_id)


@router.get("/schedule", response_model=list[EnrollmentScheduleResponse])
def schedule_board(
    status_filter: str | None = Query(None, alias="status"),
    overdue_only: bool = Query(False),
    due_within_days: int | None = Query(None, ge=0, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Every enrollment with its derived schedule.

    Defaults to active enrollments, which is what a vet planning the day
    needs; pass ``status`` to see completed or withdrawn ones.
    """
    query = (
        db.query(SynchronizationEnrollment)
        .options(
            joinedload(SynchronizationEnrollment.recipient),
            joinedload(SynchronizationEnrollment.protocol),
            joinedload(SynchronizationEnrollment.logs),
        )
        .filter(SynchronizationEnrollment.organization_id == current_user.organization_id)
        .filter(SynchronizationEnrollment.status == (status_filter or "Active"))
    )

    steps_by_protocol = _steps_by_protocol(db, current_user.organization_id)
    schedules = [build_schedule(e, steps_by_protocol.get(e.protocol_id, [])) for e in query.all()]

    if overdue_only:
        schedules = [s for s in schedules if s.overdue_count > 0]
    if due_within_days is not None:
        schedules = [
            s
            for s in schedules
            if s.next_step is not None and s.next_step.days_from_today <= due_within_days
        ]

    # Soonest action first; enrollments with nothing pending sort last.
    schedules.sort(
        key=lambda s: (
            0 if s.overdue_count else 1,
            s.next_step.days_from_today if s.next_step else 10**6,
        )
    )
    return [EnrollmentScheduleResponse(**asdict(s)) for s in schedules]


@router.get("/board", response_model=VetBoardResponse)
def vet_board(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The counts a veterinarian opens the day with.

    Each count carries the query it came from, so a number can be checked
    rather than trusted.
    """
    org_id = current_user.organization_id
    today = date.today()

    enrollments = (
        db.query(SynchronizationEnrollment)
        .options(
            joinedload(SynchronizationEnrollment.recipient),
            joinedload(SynchronizationEnrollment.protocol),
            joinedload(SynchronizationEnrollment.logs),
        )
        .filter(
            SynchronizationEnrollment.organization_id == org_id,
            SynchronizationEnrollment.status == "Active",
        )
        .all()
    )
    steps_by_protocol = _steps_by_protocol(db, org_id)
    schedules = [
        build_schedule(e, steps_by_protocol.get(e.protocol_id, []), today) for e in enrollments
    ]

    in_sync = len(schedules)
    overdue = sum(1 for s in schedules if s.overdue_count)
    due_today = sum(
        1 for s in schedules if s.next_step is not None and s.next_step.days_from_today == 0
    )
    transfer_due_today = sum(1 for s in schedules if s.transfer_due_date == today)
    unschedulable = [s for s in schedules if not s.has_schedule]

    evaluated_ids = {
        row[0]
        for row in db.query(RecipientEvaluation.recipient_id)
        .filter(RecipientEvaluation.organization_id == org_id)
        .all()
    }
    awaiting_evaluation = sum(
        1
        for s in schedules
        if s.transfer_due_date is not None
        and s.transfer_due_date >= today
        and s.recipient_id not in evaluated_ids
    )

    eligible = (
        db.query(RecipientEvaluation)
        .filter(
            RecipientEvaluation.organization_id == org_id,
            RecipientEvaluation.eligibility.in_(("Excellent", "Acceptable")),
            RecipientEvaluation.transfer_id.is_(None),
        )
        .count()
    )

    transfers_today = (
        db.query(ETTransfer)
        .filter(ETTransfer.organization_id == org_id, ETTransfer.et_date == today)
        .count()
    )

    pd_due = (
        db.query(ETTransfer)
        .outerjoin(PregnancyCheck, PregnancyCheck.transfer_id == ETTransfer.transfer_id)
        .filter(
            ETTransfer.organization_id == org_id,
            ETTransfer.et_date.isnot(None),
            ETTransfer.et_date <= today - timedelta(days=28),
            ETTransfer.et_date >= today - timedelta(days=120),
            PregnancyCheck.check_id.is_(None),
        )
        .count()
    )

    counts = [
        BoardCount(
            key="in_synchronization",
            label="Recipients in synchronization",
            count=in_sync,
            basis="Active synchronization enrollments",
        ),
        BoardCount(
            key="steps_overdue",
            label="Enrollments with an overdue step",
            count=overdue,
            basis="Active enrollments with a step due before today and no treatment logged",
        ),
        BoardCount(
            key="steps_due_today",
            label="Treatments due today",
            count=due_today,
            basis="Active enrollments whose next unlogged step falls on today",
        ),
        BoardCount(
            key="awaiting_cl_evaluation",
            label="Awaiting CL evaluation",
            count=awaiting_evaluation,
            is_estimated=True,
            basis=(
                "Active enrollments with a transfer day still ahead and no recorded evaluation "
                "for that recipient — approximate, since an evaluation is not tied to an enrollment"
            ),
        ),
        BoardCount(
            key="eligible_for_et",
            label="Eligible for ET",
            count=eligible,
            basis="Evaluations graded Excellent or Acceptable that are not yet linked to a transfer",
        ),
        BoardCount(
            key="transfer_day_today",
            label="Scheduled transfer day today",
            count=transfer_due_today,
            basis="Active enrollments whose transfer-day step falls on today",
        ),
        BoardCount(
            key="transfers_recorded_today",
            label="Transfers recorded today",
            count=transfers_today,
            basis="et_transfers dated today",
        ),
        BoardCount(
            key="pregnancy_diagnosis_due",
            label="Pregnancy diagnosis due",
            count=pd_due,
            basis="Transfers 28-120 days old with no pregnancy check recorded",
        ),
    ]

    return VetBoardResponse(
        as_of=today,
        counts=counts,
        protocols_without_steps=sorted({s.protocol_name for s in unschedulable if s.protocol_name}),
        note=(
            "Counts are derived from enrollments, evaluations and transfers as they stand now. "
            + (
                f"{len(unschedulable)} active enrollment(s) are on protocols with no step "
                "template, so no treatment can be scheduled for them until one is defined."
                if unschedulable
                else "Every active enrollment is on a protocol with a defined schedule."
            )
        ),
    )


@router.post(
    "/enrollments/{enrollment_id}/treatments",
    response_model=EnrollmentScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
def log_treatment(
    enrollment_id: int,
    payload: TreatmentLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ET_WRITE_ROLES)),
):
    """Record that a scheduled step was administered, and return the new schedule.

    Returning the whole schedule rather than the log row is deliberate: the
    caller's next question is always "what is due now?", and recomputing it
    here avoids a second request that could observe a different day.

    The drug and dose default to the template's, so the common case — the
    treatment was given as specified — needs only the step and the date. A
    substitution is recorded by passing them explicitly.
    """
    enrollment = _owned_enrollment(db, enrollment_id, current_user.organization_id)
    step = _owned_step(db, payload.step_id, current_user.organization_id)
    if step.protocol_id != enrollment.protocol_id:
        raise HTTPException(
            422, "That step belongs to a different protocol than this enrollment"
        )

    existing = (
        db.query(ProtocolLog)
        .filter(ProtocolLog.enrollment_id == enrollment_id, ProtocolLog.step_id == payload.step_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This step is already recorded for this enrollment",
        )

    db.add(
        ProtocolLog(
            organization_id=current_user.organization_id,
            enrollment_id=enrollment_id,
            step_id=payload.step_id,
            protocol_id=enrollment.protocol_id,
            transfer_id=enrollment.transfer_id,
            step_name=step.step_name,
            step_date=payload.step_date,
            drug_name=payload.drug_name or step.drug_name,
            dosage=payload.dosage or step.dosage,
            notes=payload.notes,
        )
    )
    db.commit()
    db.refresh(enrollment)
    return _schedule_response(db, enrollment, current_user.organization_id)
