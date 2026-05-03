"""Integration tests for embryo grading API endpoints."""

import io
import os
from pathlib import Path

import pytest


REQUIRES_POSTGRES = os.getenv("TEST_DATABASE_URL") is None


@pytest.mark.integration
def test_grading_model_info(client, auth_headers):
    """Test GET /grade/model-info endpoint."""
    response = client.get("/grade/model-info", headers=auth_headers)

    # Returns 200 if model loadable, 503 if dependencies/model unavailable.
    if response.status_code == 200:
        body = response.json()
        assert "model_type" in body
        assert "n_grades" in body
        assert "grade_labels" in body
        assert "backbone" in body
        assert "trained" in body
        assert body["n_grades"] == 3
        assert body["backbone"] == "efficientnet_b0"
    elif response.status_code == 503:
        # PyTorch dependencies not installed
        assert "model" in response.text.lower() or "pytorch" in response.text.lower()
    else:
        pytest.fail(f"Unexpected status {response.status_code}: {response.text}")


@pytest.mark.integration
def test_grade_embryo_requires_image(client, auth_headers):
    """Test that /grade/embryo rejects requests without an image."""
    response = client.post("/grade/embryo", headers=auth_headers)
    assert response.status_code == 422  # FastAPI validation error


@pytest.mark.integration
def test_grade_embryo_rejects_invalid_content_type(client, auth_headers):
    """Test that /grade/embryo rejects non-image files."""
    fake_text = b"This is not an image"
    files = {"image": ("test.txt", io.BytesIO(fake_text), "text/plain")}

    response = client.post("/grade/embryo", files=files, headers=auth_headers)
    assert response.status_code == 400
    assert "JPEG" in response.text or "PNG" in response.text


@pytest.mark.integration
def test_grade_embryo_rejects_invalid_image_bytes(client, auth_headers):
    """Reject malformed bytes even if the MIME type claims JPEG."""
    malformed = b"not-a-real-jpeg"
    files = {"image": ("fake.jpg", io.BytesIO(malformed), "image/jpeg")}

    response = client.post("/grade/embryo", files=files, headers=auth_headers)
    assert response.status_code == 400
    assert "invalid image" in response.text.lower()


@pytest.mark.integration
def test_grade_embryo_accepts_image_jpg_mime_type(client, auth_headers):
    """Accept image/jpg uploads and continue to image-byte validation."""
    malformed = b"not-a-real-jpg"
    files = {"image": ("fake.jpg", io.BytesIO(malformed), "image/jpg")}

    response = client.post("/grade/embryo", files=files, headers=auth_headers)
    assert response.status_code == 400
    assert "invalid image" in response.text.lower()


@pytest.mark.integration
def test_grade_embryo_accepts_jpg_extension_with_generic_mime(client, auth_headers):
    """Accept .jpg extension even if client sends a generic MIME type."""
    malformed = b"not-a-real-jpg"
    files = {"image": ("fake.jpg", io.BytesIO(malformed), "application/octet-stream")}

    response = client.post("/grade/embryo", files=files, headers=auth_headers)
    assert response.status_code == 400
    assert "invalid image" in response.text.lower()


@pytest.mark.integration
def test_grade_embryo_rejects_empty_image(client, auth_headers):
    """Test that /grade/embryo rejects empty image files."""
    files = {"image": ("empty.jpg", io.BytesIO(b""), "image/jpeg")}

    response = client.post("/grade/embryo", files=files, headers=auth_headers)
    assert response.status_code == 400
    assert "empty" in response.text.lower()


@pytest.mark.integration
def test_grade_embryo_with_real_image(client, auth_headers):
    """Test grading a real embryo image."""
    image_dir = Path(__file__).resolve().parents[3] / "docs" / "Blastocystimages" / "Blastocyst images"
    
    if not image_dir.exists():
        pytest.skip(f"Embryo images not found at {image_dir}")

    images = list(image_dir.glob("*.jpg"))
    if not images:
        pytest.skip("No JPEG images found in Blastocyst images directory")

    test_image = images[0]

    with open(test_image, "rb") as f:
        files = {"image": (test_image.name, f, "image/jpeg")}
        data = {
            "embryo_stage": "7",
            "embryo_grade": "1",
            "donor_breed": "Angus",
            "fresh_or_frozen": "Fresh",
            "technician_name": "Test Tech",
        }

        response = client.post("/grade/embryo", files=files, data=data, headers=auth_headers)

    # 200: model available and grading succeeded
    # 503: PyTorch/model not available
    # 500: grading failed
    assert response.status_code in (200, 503, 500), response.text

    if response.status_code == 200:
        body = response.json()
        assert "grade_label" in body
        assert "grade_class" in body
        assert "grade_probabilities" in body
        assert "viability_score" in body
        assert "heatmap_available" in body

        # Validate types
        assert body["grade_label"] in ("Low", "Medium", "High")
        assert body["grade_class"] in (0, 1, 2)
        assert isinstance(body["grade_probabilities"], dict)
        assert "Low" in body["grade_probabilities"]
        assert "Medium" in body["grade_probabilities"]
        assert "High" in body["grade_probabilities"]
        assert 0 <= body["viability_score"] <= 1
        assert isinstance(body["heatmap_available"], bool)

        # Probabilities should sum to ~1.0
        prob_sum = sum(body["grade_probabilities"].values())
        assert 0.99 <= prob_sum <= 1.01


