#!/usr/bin/env python
"""Train the ordinal + metadata-fusion embryo grader.

Against the cross-entropy baseline in ``ml/artifacts/grading/real_labels_v1``
(accuracy 0.542, macro-F1 0.475, Grade-2 recall 0.192), this changes exactly two
things and holds everything else fixed — same split seed, same backbone, same
freezing policy — so any difference is attributable:

1. CORAL ordinal loss instead of cross-entropy (see ``ml/grading/ordinal.py``).
2. Late fusion of the 36 published morphometric variables.

Honest ceiling
--------------
The label is the modal grade of three embryologists who agree unanimously on
only 58.7% of these images, with pairwise Cohen's kappa 0.411-0.727 (raw
agreement 61.2-82.0%). A classifier cannot reliably exceed the agreement of the
people defining its target. Treat anything approaching ~75% as at the ceiling,
not as headroom, and report the kappa alongside the accuracy.

Leakage
-------
The metadata scaler is fitted on the training split only. Fitting it over all
482 rows would leak the test distribution into training — on a dataset this
small that alone can move the reported number.

Run:  python -m ml.grading.train_ordinal_fusion --epochs 40
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .config import PROJECT_ROOT, SEED
from .ordinal import (
    CoralLoss,
    init_bias_from_prevalence,
    logits_to_class,
    ordinal_metrics,
    threshold_pos_weights,
)
from .real_labels import (
    CLASS_NAMES,
    load_labeled_images,
    load_morphometrics,
    morphometric_columns,
    stratified_split,
)

ARTIFACT_ROOT = PROJECT_ROOT / "ml" / "artifacts" / "grading"
BASELINE = {"accuracy": 0.5417, "macro_f1": 0.4753, "grade2_recall": 0.1923}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class _Dataset:
    """Images plus their standardised morphometrics."""

    def __init__(self, frame: pd.DataFrame, features: np.ndarray, transform):
        self.frame = frame.reset_index(drop=True)
        self.features = features.astype(np.float32)
        self.transform = transform

    def __len__(self):
        return len(self.frame)

    def __getitem__(self, i):
        import torch
        from PIL import Image

        row = self.frame.iloc[i]
        image = Image.open(row["image_path"]).convert("RGB")
        return (
            self.transform(image),
            torch.from_numpy(self.features[i]),
            int(row["grade_class"]),
        )


def train(
    epochs: int = 40,
    batch_size: int = 16,
    lr: float = 1e-4,
    seed: int = SEED,
    head: str = "coral",
    use_metadata: bool = True,
    arm_name: str = "ordinal_fusion",
) -> dict:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader
    from torchvision import transforms

    from .models import EmbryoGradeOrdinalFusion

    torch.manual_seed(seed)
    np.random.seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    labels = load_labeled_images()
    morph = load_morphometrics()
    feature_names = morphometric_columns()
    data = labels.merge(morph, on="figure_name", how="inner", validate="one_to_one")
    if len(data) != len(labels):
        raise ValueError(f"Join dropped rows: {len(labels)} labels -> {len(data)}")

    # Same seed and function as the baseline, so the splits are identical.
    train_df, val_df, test_df = stratified_split(data, seed=seed)

    # Scaler fitted on train only.
    mean = train_df[feature_names].to_numpy(dtype=np.float64).mean(axis=0)
    std = train_df[feature_names].to_numpy(dtype=np.float64).std(axis=0)
    std[std == 0] = 1.0

    def scale(frame):
        return (frame[feature_names].to_numpy(dtype=np.float64) - mean) / std

    train_tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(20),
        transforms.ColorJitter(brightness=0.15, contrast=0.15),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    eval_tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    loaders = {
        "train": DataLoader(_Dataset(train_df, scale(train_df), train_tf), batch_size=batch_size, shuffle=True),
        "val": DataLoader(_Dataset(val_df, scale(val_df), eval_tf), batch_size=batch_size),
        "test": DataLoader(_Dataset(test_df, scale(test_df), eval_tf), batch_size=batch_size),
    }

    y_train = train_df["grade_class"].to_numpy()
    bias_init = init_bias_from_prevalence(y_train) if head == "coral" else None

    model = EmbryoGradeOrdinalFusion(
        n_grades=3,
        n_metadata_features=len(feature_names),
        freeze_backbone=True,
        head=head,
        use_metadata=use_metadata,
        bias_init=bias_init,
    ).to(device)

    if head == "coral":
        criterion = CoralLoss(
            n_classes=3, pos_weights=threshold_pos_weights(y_train)
        ).to(device)
    else:
        counts = train_df["grade_class"].value_counts().sort_index().to_numpy()
        weights = torch.tensor(
            counts.sum() / (len(counts) * counts), dtype=torch.float32, device=device
        )
        criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad], lr=lr, weight_decay=1e-4
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=4, factor=0.5)

    def evaluate(loader):
        model.eval()
        preds, trues, loss_sum, n = [], [], 0.0, 0
        with torch.no_grad():
            for images, meta, y in loader:
                images, meta, y = images.to(device), meta.to(device), y.to(device)
                logits = model(images, meta)
                loss_sum += float(criterion(logits, y)) * y.size(0)
                n += y.size(0)
                predicted = (
                    logits_to_class(logits) if head == "coral" else logits.argmax(dim=1)
                )
                preds.extend(predicted.cpu().numpy())
                trues.extend(y.cpu().numpy())
        return np.array(trues), np.array(preds), loss_sum / max(n, 1)

    history, best_mae, best_state, best_epoch = [], float("inf"), None, 0
    patience = 10

    for epoch in range(1, epochs + 1):
        model.train()
        run_loss, n = 0.0, 0
        for images, meta, y in loaders["train"]:
            images, meta, y = images.to(device), meta.to(device), y.to(device)
            optimizer.zero_grad()
            loss = criterion(model(images, meta), y)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            run_loss += float(loss) * y.size(0)
            n += y.size(0)

        y_true, y_pred, val_loss = evaluate(loaders["val"])
        m = ordinal_metrics(y_true, y_pred)
        scheduler.step(val_loss)
        history.append({
            "epoch": epoch, "train_loss": run_loss / max(n, 1), "val_loss": val_loss,
            "val_accuracy": m["accuracy"], "val_mae": m["mae_grades"],
        })
        print(
            f"epoch {epoch:>3}/{epochs}  train {run_loss/max(n,1):.4f}  "
            f"val {val_loss:.4f}  acc {m['accuracy']:.3f}  MAE {m['mae_grades']:.3f}"
        )

        # Selected on MAE, not accuracy: for an ordinal target the size of the
        # error is the thing that matters clinically.
        if m["mae_grades"] < best_mae:
            best_mae, best_epoch = m["mae_grades"], epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        elif epoch - best_epoch >= patience:
            print(f"early stop: no MAE improvement in {patience} epochs")
            break

    if best_state is not None:
        model.load_state_dict(best_state)

    y_true, y_pred, _ = evaluate(loaders["test"])
    from sklearn.metrics import classification_report, confusion_matrix, f1_score

    metrics = ordinal_metrics(y_true, y_pred)
    metrics["macro_f1"] = float(f1_score(y_true, y_pred, average="macro"))
    metrics["confusion_matrix"] = confusion_matrix(y_true, y_pred).tolist()
    metrics["classification_report"] = classification_report(
        y_true, y_pred, target_names=CLASS_NAMES, output_dict=True, zero_division=0
    )

    artifact_dir = ARTIFACT_ROOT / f"ablation_{arm_name}"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    weights_path = artifact_dir / "grade_classifier.pt"
    torch.save(model.state_dict(), weights_path)

    metadata = {
        "type": "embryo_grade_classifier",
        "model_class": "EmbryoGradeOrdinalFusion",
        "arm": arm_name,
        "head": head,
        "uses_metadata": use_metadata,
        "backbone": "efficientnet_b0",
        "metadata_features": feature_names,
        "n_metadata_features": len(feature_names),
        "class_names": CLASS_NAMES,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "split": {"train": len(train_df), "val": len(val_df), "test": len(test_df)},
        "training": {
            "epochs_run": len(history), "epochs_max": epochs, "best_epoch": best_epoch,
            "batch_size": batch_size, "lr": lr, "seed": seed, "device": str(device),
            "selection_metric": "val MAE in grade units",
        },
        "metadata_scaler": (
            {"mean": mean.tolist(), "std": std.tolist()} if use_metadata else None
        ),
        "coral_bias_init": bias_init,
        "test_metrics": metrics,
        "baseline_cross_entropy": BASELINE,
        "label_source": {
            "citation": (
                "Rocha J.C. et al. (2017), 'Automatized image processing of bovine "
                "blastocysts produced in vitro for quantitative variable determination', "
                "Scientific Data 4:170192, doi:10.1038/sdata.2017.192"
            ),
            "dataset_doi": "10.6084/m9.figshare.c.3825241",
            "license": "CC0 (data), CC-BY 4.0 (article)",
        },
        "caveats": [
            "The label is the modal grade of three embryologists who agree unanimously on "
            "only 58.7% of these images (pairwise Cohen's kappa 0.411-0.727). That agreement "
            "is the ceiling; quote it whenever quoting accuracy.",
            "482 images is small. Treat these metrics as indicative, not as a substitute for "
            "prospective validation on Ovulite's own embryo images.",
            "No ET-record linkage exists for this external image set, so no donor, technician "
            "or stage metadata is fused — only the published per-image morphometrics.",
            "Predicts IETS grade only. It does not predict pregnancy, and its output must not "
            "be fed into the pregnancy model: the grading label is independent of outcome and "
            "wiring them together would manufacture circular leakage.",
        ],
    }
    (artifact_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (artifact_dir / "training_history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
    (artifact_dir / "manifest.json").write_text(
        json.dumps({"files": {"grade_classifier.pt": _sha256(weights_path)}}, indent=2),
        encoding="utf-8",
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    meta = train(args.epochs, args.batch_size, args.lr, args.seed)
    m = meta["test_metrics"]
    b = meta["baseline_cross_entropy"]
    g2 = m["classification_report"][CLASS_NAMES[1]]["recall"]

    print("\n" + "=" * 62)
    print(f"{'':<22}{'ordinal+fusion':>16}{'cross-entropy':>16}")
    print(f"{'accuracy':<22}{m['accuracy']:>16.3f}{b['accuracy']:>16.3f}")
    print(f"{'macro F1':<22}{m['macro_f1']:>16.3f}{b['macro_f1']:>16.3f}")
    print(f"{'Grade 2 recall':<22}{g2:>16.3f}{b['grade2_recall']:>16.3f}")
    print(f"{'MAE (grades)':<22}{m['mae_grades']:>16.3f}{'n/a':>16}")
    print(f"{'adjacent accuracy':<22}{m['adjacent_accuracy']:>16.3f}{'n/a':>16}")
    print(f"{'off-by-two errors':<22}{m['off_by_two']:>16d}{'n/a':>16}")
    print("=" * 62)
    print("Human ceiling: raters agree unanimously on 58.7%; pairwise kappa 0.411-0.727.")


if __name__ == "__main__":
    main()
