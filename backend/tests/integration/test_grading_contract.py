"""Contract for embryo grading.

The central requirement is separation: AI output is recorded beside the
embryologist's grade and never over it. Everything else here guards the edges of
an endpoint that takes an uploaded file, which is the part most likely to be fed
something unexpected.

None of these assert the model is accurate. It scores 0.587 cross-validated
against a human-agreement ceiling of 0.587 — there is nothing left to claim.
"""

import hashlib
import io as _io
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from PIL import Image


def _jpeg(width=640, height=512, colour=(120, 120, 120)) -> bytes:
    buffer = _io.BytesIO()
    Image.new("RGB", (width, height), colour).save(buffer, "JPEG")
    return buffer.getvalue()


def _blastocyst_image() -> bytes:
    """A real graded image, so the happy path exercises a real measurement."""
    from ml.grading.config import IMAGE_DIR

    path = IMAGE_DIR / "blq3.jpg"
    if not path.exists():
        pytest.skip("Rocha images not extracted in this environment")
    return path.read_bytes()


@pytest.fixture
def embryo_id(client: TestClient, auth_headers, db_session, admin_org_id) -> int:
    from app.models.embryo import Embryo

    embryo = Embryo(organization_id=admin_org_id, grade=1, stage=7, fresh_or_frozen="Fresh")
    db_session.add(embryo)
    db_session.commit()
    db_session.refresh(embryo)
    return embryo.embryo_id


# ── Upload validation ─────────────────────────────────────────────────────

class TestImageValidation:
    def test_empty_file_rejected(self, client: TestClient, auth_headers):
        response = client.post(
            "/grade/embryo", headers=auth_headers,
            files={"image": ("empty.jpg", b"", "image/jpeg")},
        )
        assert response.status_code == 400

    def test_non_image_rejected(self, client: TestClient, auth_headers):
        response = client.post(
            "/grade/embryo", headers=auth_headers,
            files={"image": ("notes.txt", b"this is not an image at all", "text/plain")},
        )
        assert response.status_code == 400

    def test_oversized_image_rejected(self, client: TestClient, auth_headers):
        from app.api.grading import _MAX_IMAGE_BYTES

        oversized = b"\xff\xd8\xff" + b"\x00" * (_MAX_IMAGE_BYTES + 1)
        response = client.post(
            "/grade/embryo", headers=auth_headers,
            files={"image": ("huge.jpg", oversized, "image/jpeg")},
        )
        assert response.status_code == 400
        assert "too large" in response.json()["detail"].lower()

    def test_image_without_a_blastocyst_is_refused_with_a_reason(
        self, client: TestClient, auth_headers
    ):
        """A blank frame must not come back as a confident grade."""
        response = client.post(
            "/grade/embryo", headers=auth_headers,
            files={"image": ("blank.jpg", _jpeg(colour=(255, 255, 255)), "image/jpeg")},
        )
        if response.status_code == 503:
            pytest.skip("grading model unavailable")
        assert response.status_code == 422
        assert "blastocyst" in response.json()["detail"].lower()


# ── Output shape ──────────────────────────────────────────────────────────

class TestGradeOutput:
    @pytest.fixture
    def graded(self, client: TestClient, auth_headers):
        response = client.post(
            "/grade/embryo", headers=auth_headers,
            files={"image": ("blq3.jpg", _blastocyst_image(), "image/jpeg")},
        )
        if response.status_code == 503:
            pytest.skip("grading model unavailable")
        assert response.status_code == 200, response.text
        return response.json()

    def test_grade_is_in_range(self, graded):
        assert graded["predicted_grade"] in (1, 2, 3)

    def test_probabilities_sum_to_one(self, graded):
        total = sum(p["probability"] for p in graded["probabilities"])
        assert total == pytest.approx(1.0, abs=1e-6)

    def test_confidence_is_the_largest_probability(self, graded):
        assert graded["confidence"] == pytest.approx(
            max(p["probability"] for p in graded["probabilities"]), abs=1e-6
        )

    def test_names_the_model_that_produced_it(self, graded):
        assert graded["model_type"] == "morphometric_tabular_grade_classifier"
        assert graded["model_version"]

    def test_does_not_promise_a_heatmap_it_cannot_produce(self, graded):
        """Grad-CAM belongs to the CNN, which no longer backs this endpoint."""
        assert graded["heatmap_available"] is False

    def test_caveats_frame_it_as_experimental_decision_support(self, graded):
        joined = " ".join(graded["caveats"]).lower()
        assert "decision support" in joined
        assert "not a diagnosis" in joined or "not ground truth" in joined
        # The ceiling has to travel with the accuracy, or the number reads as a
        # shortfall rather than the limit of the label.
        assert "0.587" in joined


