"""Isolated tests: never run the application's startup against a local database."""
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.canonical_intake import router as intake
from app.api.case_timeline import router as timeline
from app.api.literature import router as literature
from app.auth.dependencies import get_current_user
from app.database import Base, get_db
from app.models.organization import Organization
from app.models.et_transfer import ETTransfer
from app.services.canonical_intake import validate_csv


@pytest.fixture
def harness():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    db = Session(engine)
    db.add_all([Organization(organization_id=101, name="Test A", slug="test-a"), Organization(organization_id=102, name="Test B", slug="test-b")])
    db.commit()
    user = SimpleNamespace(organization_id=101, username="curator", role="embryologist")
    app = FastAPI()
    app.include_router(intake, prefix="/intake")
    app.include_router(literature, prefix="/literature")
    app.include_router(timeline, prefix="/case-timeline")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as client:
        yield client, db, user
    db.close()
    engine.dispose()


HEADERS = "et_number,et_date,recipient_tag,farm_location,embryo_stage,embryo_grade,cl_measure_mm,pc1_date,pc1_result"
CSV = HEADERS + "\n1,2026-01-01,R1,Farm A,6,1,20,2026-02-01,positive\n"
MAPPING = {key: key for key in HEADERS.split(",")}


def preview(client, csv=CSV, source="real_internal"):
    return client.post("/intake/preview", json={"filename": "test.csv", "csv_text": csv,
        "mapping": MAPPING, "source_type": source, "source_reference": "Test fixture permission"})


def test_import_commit_provenance_and_replay(harness):
    client, db, _ = harness
    response = preview(client)
    assert response.status_code == 201, response.text
    batch = response.json()["batch_id"]
    assert db.query(ETTransfer).count() == 0
    assert client.post(f"/intake/batches/{batch}/commit").json()["inserted"] == 1
    transfer = db.query(ETTransfer).one()
    assert transfer.pc1_result == "Pregnant"
    result = client.get(f"/case-timeline/{transfer.transfer_id}/timeline").json()
    assert result["provenance"]["source_row"] == 2
    assert [event["kind"] for event in result["events"]] == ["transfer", "pregnancy_check"]
    assert client.post(f"/intake/batches/{batch}/commit").status_code == 409
    assert preview(client).status_code == 409


def test_synthetic_never_enters_clinical_tables(harness):
    client, db, _ = harness
    batch = preview(client, source="synthetic_demo").json()["batch_id"]
    response = client.post(f"/intake/batches/{batch}/commit")
    assert response.json()["status"] == "demo_staged"
    assert db.query(ETTransfer).count() == 0


def test_import_org_isolation_and_readonly_role(harness):
    client, _, user = harness
    batch = preview(client).json()["batch_id"]
    user.organization_id = 102
    assert client.get("/intake/batches").json() == []
    assert client.post(f"/intake/batches/{batch}/commit").status_code == 404
    user.role = "viewer"
    assert preview(client).status_code == 403


def test_validation_reconciles_duplicates_and_errors():
    text = CSV + "1,2026-01-01,R1,Farm A,6,1,20,,\n2,2026-01-01,R2,Farm A,6,1,NaN,,\n3,2026-01-01,R3,Farm A,6,1,20,2025-01-01,Open\n"
    accepted, report = validate_csv(text, MAPPING, set())
    assert accepted == []
    assert report["total"] == 4
    assert report["duplicate"] == 2
    assert report["rejected"] == 2
    assert report["accepted"] + report["duplicate"] + report["rejected"] == report["total"]


def test_column_mapping_and_existing_identifiers():
    mapping = {**MAPPING, "recipient_tag": "Animal"}
    accepted, report = validate_csv(CSV.replace("recipient_tag", "Animal"), mapping, {1})
    assert not accepted and report["duplicate"] == 1
    with pytest.raises(ValueError, match="required"):
        validate_csv(CSV, {}, set())


