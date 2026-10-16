"""Integration tests for the monitoring endpoints (Module 7).

Ported from Inshal's repository, with the fixtures mapped onto this repo's
role model (there is no `technical_staff_headers` here) and every seeded row
given an organization_id, since predictions and transfers are tenant-scoped.

The last test is new and covers the adaptation rather than the upstream code:
drift for one organization must be computed only from that organization's
outcomes. Upstream pooled every row, so this is exactly where a port of it
would go wrong silently.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

import pytest

from app.models.et_transfer import ETTransfer
from app.models.model_metric import ModelMetric
from app.models.organization import Organization
from app.models.prediction import Prediction
from app.models.retrain_job import RetrainJob
from app.models.user import User


def _org_id(db, username: str = "admin") -> int:
    """The organization the seeded admin belongs to."""
    user = db.query(User).filter(User.username == username).first()
    assert user is not None, "admin user was not seeded"
    assert user.organization_id is not None, "admin has no organization"
    return user.organization_id


def _seed_drifting_predictions(
    db,
    organization_id: int,
    model_version: str,
    n_baseline: int = 60,
    n_current: int = 40,
) -> None:
    """Healthy saved history plus a current window whose predictions are wrong
    (pregnant cases get low probabilities), so performance drift fires."""
    now = datetime.utcnow()
    for i in range(3):
        db.add(ModelMetric(
            organization_id=organization_id,
            model_version=model_version, window_label="30d", brier_score=0.15, roc_auc=0.85,
            pr_auc=0.7, win_rate=0.8, sample_size=40,
            metric_date=date.today() - timedelta(days=7 * (i + 1)),
        ))

    def add(i: int, age_days: int, good: bool) -> None:
        pregnant = i % 3 == 0
        transfer = ETTransfer(
            organization_id=organization_id, et_date=date.today() - timedelta(days=age_days + 30),
            pc1_result="Pregnant" if pregnant else "Open", cl_measure_mm=18, heat_day=7,
        )
        db.add(transfer)
        db.flush()
        if good:
            probability = 0.8 if pregnant else 0.2
        else:
            probability = 0.2 if pregnant else 0.8
        db.add(Prediction(
            organization_id=organization_id, transfer_id=transfer.transfer_id, model_name="TEST",
            model_version=model_version, probability=probability,
            predicted_at=now - timedelta(days=age_days),
        ))

    for i in range(n_baseline):
        add(i, 40 + (i % 100), good=True)
    for i in range(n_current):
        add(i, i % 20, good=False)
    db.commit()


def _counts(db, model_version: str) -> tuple[int, int]:
    metrics = db.query(ModelMetric).filter(ModelMetric.model_version == model_version).count()
    jobs = db.query(RetrainJob).filter(RetrainJob.model_version == model_version).count()
    return metrics, jobs


# ── Contract ────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_monitoring_run_requires_auth(client):
    """Unauthenticated requests must be rejected before pipeline logic runs."""
    response = client.post("/monitoring/run")
    assert response.status_code in (401, 403), response.text


@pytest.mark.integration
def test_monitoring_run_triggers_pipeline(client, auth_headers):
    """POST /monitoring/run should compute metrics and return a DriftReport."""
    response = client.post("/monitoring/run", headers=auth_headers)
    assert response.status_code == 200, response.text

    body = response.json()
    for field in (
        "model_version",
        "current_metrics",
        "performance_drift_detected",
        "performance_drift_details",
        "population_drift_detected",
        "population_drift_details",
        "drift_detected",
        "retrain_recommended",
    ):
        assert field in body, f"DriftReport missing field: {field}"

    current = body["current_metrics"]
    assert current["status"] in ("ok", "insufficient_data", "single_class")
    assert isinstance(current["sample_size"], int)


@pytest.mark.integration
def test_monitoring_metrics_contract(client, auth_headers):
    response = client.get("/monitoring/metrics", headers=auth_headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert isinstance(body["metrics"], list)
    assert body["total"] >= len(body["metrics"])

    if body["metrics"]:
        row = body["metrics"][0]
        for field in ("metric_id", "model_version", "sample_size", "metric_date", "created_at"):
            assert field in row, f"ModelMetricOut missing field: {field}"


@pytest.mark.integration
def test_monitoring_drift_contract(client, auth_headers):
    response = client.get("/monitoring/drift", headers=auth_headers)
    assert response.status_code == 200, response.text

    body = response.json()
    # drift_detected must be true only if at least one underlying signal fired.
    if body["drift_detected"]:
        assert body["performance_drift_detected"] or body["population_drift_detected"], (
            "drift_detected=true but neither underlying signal is true -- "
            "the two-independent-signals rule is violated"
        )


@pytest.mark.integration
def test_monitoring_retrain_jobs_contract(client, auth_headers):
    response = client.get("/monitoring/retrain-jobs", headers=auth_headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert "jobs" in body and "total" in body
    if body["jobs"]:
        job = body["jobs"][0]
        for field in ("job_id", "reason", "status", "triggered_by", "triggered_at"):
            assert field in job, f"RetrainJobOut missing field: {field}"
        assert job["status"] in ("PENDING", "RUNNING", "COMPLETE", "FAILED")


@pytest.mark.integration
def test_acknowledge_rejects_invalid_status(client, auth_headers):
    """new_status is validated against the allowed set before any DB work."""
    response = client.post(
        "/monitoring/retrain-jobs/1/acknowledge",
        headers=auth_headers,
        params={"new_status": "NOT_A_REAL_STATUS"},
    )
    assert response.status_code == 400, response.text


# ── Read-only GET, and the retrain rate limit ───────────────────────────


@pytest.mark.integration
def test_get_drift_never_writes(client, db_session, auth_headers):
    model_version = f"test_{uuid.uuid4().hex[:8]}"
    _seed_drifting_predictions(db_session, _org_id(db_session), model_version)
    before = _counts(db_session, model_version)

    for _ in range(3):
        response = client.get(
            f"/monitoring/drift?model_version={model_version}", headers=auth_headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["drift_detected"] is True
        assert body["persisted"] is False
        assert body["retrain_job_id"] is None

    assert _counts(db_session, model_version) == before, (
        "a GET must not create metric rows or retrain jobs"
    )


@pytest.mark.integration
def test_run_persists_one_snapshot_per_day_and_one_open_job(client, db_session, auth_headers):
    model_version = f"test_{uuid.uuid4().hex[:8]}"
    _seed_drifting_predictions(db_session, _org_id(db_session), model_version)
    metrics_before, _ = _counts(db_session, model_version)

    first = client.post(f"/monitoring/run?model_version={model_version}", headers=auth_headers)
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["persisted"] is True
    assert first_body["retrain_job_id"] is not None

    second = client.post(
        f"/monitoring/run?model_version={model_version}", headers=auth_headers
    ).json()
    assert second["retrain_job_id"] == first_body["retrain_job_id"], (
        "no duplicate job while one is open"
    )
    assert "still PENDING" in second["retrain_suppressed_reason"]

    metrics_after, jobs_after = _counts(db_session, model_version)
    assert metrics_after == metrics_before + 1, (
        "re-running on the same day updates today's snapshot rather than adding one"
    )
    assert jobs_after == 1


@pytest.mark.integration
def test_new_retrain_job_needs_twenty_new_labels(client, db_session, auth_headers):
    organization_id = _org_id(db_session)
    model_version = f"test_{uuid.uuid4().hex[:8]}"
    _seed_drifting_predictions(db_session, organization_id, model_version)

    first = client.post(
        f"/monitoring/run?model_version={model_version}", headers=auth_headers
    ).json()
    job_id = first["retrain_job_id"]
    closed = client.post(
        f"/monitoring/retrain-jobs/{job_id}/acknowledge?new_status=COMPLETE", headers=auth_headers
    )
    assert closed.status_code == 200, closed.text

    # Make the closed job older than everything that follows.
    job = db_session.get(RetrainJob, job_id)
    job.triggered_at = datetime.utcnow() - timedelta(hours=1)
    db_session.commit()

    def add_new_labels(n: int) -> None:
        for _ in range(n):
            transfer = ETTransfer(
                organization_id=organization_id, et_date=date.today(),
                pc1_result="Pregnant", cl_measure_mm=18, heat_day=7,
            )
            db_session.add(transfer)
            db_session.flush()
            db_session.add(Prediction(
                organization_id=organization_id, transfer_id=transfer.transfer_id,
                model_name="TEST", model_version=model_version, probability=0.1,
                predicted_at=datetime.utcnow(),
            ))
        db_session.commit()

    add_new_labels(5)
    too_few = client.post(
        f"/monitoring/run?model_version={model_version}", headers=auth_headers
    ).json()
    assert too_few["drift_detected"] is True
    assert too_few["retrain_job_id"] is None
    assert "need 20" in too_few["retrain_suppressed_reason"]
    assert _counts(db_session, model_version)[1] == 1

    add_new_labels(20)
    enough = client.post(
        f"/monitoring/run?model_version={model_version}", headers=auth_headers
    ).json()
    assert enough["retrain_job_id"] not in (None, job_id)
    assert _counts(db_session, model_version)[1] == 2


# ── Tenancy (the adaptation, not the upstream behaviour) ────────────────


@pytest.mark.integration
def test_drift_ignores_another_organizations_outcomes(client, db_session, auth_headers):
    """Another tenant's badly-predicted outcomes must not show up as this
    tenant's drift, and must not land in this tenant's metric history.

    Upstream computed over every row in the table. With the queries unscoped,
    the caller below would see drift_detected=true sourced entirely from an
    organization it cannot otherwise read.
    """
    model_version = f"test_{uuid.uuid4().hex[:8]}"

    suffix = uuid.uuid4().hex[:6]
    other = Organization(name=f"Other Clinic {suffix}", slug=f"other-clinic-{suffix}")
    db_session.add(other)
    db_session.flush()
    assert other.organization_id != _org_id(db_session)

    # Every drifting row belongs to the *other* organization.
    _seed_drifting_predictions(db_session, other.organization_id, model_version)

    report = client.get(
        f"/monitoring/drift?model_version={model_version}", headers=auth_headers
    )
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["current_metrics"]["sample_size"] == 0, (
        "the caller's window picked up another organization's predictions"
    )
    assert body["drift_detected"] is False
    assert body["performance_drift_detected"] is False
    assert body["population_drift_detected"] is False

    # The other org's saved snapshots must not appear in this org's history.
    history = client.get(
        f"/monitoring/metrics?model_version={model_version}", headers=auth_headers
    ).json()
    assert history["metrics"] == [], "metric history leaked across organizations"
