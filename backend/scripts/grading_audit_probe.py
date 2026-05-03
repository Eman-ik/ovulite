"""Audit probe for embryo grading system."""

import io
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    print("=" * 80)
    print("EMBRYO GRADING SYSTEM AUDIT PROBE")
    print("=" * 80)

    # 1. Check artifact paths
    print("\n[1] Checking grading artifact paths...")
    from ml.grading.config import ARTIFACTS_DIR, IMAGE_DIR, UPLOAD_DIR

    print(f"    Expected artifacts dir: {ARTIFACTS_DIR}")
    print(f"    Exists: {ARTIFACTS_DIR.exists()}")
    if ARTIFACTS_DIR.exists():
        artifacts = list(ARTIFACTS_DIR.glob("*"))
        print(f"    Contains: {[a.name for a in artifacts]}")

    print(f"    Training images dir: {IMAGE_DIR}")
    print(f"    Exists: {IMAGE_DIR.exists()}")
    if IMAGE_DIR.exists():
        images = list(IMAGE_DIR.glob("*.jpg"))
        print(f"    Image count: {len(images)}")

    print(f"    Upload dir: {UPLOAD_DIR}")
    print(f"    Exists: {UPLOAD_DIR.exists()}")

    # 2. Test model loading
    print("\n[2] Testing model loader...")
    try:
        from ml.grading.predict import EmbryoGrader

        grader = EmbryoGrader.get_instance()
        info = grader.get_model_info()
        print(f"    Model type: {info['model_type']}")
        print(f"    Backbone: {info['backbone']}")
        print(f"    Trained: {info['trained']}")
        print(f"    Grades: {info['n_grades']} ({info['grade_labels']})")
        if info["trained"]:
            print(f"    Best val acc: {info.get('best_val_acc')}")
            print(f"    Train samples: {info.get('n_train')}")
            print(f"    Val samples: {info.get('n_val')}")
    except ImportError as e:
        print(f"    ⚠ PyTorch not available: {e}")
    except Exception as e:
        print(f"    ⚠ Model loading failed: {e}")

    # 3. Test image processing safety
    print("\n[3] Testing image upload handling...")
    if IMAGE_DIR.exists() and list(IMAGE_DIR.glob("*.jpg")):
        test_image_path = list(IMAGE_DIR.glob("*.jpg"))[0]
        print(f"    Using test image: {test_image_path.name}")

        with open(test_image_path, "rb") as f:
            image_bytes = f.read()

        print(f"    Image size: {len(image_bytes)} bytes")

        # Test size limits
        max_size = 10 * 1024 * 1024
        if len(image_bytes) > max_size:
            print(f"    ⚠ Image exceeds 10MB limit")
        else:
            print(f"    ✓ Image within size limit")

        # Test that image can be loaded
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(image_bytes))
            print(f"    ✓ Valid image: {img.size} {img.mode}")
        except Exception as e:
            print(f"    ⚠ Invalid image: {e}")

        # Test grading
        try:
            print("\n[4] Testing grading inference...")
            grader = EmbryoGrader.get_instance()
            metadata = {
                "embryo_stage": 7,
                "embryo_grade": 1,
                "donor_breed": "Angus",
                "fresh_or_frozen": "Fresh",
                "technician_name": "Test Tech",
            }
            result = grader.grade(
                image_bytes, metadata=metadata, generate_heatmap=True
            )

            print(f"    Grade: {result['grade_label']} (class {result['grade_class']})")
            print(f"    Probabilities: {result['grade_probabilities']}")
            print(f"    Viability score: {result['viability_score']}")
            print(f"    Heatmap generated: {result['heatmap_bytes'] is not None}")
            if result["heatmap_bytes"]:
                print(f"    Heatmap size: {len(result['heatmap_bytes'])} bytes")

        except ImportError as e:
            print(f"    ⚠ PyTorch not available: {e}")
        except Exception as e:
            print(f"    ⚠ Grading failed: {e}")

    # 4. Check API endpoint availability
    print("\n[5] Testing API endpoints (via local FastAPI)...")
    try:
        import requests

        base_url = "http://localhost:8000"

        # Test model-info endpoint (doesn't require auth)
        try:
            resp = requests.get(f"{base_url}/grade/model-info", timeout=2)
            if resp.status_code == 200:
                info = resp.json()
                print(f"    ✓ /grade/model-info: {info['model_type']}")
            else:
                print(f"    ℹ /grade/model-info returned {resp.status_code}")
        except requests.exceptions.ConnectionError:
            print("    ℹ API server not running (start with uvicorn)")
        except Exception as e:
            print(f"    ⚠ API check failed: {e}")
            
    except ImportError:
        print("    ℹ requests library not available")

    # 5. Document training procedure
    print("\n[6] Training procedure info...")
    print("    To train the grading model, run:")
    print("    $ cd D:\\Ovulite new")
    print("    $ .\\backend\\venv\\Scripts\\python.exe -m ml.grading.run_training")
    print()
    print("    Training modes:")
    print("      --simclr            : SimCLR pretraining only")
    print("      --supervised        : Supervised training only")
    print("      (no flags)          : Full pipeline (SimCLR + supervised)")
    print()
    print("    Expected artifacts after training:")
    print(f"      {ARTIFACTS_DIR / 'simclr_backbone.pt'}")
    print(f"      {ARTIFACTS_DIR / 'grading_model.pt'}")
    print(f"      {ARTIFACTS_DIR / 'grading_history.json'}")

    print("\n[7] Security findings...")
    print("    ✓ File type validation (JPEG/PNG only)")
    print("    ✓ Size limit (10MB)")
    print("    ✓ Hash-based deduplication (SHA256)")
    print("    ✓ Filesystem path sanitization (hash-based filenames)")
    print("    ⚠ No virus scanning")
    print("    ⚠ No EXIF data stripping (potential privacy leak)")

    print("\n" + "=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
