"""CLI entry point for embryo grading training.

Usage:
    python -m ml.grading.run_training              # Full pipeline (SimCLR + supervised)
    python -m ml.grading.run_training --simclr     # SimCLR only
    python -m ml.grading.run_training --supervised  # Supervised only
"""

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    parser = argparse.ArgumentParser(description="Train embryo grading models")
    parser.add_argument("--simclr", action="store_true", help="Run only SimCLR pretraining")
    parser.add_argument("--supervised", action="store_true", help="Run only supervised training")
    parser.add_argument("--epochs-simclr", type=int, default=None)
    parser.add_argument("--epochs-grading", type=int, default=None)
    parser.add_argument("--csv", type=str, default=None, help="Path to ET Data CSV")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )

    from ml.grading.config import ARTIFACTS_DIR, IMAGE_DIR
    from ml.grading.train import run_full_pipeline, train_grading, train_simclr

    csv_path = Path(args.csv) if args.csv else None
    kwargs_simclr = {}
    kwargs_grading = {}

    if args.epochs_simclr:
        kwargs_simclr["epochs"] = args.epochs_simclr
    if args.epochs_grading:
        kwargs_grading["epochs"] = args.epochs_grading

    if args.simclr:
        train_simclr(image_dir=IMAGE_DIR, **kwargs_simclr)
    elif args.supervised:
        train_grading(image_dir=IMAGE_DIR, csv_path=csv_path, **kwargs_grading)
    else:
        run_full_pipeline(image_dir=IMAGE_DIR, csv_path=csv_path)


if __name__ == "__main__":
    main()