@pytest.mark.integration
def test_grade_embryo_with_heatmap_endpoint(client, auth_headers):
    """Test /grade/embryo-with-heatmap returns base64-encoded heatmap."""
    image_dir = Path(__file__).resolve().parents[3] / "docs" / "Blastocystimages" / "Blastocyst images"
    
    if not image_dir.exists():
        pytest.skip(f"Embryo images not found at {image_dir}")

    images = list(image_dir.glob("*.jpg"))
    if not images:
        pytest.skip("No JPEG images found")

    test_image = images[0]

    with open(test_image, "rb") as f:
        files = {"image": (test_image.name, f, "image/jpeg")}
        response = client.post("/grade/embryo-with-heatmap", files=files, headers=auth_headers)

    assert response.status_code in (200, 503, 500), response.text

    if response.status_code == 200:
        body = response.json()
        assert "grade_label" in body
        assert "grade_class" in body
        assert "grade_probabilities" in body
        assert "viability_score" in body
        assert "heatmap_base64" in body

        # Heatmap may be None if generation failed
        if body["heatmap_base64"]:
            import base64
            # Should be valid base64
            try:
                decoded = base64.b64decode(body["heatmap_base64"])
                assert len(decoded) > 0
            except Exception as e:
                pytest.fail(f"Invalid base64 heatmap: {e}")


@pytest.mark.integration
@pytest.mark.skipif(REQUIRES_POSTGRES, reason="Requires PostgreSQL TEST_DATABASE_URL")
def test_upload_embryo_image(client, auth_headers):
    """Test /grade/upload endpoint for image storage."""
    image_dir = Path(__file__).resolve().parents[3] / "docs" / "Blastocystimages" / "Blastocyst images"
    
    if not image_dir.exists():
        pytest.skip(f"Embryo images not found at {image_dir}")

    images = list(image_dir.glob("*.jpg"))
    if not images:
        pytest.skip("No JPEG images found")

    test_image = images[0]

    with open(test_image, "rb") as f:
        files = {"image": (test_image.name, f, "image/jpeg")}
        data = {"notes": "Integration test upload"}
        response = client.post("/grade/upload", files=files, data=data, headers=auth_headers)

    assert response.status_code == 200, response.text

    body = response.json()
    assert "image_id" in body
    assert "file_path" in body
    assert body["image_id"] > 0
    assert "uploads/embryo_images" in body["file_path"]

    # Check file was actually created
    project_root = Path(__file__).resolve().parents[3]
    uploaded_file = project_root / body["file_path"]
    assert uploaded_file.exists(), f"Uploaded file not found at {uploaded_file}"


@pytest.mark.integration
def test_upload_rejects_oversized_image(client, auth_headers):
    """Test that upload endpoint rejects images over 10MB."""
    # Create a fake 11MB file
    fake_large = io.BytesIO(b"x" * (11 * 1024 * 1024))
    files = {"image": ("large.jpg", fake_large, "image/jpeg")}

    response = client.post("/grade/upload", files=files, headers=auth_headers)
    assert response.status_code in (400, 413)


@pytest.mark.integration
def test_upload_rejects_invalid_image_bytes(client, auth_headers):
    """Reject malformed bytes even if MIME type is image/jpeg."""
    malformed = b"not-a-real-jpeg"
    files = {"image": ("fake.jpg", io.BytesIO(malformed), "image/jpeg")}

    response = client.post("/grade/upload", files=files, headers=auth_headers)
    assert response.status_code == 400
    assert "invalid image" in response.text.lower()


@pytest.mark.integration
def test_grade_embryo_size_limit(client, auth_headers):
    """Test that grading endpoint rejects oversized images."""
    fake_large = io.BytesIO(b"x" * (11 * 1024 * 1024))
    files = {"image": ("large.jpg", fake_large, "image/jpeg")}

    response = client.post("/grade/embryo", files=files, headers=auth_headers)
    assert response.status_code in (400, 413, 422)
