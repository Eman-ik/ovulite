#!/usr/bin/env python
"""Ablate the two grading changes separately.

The first attempt changed the loss and added a metadata branch in one run, got a
worse result, and left no way to tell which change caused it. This runs the arms
independently against the same split so each is attributable:

    A  cross-entropy, image only     the shipped baseline (already trained)
    B  CORAL,         image only     the loss change alone
    C  cross-entropy, image + morph  the fusion change alone
    D  CORAL,         image + morph  both

Arm A is not re-run; its metrics are read from the existing artifact so the
comparison uses the real shipped numbers rather than a re-trained approximation.

Run:  python -m ml.grading.run_ablation --epochs 40
"""

from __future__ import annotations

import argparse
import json

from .config import PROJECT_ROOT, SEED
from .real_labels import CLASS_NAMES
from .train_ordinal_fusion import train

ARMS = [
    ("B_ordinal_only", "coral", False, "CORAL, image only"),
    ("C_fusion_only", "softmax", True, "cross-entropy, image + morphometrics"),
    ("D_ordinal_fusion", "coral", True, "CORAL, image + morphometrics"),
]

BASELINE_ARTIFACT = (
    PROJECT_ROOT / "ml" / "artifacts" / "grading" / "real_labels_v1" / "metadata.json"
)


def _baseline_row() -> dict:
    """Read arm A from the shipped artifact rather than assuming its numbers."""
    meta = json.loads(BASELINE_ARTIFACT.read_text(encoding="utf-8"))
    m = meta["test_metrics"]
    report = m["classification_report"]
    return {
        "arm": "A_baseline",
        "description": "cross-entropy, image only (shipped)",
        "accuracy": m["accuracy"],
        "macro_f1": m["macro_f1"],
        "grade2_recall": report[CLASS_NAMES[1]]["recall"],
        "mae_grades": None,
        "adjacent_accuracy": None,
        "predicts_middle_class": any(row[1] > 0 for row in m["confusion_matrix"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    rows = [_baseline_row()]

    for arm_name, head, use_metadata, description in ARMS:
        print(f"\n{'='*70}\nARM {arm_name}  —  {description}\n{'='*70}", flush=True)
        meta = train(
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr,
            seed=args.seed,
            head=head,
            use_metadata=use_metadata,
            arm_name=arm_name,
        )
        m = meta["test_metrics"]
        rows.append({
            "arm": arm_name,
            "description": description,
            "accuracy": m["accuracy"],
            "macro_f1": m["macro_f1"],
            "grade2_recall": m["classification_report"][CLASS_NAMES[1]]["recall"],
            "mae_grades": m["mae_grades"],
            "adjacent_accuracy": m["adjacent_accuracy"],
            "predicts_middle_class": any(row[1] > 0 for row in m["confusion_matrix"]),
        })

    out = PROJECT_ROOT / "ml" / "artifacts" / "grading" / "ablation_summary.json"
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def fmt(v, spec=".3f"):
        return "n/a" if v is None else format(v, spec)

    print("\n" + "=" * 96)
    print(f"{'arm':<20}{'accuracy':>10}{'macroF1':>10}{'G2 recall':>11}{'MAE':>8}{'adj acc':>9}{'predicts G2':>13}")
    print("-" * 96)
    for r in rows:
        print(
            f"{r['arm']:<20}{fmt(r['accuracy']):>10}{fmt(r['macro_f1']):>10}"
            f"{fmt(r['grade2_recall']):>11}{fmt(r['mae_grades']):>8}"
            f"{fmt(r['adjacent_accuracy']):>9}{str(r['predicts_middle_class']):>13}"
        )
    print("=" * 96)
    print("Majority-class baseline accuracy = 0.403 (Grade 3 is 29/72 of the test split).")
    print("Human ceiling: three raters agree unanimously on 58.7%; pairwise kappa 0.411-0.727.")
    print(f"\nwritten: {out}")


if __name__ == "__main__":
    main()
