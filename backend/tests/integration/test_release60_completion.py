"""Completion acceptance: full records, licensed corpus, vector index and RAG guardrails."""
import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from tests.integration.test_release60_workflows import harness, CSV, DOCUMENT, preview
from app.api.transfers import router as transfers
from app.api.import_data import router as legacy_import
from app.models.case_metadata import CaseAudit, CaseMetadata
from app.models.et_transfer import ETTransfer
from app.models.literature_chunk import LiteratureChunk
from app.services.literature_rag import generate, settings


def record(**changes):
    return {"et_number": 10, "et_date": "2026-04-10", "recipient_tag": "R1", "farm_location": "Farm A",
        "embryo_stage": 6, "embryo_grade": 1, "donor_tag": "D1", "sire_name": "S1",
        "donor_breed": "Holstein", "recipient_breed": "Holstein", "semen_type": "sexed",
        "opu_date": "2026-04-01", "ivf_date": "2026-04-02", "p4_ng_ml": 3.1,
        "protocol_name": "Recorded protocol", "technician_name": "Tech A", "embryo_day": 8,
        "recipient_age_years": 4, "recipient_parity": 2, **changes}


def test_extended_manual_record_and_full_lineage(harness):
    client, db, _ = harness
    response = client.post("/intake/manual", json={"record": record(), "source_reference": "Collection log 2026"})
    assert response.status_code == 201, response.text
    identifier = response.json()["transfer_id"]
    metadata = db.query(CaseMetadata).one()
    assert metadata.data["p4_ng_ml"] == 3.1
    timeline = client.get(f"/case-timeline/{identifier}/timeline").json()
    assert [event["kind"] for event in timeline["events"]] == ["opu", "ivf", "transfer"]
    assert timeline["audit"][0]["actor"] == "curator"
    transfer = db.query(ETTransfer).one()
    assert transfer.embryo.sire.semen_type == "Sexed"
    assert transfer.protocol.name == "Recorded protocol"


@pytest.mark.parametrize("changes", [
    {"pc2_result": "Pregnant"}, {"previous_et_count": 1, "previous_et_pregnancies": 2},
    {"opu_date": "2026-04-12"}, {"relative_humidity_pct": 101},
    {"estrus_date": "2026-04-03", "days_estrus_to_et": 8},
    {"p4_ng_ml": -1}, {"pregnancy_loss_date": "2026-05-01"},
])
def test_extended_validation_rejects_inconsistent_records(harness, changes):
    client, db, _ = harness
    response = client.post("/intake/manual", json={"record": record(**changes), "source_reference": "Collection log"})
    assert response.status_code == 422, response.text
    assert db.query(ETTransfer).count() == 0


def test_legacy_csv_cannot_bypass_mapping(harness):
    client, _, user = harness
    client.app.include_router(legacy_import, prefix="/import")
    user.role = "admin"
    assert client.post("/import/csv", files={"file": ("x.csv", CSV, "text/csv")}).status_code == 410
    assert client.post("/import/seed-from-disk").status_code == 410


def test_manual_update_validation_audit_and_tenant_links(harness):
    client, db, user = harness
    client.app.include_router(transfers, prefix="/transfers")
    identifier = client.post("/intake/manual", json={"record": record(), "source_reference": "Collection log"}).json()["transfer_id"]
    user.role = "veterinarian"
    assert client.put(f"/transfers/{identifier}", json={"cl_measure_mm": 500}).status_code == 422
    assert client.put(f"/transfers/{identifier}", json={"recipient_id": 9999}).status_code == 422
    response = client.put(f"/transfers/{identifier}", json={"pc1_date": "2026-05-10", "pc1_result": "Pregnant"})
    assert response.status_code == 200, response.text
    assert db.query(CaseMetadata).one().version == 2
    assert db.query(CaseAudit).count() == 2
    assert db.query(CaseMetadata).one().data["p4_ng_ml"] == 3.1


def test_corpus_has_60_licensed_nonduplicate_papers():
    path = Path(__file__).resolve().parents[2] / "resources" / "literature_seed" / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    documents = manifest["documents"]
    assert len(documents) == 60
    assert len({doc["pmcid"] for doc in documents}) == 60
    for doc in documents:
        assert doc["checksum"] == hashlib.sha256(doc["content"].encode()).hexdigest()
        assert "creativecommons.org/licenses/by/" in doc["license_url"] or "creativecommons.org/publicdomain/zero/" in doc["license_url"]
        assert len(doc["content"]) > 200
        assert doc["year"] <= 2026


