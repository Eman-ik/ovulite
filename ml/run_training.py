#!/usr/bin/env python3
"""CLI entry point — train all pregnancy prediction models.

Usage:
    python -m ml.run_training [--version VERSION] [--csv CSV_PATH]
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.train_pipeline import run_full_pipeline


def main():
    parser = argparse.ArgumentParser(description="Train pregnancy prediction models")
    parser.add_argument("--version", type=str, default=None, help="Model version tag")
    parser.add_argument("--csv", type=str, default=None, help="Path to ET Data CSV")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    result = run_full_pipeline(csv_path=args.csv, version=args.version)

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"  Version:      {result['version']}")
    print(f"  Best model:   {result['best_model']}")
    print(f"  Artifacts:    {result['artifact_dir']}")
    print(f"  Report:       {result['report_path']}")
    print()

    # Print holdout metrics for each model
    for key in ("logistic", "xgboost", "tabpfn"):
        m = result["metadata"]["models"].get(key, {})
        metrics = m.get("calibrated_metrics") or m.get("holdout_metrics") or {}
        name = m.get("name", key)
        print(f"  {name}:")
        print(f"    ROC-AUC: {metrics.get('roc_auc', 0):.4f}")
        print(f"    PR-AUC:  {metrics.get('pr_auc', 0):.4f}")
        print(f"    Brier:   {metrics.get('brier_score', 0):.4f}")
        print()


if __name__ == "__main__":
    main()