class TestHeatmapEndpoint:
    def test_heatmap_endpoint_still_returns_an_overlay(self, client: TestClient, auth_headers):
        response = client.post(
            "/grade/embryo-with-heatmap", headers=auth_headers,
            files={"image": ("blq3.jpg", _blastocyst_image(), "image/jpeg")},
        )
        if response.status_code == 503:
            pytest.skip("CNN artifact unavailable")
        assert response.status_code == 200, response.text
        assert response.json()["heatmap_image_base64"]


# ── Separation of AI and manual assessment ────────────────────────────────

class TestManualAndAIStaySeparate:
    def test_recording_an_assessment_never_touches_the_manual_grade(
        self, client: TestClient, auth_headers, db_session, embryo_id
    ):
        """The requirement this whole table exists for."""
        from app.models.embryo import Embryo

        before = db_session.get(Embryo, embryo_id).grade
        response = client.post(
            f"/grade/embryo/{embryo_id}", headers=auth_headers,
            files={"image": ("blq3.jpg", _blastocyst_image(), "image/jpeg")},
        )
        if response.status_code == 503:
            pytest.skip("grading model unavailable")
        assert response.status_code == 200, response.text

        db_session.expire_all()
        assert db_session.get(Embryo, embryo_id).grade == before

    def test_assessment_is_persisted_with_its_provenance(
        self, client: TestClient, auth_headers, embryo_id
    ):
        image = _blastocyst_image()
        response = client.post(
            f"/grade/embryo/{embryo_id}", headers=auth_headers,
            files={"image": ("blq3.jpg", image, "image/jpeg")},
        )
        if response.status_code == 503:
            pytest.skip("grading model unavailable")
        body = response.json()
        assert body["embryo_id"] == embryo_id
        assert body["model_version"]
        assert body["image_sha256"] == hashlib.sha256(image).hexdigest()

    def test_assessments_accumulate_rather_than_overwrite(
        self, client: TestClient, auth_headers, embryo_id
    ):
        """Re-grading must leave the earlier assessment readable.

        Overwriting would erase which model said what, which is the only reason
        to store the model version at all.
        """
        image = _blastocyst_image()
        for _ in range(2):
            response = client.post(
                f"/grade/embryo/{embryo_id}", headers=auth_headers,
                files={"image": ("blq3.jpg", image, "image/jpeg")},
            )
            if response.status_code == 503:
                pytest.skip("grading model unavailable")

        body = client.get(f"/grade/embryo/{embryo_id}/assessments", headers=auth_headers).json()
        assert len(body["ai_assessments"]) == 2

    def test_comparison_reports_both_without_reconciling_them(
        self, client: TestClient, auth_headers, db_session, embryo_id
    ):
        from app.models.embryo_ai_assessment import EmbryoAIAssessment
        from app.models.embryo import Embryo

        organization_id = db_session.get(Embryo, embryo_id).organization_id
        db_session.add(
            EmbryoAIAssessment(
                organization_id=organization_id, embryo_id=embryo_id,
                model_name="test", model_version="v0",
                predicted_grade=3, confidence=Decimal("0.6100"),
            )
        )
        db_session.commit()

        body = client.get(f"/grade/embryo/{embryo_id}/assessments", headers=auth_headers).json()
        assert body["manual_grade"] == 1      # the embryologist's, untouched
        assert body["latest_ai_grade"] == 3   # the model's, disagreeing
        assert body["agrees"] is False        # surfaced, not resolved

    def test_grading_a_missing_embryo_is_refused(self, client: TestClient, auth_headers):
        response = client.post(
            "/grade/embryo/999999", headers=auth_headers,
            files={"image": ("blq3.jpg", _blastocyst_image(), "image/jpeg")},
        )
        assert response.status_code == 404


# ── Access control ────────────────────────────────────────────────────────

class TestAccessControl:
    def test_anonymous_cannot_grade(self, client: TestClient):
        assert client.post(
            "/grade/embryo", files={"image": ("a.jpg", _jpeg(), "image/jpeg")}
        ).status_code == 401

    def test_model_info_describes_the_served_grader(self, client: TestClient, auth_headers):
        body = client.get("/grade/model-info", headers=auth_headers).json()
        assert "morphometric" in body["model_type"]
        assert "simclr" not in body["model_type"].lower(), (
            "model-info is describing the similarity index, not the grader"
        )