def test_corpus_seed_is_idempotent_and_organization_scoped(harness):
    client, _, user = harness
    response = client.post("/literature/seed")
    assert response.status_code == 201, response.text
    assert response.json()["inserted"] == 60
    assert client.post("/literature/seed").json()["inserted"] == 0
    user.organization_id = 102
    assert client.get("/literature/documents").json()["total"] == 0


def test_generative_rag_uses_retrieved_citations_and_persisted_index(harness, monkeypatch):
    client, db, _ = harness
    client.post("/literature/documents", json=DOCUMENT)
    monkeypatch.setenv("LITERATURE_RAG_ENABLED", "true")
    response = Mock()
    response.json.return_value = {"response": json.dumps({"claims": [{"text": "The supplied fixture discusses progesterone.", "citations": [1]}], "insufficient_evidence": False})}
    post = Mock(return_value=response)
    monkeypatch.setattr("app.services.literature_rag.requests.post", post)
    result = client.post("/literature/query", json={"question": "progesterone evidence"}).json()
    assert result["mode"] == "generative_rag"
    assert "[1]" in result["answer"]
    assert db.query(LiteratureChunk).count() > 0
    payload = post.call_args.kwargs["json"]
    assert "case" not in json.loads(payload["prompt"])


@pytest.mark.parametrize("response_body", [
    {"claims": [{"text": "Unsupported reference", "citations": [999]}], "insufficient_evidence": False},
    {"claims": [{"text": "No citation", "citations": []}], "insufficient_evidence": False},
])
def test_bad_generation_falls_back_to_real_passages(harness, monkeypatch, response_body):
    client, _, _ = harness
    client.post("/literature/documents", json=DOCUMENT)
    monkeypatch.setenv("LITERATURE_RAG_ENABLED", "true")
    response = Mock()
    response.json.return_value = {"response": json.dumps(response_body)}
    monkeypatch.setattr("app.services.literature_rag.requests.post", Mock(return_value=response))
    result = client.post("/literature/query", json={"question": "progesterone evidence"}).json()
    assert result["mode"] == "extractive_retrieval"
    assert result["citations"]
    assert result["fallback_reason"]


def test_generation_outage_is_honest(harness, monkeypatch):
    client, _, _ = harness
    client.post("/literature/documents", json=DOCUMENT)
    monkeypatch.setenv("LITERATURE_RAG_ENABLED", "true")
    monkeypatch.setattr("app.services.literature_rag.requests.post", Mock(side_effect=requests.Timeout))
    result = client.post("/literature/query", json={"question": "progesterone evidence"}).json()
    assert result["mode"] == "extractive_retrieval"
    assert "unavailable" in result["fallback_reason"]


def test_llama_cpp_provider(harness, monkeypatch):
    client, _, _ = harness
    client.post("/literature/documents", json=DOCUMENT)
    monkeypatch.setenv("LITERATURE_RAG_ENABLED", "true")
    monkeypatch.setenv("LITERATURE_GENERATION_PROVIDER", "llama_cpp")
    response = Mock()
    response.json.return_value = {"choices": [{"message": {"content": json.dumps({"claims": [{"text": "The fixture discusses progesterone.", "citations": [1]}], "insufficient_evidence": False})}}]}
    post = Mock(return_value=response)
    monkeypatch.setattr("app.services.literature_rag.requests.post", post)
    assert client.post("/literature/query", json={"question": "progesterone"}).json()["mode"] == "generative_rag"
    assert post.call_args.args[0].endswith("/v1/chat/completions")


def test_external_embryo_identifier_is_unique(harness):
    client, db, _ = harness
    first = client.post("/intake/manual", json={"record": record(embryo_identifier="EMB-1"), "source_reference": "Collection log"})
    assert first.status_code == 201
    duplicate = client.post("/intake/manual", json={"record": record(et_number=11, embryo_identifier="EMB-1"), "source_reference": "Collection log"})
    assert duplicate.status_code == 409
    assert db.query(ETTransfer).count() == 1


def test_intake_revisions_and_source_download(harness):
    client, _, user = harness
    batch_id = preview(client).json()["batch_id"]
    assert client.get(f"/intake/batches/{batch_id}/source").content == CSV.encode()
    preview(client)
    revisions = client.get(f"/intake/batches/{batch_id}/revisions").json()
    assert len(revisions) == 2
    assert revisions[0]["report"]["schema_version"] == "2.0"
    user.organization_id = 102
    assert client.get(f"/intake/batches/{batch_id}/source").status_code == 404
    assert client.get(f"/intake/batches/{batch_id}/revisions").json() == []