def test_preview_can_correct_mapping_without_changing_raw_source(harness):
    from app.models.intake_batch import IntakeBatch
    client, db, _ = harness
    wrong = {**MAPPING, "embryo_stage": "embryo_grade", "embryo_grade": "embryo_stage"}
    response = client.post("/intake/preview", json={"filename": "test.csv", "csv_text": CSV,
        "mapping": wrong, "source_type": "real_internal", "source_reference": "Test fixture permission"})
    assert response.status_code == 201
    assert response.json()["report"]["rejected"] == 1
    corrected = preview(client)
    assert corrected.json()["batch_id"] == response.json()["batch_id"]
    assert corrected.json()["report"]["accepted"] == 1
    assert db.query(IntakeBatch).one().raw_csv == CSV


DOCUMENT = {"title": "Test evidence fixture", "authors": "Fixture Author", "year": 2026,
    "source_url": "https://example.org/test-evidence", "source_kind": "peer_reviewed", "rights": "Test fixture only",
    "content": "Progesterone evidence appears in this artificial test passage. This text is a software test fixture and is not clinical or scientific evidence. " * 3}


def test_literature_citations_duplicates_abstention_and_tenant(harness):
    client, _, user = harness
    assert client.post("/literature/query", json={"question": "progesterone evidence"}).json()["citations"] == []
    response = client.post("/literature/documents", json=DOCUMENT)
    assert response.status_code == 201, response.text
    assert client.post("/literature/documents", json=DOCUMENT).status_code == 409
    answer = client.post("/literature/query", json={"question": "progesterone evidence"}).json()
    assert answer["citations"][0]["document_id"] == response.json()["document_id"]
    assert answer["citations"][0]["excerpt"] in " ".join(DOCUMENT["content"].split())
    assert client.post("/literature/query", json={"question": "unrelated galaxies"}).json()["citations"] == []
    user.organization_id = 102
    assert client.get("/literature/documents").json()["total"] == 0
    assert client.post("/literature/query", json={"question": "progesterone evidence"}).json()["citations"] == []
    user.role = "viewer"
    assert client.post("/literature/documents", json=DOCUMENT).status_code == 403


def test_new_routes_require_authentication():
    app = FastAPI()
    app.include_router(literature, prefix="/literature")
    with TestClient(app) as client:
        assert client.get("/literature/documents").status_code == 401


def test_timeline_prior_history_and_cross_organization_denial(harness):
    client, db, user = harness
    first = preview(client).json()["batch_id"]
    assert client.post(f"/intake/batches/{first}/commit").status_code == 200
    later = CSV.replace("\n1,2026-01-01", "\n2,2026-03-01").replace("2026-02-01", "2026-04-01")
    second = preview(client, later).json()["batch_id"]
    assert client.post(f"/intake/batches/{second}/commit").status_code == 200
    transfer = db.query(ETTransfer).filter_by(et_number=2).one()
    result = client.get(f"/case-timeline/{transfer.transfer_id}/timeline").json()
    assert result["recipient_history"]["total"] == 1
    assert result["recipient_history"]["items"][0]["date"] == "2026-01-01"
    user.organization_id = 102
    assert client.get(f"/case-timeline/{transfer.transfer_id}/timeline").status_code == 404


def test_migrations_upgrade_and_downgrade(harness):
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect
    _, db, _ = harness
    migrations = []
    for name in ("008_literature_documents", "009_canonical_intake", "010_release60_metadata_rag", "011_intake_governance"):
        spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[2] / "alembic" / "versions" / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        migrations.append(module)
    connection = db.connection()
    with Operations.context(MigrationContext.configure(connection)):
        for migration in reversed(migrations):
            migration.downgrade()
        for migration in migrations:
            migration.upgrade()
    assert {"literature_documents", "intake_batches", "transfer_provenance"} <= set(inspect(connection).get_table_names())
