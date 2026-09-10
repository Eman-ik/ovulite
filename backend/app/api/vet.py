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

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import ET_WRITE_ROLES, get_current_user, require_role
from app.database import get_db
from app.models.calving_record import CalvingRecord
from app.models.et_transfer import ETTransfer
from app.models.pregnancy_check import PregnancyCheck
from app.models.recipient import Recipient
from app.models.recipient_evaluation import RecipientEvaluation
from app.models.technician import Technician
from app.models.user import User
from app.schemas.vet import (
    CalvingRecordCreate,
    CalvingRecordResponse,
    CalvingRecordUpdate,
    PregnancyCheckCreate,
    PregnancyCheckResponse,
    PregnancyCheckUpdate,
    RecipientEvaluationCreate,
    RecipientEvaluationResponse,
    RecipientEvaluationUpdate,
    RetentionResponse,
    RetentionStage,
    TransferOutcomeChain,
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
