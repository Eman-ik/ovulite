"""Generate metrics summary and ROC plot for a trained prediction artifact.

Usage:
    python backend/scripts/generate_metrics_and_roc.py --version v20260306_audit_fix5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, roc_curve

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.features import build_feature_matrix, preprocess_for_model
from ml.split import temporal_split


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate ROC and metrics summary")
    parser.add_argument("--version", required=True, help="Artifact version under ml/artifacts")
    args = parser.parse_args()

    artifact_dir = PROJECT_ROOT / "ml" / "artifacts" / args.version
    metadata_path = artifact_dir / "metadata.json"

    if not metadata_path.exists():
        raise FileNotFoundError(f"metadata.json not found: {metadata_path}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    print("=" * 72)
    print(f"METRICS SUMMARY - {args.version}")
    print("=" * 72)
    print(f"{'Model':35} {'Accuracy':>10} {'ROC_AUC':>10} {'PR_AUC':>10} {'F1':>10}")
    print("-" * 72)
    summary: dict[str, dict[str, float | None]] = {}
    for key, model_data in metadata.get("models", {}).items():
        model_name = model_data.get("name", key)
        metrics = model_data.get("calibrated_metrics") or model_data.get("holdout_metrics") or {}
        acc = metrics.get("accuracy", 0.0)
        roc = metrics.get("roc_auc", 0.0)
        pr = metrics.get("pr_auc", 0.0)
        f1 = metrics.get("f1", 0.0)
        print(f"{model_name[:35]:35} {acc:10.4f} {roc:10.4f} {pr:10.4f} {f1:10.4f}")
        summary[model_name] = {
            "accuracy": acc,
            "roc_auc": roc,
            "pr_auc": pr,
            "f1": f1,
        }

    # Build holdout split exactly as training pipeline does.
    df = build_feature_matrix(None)
    train_df, holdout_df = temporal_split(df)
    _, _, _, encoder_map = preprocess_for_model(train_df, fit=True)
    X_test, y_test, _, _ = preprocess_for_model(holdout_df, fit=False, encoder_map=encoder_map)

    model_files = {
        "LogisticRegression": artifact_dir / "logistic_model.joblib",
        "TabPFN_or_Fallback": artifact_dir / "tabpfn_model.joblib",
        "XGBoost": artifact_dir / "xgboost_model.joblib",
    }

    loaded: dict[str, object] = {}
    for name, path in model_files.items():
        if path.exists():
            loaded[name] = joblib.load(path)

    if not loaded:
        raise RuntimeError(f"No model files found in {artifact_dir}")

    plt.figure(figsize=(8, 6))
    for name, model in loaded.items():
        if not hasattr(model, "predict_proba"):
            continue
        y_prob = model.predict_proba(X_test)[:, 1]
        fpr, tpr, _ = roc_curve(y_test, y_prob)
        auc = roc_auc_score(y_test, y_prob)
        plt.plot(fpr, tpr, label=f"{name} (AUC={auc:.3f})")

    plt.plot([0, 1], [0, 1], "k--", alpha=0.5)
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title(f"Ovulite ROC Curves - {args.version}")
    plt.legend()
    plt.grid(alpha=0.2)

    roc_path = artifact_dir / "roc_curves.png"
    plt.savefig(roc_path, dpi=150, bbox_inches="tight")

    summary_path = artifact_dir / "metrics_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\nSaved files:")
    print(f"- {roc_path}")
    print(f"- {summary_path}")


if __name__ == "__main__":
    main()
