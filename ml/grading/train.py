"""Training pipelines for SimCLR pretraining and supervised grading.

Two-stage training (REQUIREMENTS §4.2):
1. SimCLR self-supervised pretraining on all 482 images (no labels needed)
2. Supervised fine-tuning with pseudo-labels from pregnancy outcomes
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, random_split

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from .config import (
    ARTIFACTS_DIR,
    BACKBONE_FEATURE_DIM,
    BATCH_SIZE_GRADING,
    BATCH_SIZE_SIMCLR,
    EPOCHS_GRADING,
    EPOCHS_SIMCLR,
    IMAGE_DIR,
    LR_GRADING,
    LR_SIMCLR,
    NUM_GRADES,
    SEED,
    SIMCLR_PROJECTION_DIM,
    SIMCLR_TEMPERATURE,
)


def _set_seed(seed: int = SEED):
    """Set reproducibility seeds."""
    import random

    random.seed(seed)
    np.random.seed(seed)
    if HAS_TORCH:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)


# ═══════════════════════════════════════════════════════════
# Stage 1: SimCLR Pretraining
# ═══════════════════════════════════════════════════════════

def train_simclr(
    image_dir: Path = IMAGE_DIR,
    epochs: int = EPOCHS_SIMCLR,
    batch_size: int = BATCH_SIZE_SIMCLR,
    lr: float = LR_SIMCLR,
    save_dir: Path = ARTIFACTS_DIR,
) -> Path:
    """Train SimCLR on unlabeled embryo images.

    Returns path to saved backbone weights.
    """
    if not HAS_TORCH:
        raise ImportError("PyTorch is required for SimCLR training")

    from .models import SimCLRModel, nt_xent_loss
    from .preprocessing import EmbryoImageDataset, get_simclr_transforms

    _set_seed()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"SimCLR training on {device}")

    # Dataset: all images with SimCLR pair augmentation
    # get_simclr_transforms() already returns SimCLRPairTransform
    transform = get_simclr_transforms()
    dataset = EmbryoImageDataset(
        image_dir=image_dir,
        transform=transform,
        mode="plain",
    )

    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,  # Windows compatibility
        drop_last=True,
        pin_memory=torch.cuda.is_available(),
    )

    logger.info(f"SimCLR dataset: {len(dataset)} images, {len(loader)} batches")

    # Model
    model = SimCLRModel(projection_dim=SIMCLR_PROJECTION_DIM).to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    # Training loop
    best_loss = float("inf")
    history = []

    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0.0
        n_batches = 0

        for batch in loader:
            # SimCLR pair: batch is (view1, view2) tuple from SimCLRPairTransform
            view1, view2 = batch
            view1, view2 = view1.to(device), view2.to(device)

            _, z1 = model(view1)
            _, z2 = model(view2)

            loss = nt_xent_loss(z1, z2, temperature=SIMCLR_TEMPERATURE)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()
            n_batches += 1

        scheduler.step()
        avg_loss = epoch_loss / max(n_batches, 1)
        history.append({"epoch": epoch, "loss": avg_loss})

        if epoch % 10 == 0 or epoch == 1:
            logger.info(f"SimCLR Epoch {epoch}/{epochs} | Loss: {avg_loss:.4f}")

        if avg_loss < best_loss:
            best_loss = avg_loss

    # Save backbone weights (without projection head)
    save_dir.mkdir(parents=True, exist_ok=True)
    backbone_path = save_dir / "simclr_backbone.pt"
    torch.save(model.backbone.state_dict(), backbone_path)

    # Save training history
    meta = {
        "type": "simclr_pretraining",
        "epochs": epochs,
        "best_loss": best_loss,
        "n_images": len(dataset),
        "device": str(device),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "history": history,
    }
    with open(save_dir / "simclr_history.json", "w") as f:
        json.dump(meta, f, indent=2)

    logger.info(f"SimCLR backbone saved to {backbone_path}")
    return backbone_path


# ═══════════════════════════════════════════════════════════
# Stage 2: Supervised Grading Training
# ═══════════════════════════════════════════════════════════

def train_grading(
    image_dir: Path = IMAGE_DIR,
    csv_path: Path | None = None,
    epochs: int = EPOCHS_GRADING,
    batch_size: int = BATCH_SIZE_GRADING,
    lr: float = LR_GRADING,
    save_dir: Path = ARTIFACTS_DIR,
    simclr_backbone_path: Path | None = None,
) -> Path:
    """Train supervised grading model with pseudo-labels.

    Steps:
    1. Build image-record linkage and pseudo-labels
    2. Optionally load SimCLR-pretrained backbone
    3. Train fusion model (CNN + metadata → grade + viability)
    4. Save model weights and metadata

    Returns path to saved model.
    """
    if not HAS_TORCH:
        raise ImportError("PyTorch is required for grading training")

    from .linkage import build_grade_labels, build_image_record_mapping
    from .models import EmbryoGradingModel
    from .preprocessing import GradingDataset, get_eval_transforms, get_train_transforms

    _set_seed()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Grading training on {device}")

    # ── Build labels ──
    if csv_path is None:
        from .config import PROJECT_ROOT
        csv_candidates = list(Path(PROJECT_ROOT / "docs" / "dataset").glob("*ET Data*"))
        if not csv_candidates:
            raise FileNotFoundError("No ET Data CSV found in docs/dataset/")
        csv_path = csv_candidates[0]

    mapping = build_image_record_mapping(image_dir, csv_path)
    image_paths, labels_list, meta_list = build_grade_labels(mapping)
    n_samples = len(image_paths)
    logger.info(f"Labelled samples: {n_samples}")

    if n_samples < 20:
        raise ValueError(f"Too few labelled samples ({n_samples}), need ≥20")

    # ── Prepare datasets ──
    # 80/20 train/val split
    n_train = int(0.8 * n_samples)
    train_paths, val_paths = image_paths[:n_train], image_paths[n_train:]
    train_labels, val_labels = labels_list[:n_train], labels_list[n_train:]
    train_meta, val_meta = meta_list[:n_train], meta_list[n_train:]

    train_dataset = GradingDataset(train_paths, train_labels, train_meta, get_train_transforms())
    val_dataset = GradingDataset(val_paths, val_labels, val_meta, get_eval_transforms())

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True, num_workers=0, drop_last=True,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False, num_workers=0,
    )

    logger.info(f"Train: {len(train_dataset)}, Val: {len(val_dataset)}")

    # ── Model ──
    model = EmbryoGradingModel(
        backbone_feature_dim=BACKBONE_FEATURE_DIM,
        metadata_output_dim=32,
        n_grades=NUM_GRADES,
        freeze_backbone=True,
    ).to(device)

    # Load SimCLR pretrained backbone if available
    if simclr_backbone_path is None:
        simclr_backbone_path = save_dir / "simclr_backbone.pt"

    if simclr_backbone_path.exists():
        logger.info("Loading SimCLR pretrained backbone")
        state = torch.load(simclr_backbone_path, map_location=device, weights_only=True)
        model.backbone.load_state_dict(state, strict=False)
    else:
        logger.info("No SimCLR backbone found, using ImageNet weights")

    # ── Loss functions ──
    # Class weights for imbalanced pseudo-labels
    import collections
    class_counts = collections.Counter(labels_list)
    total = n_samples
    weights = torch.tensor(
        [total / (NUM_GRADES * class_counts.get(c, 1)) for c in range(NUM_GRADES)],
        dtype=torch.float32,
    ).to(device)

    grade_criterion = nn.CrossEntropyLoss(weight=weights)
    viability_criterion = nn.BCELoss()

    # ── Optimizer ──
    # Higher LR for new layers, lower for backbone
    backbone_params = [p for n, p in model.named_parameters() if "backbone" in n and p.requires_grad]
    other_params = [p for n, p in model.named_parameters() if "backbone" not in n]

    optimizer = optim.AdamW([
        {"params": backbone_params, "lr": lr * 0.1},
        {"params": other_params, "lr": lr},
    ], weight_decay=1e-4)

    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

    # ── Training loop ──
    best_val_loss = float("inf")
    best_epoch = 0
    history = []
    patience_counter = 0
    max_patience = 10

    for epoch in range(1, epochs + 1):
        # Train
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        for batch in train_loader:
            images = batch["image"].to(device)
            grade_labels = batch["grade_label"].to(device)
            viability_labels = batch["viability_label"].float().to(device)
            numeric_meta = batch["numeric_meta"].to(device)
            categorical_meta = {k: v.to(device) for k, v in batch["categorical_meta"].items()}

            grade_logits, viability_pred = model(images, numeric_meta, categorical_meta)

            loss_g = grade_criterion(grade_logits, grade_labels)
            loss_v = viability_criterion(viability_pred, viability_labels)
            loss = loss_g + 0.5 * loss_v  # Grade is primary objective

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            train_loss += loss.item() * images.size(0)
            train_correct += (grade_logits.argmax(1) == grade_labels).sum().item()
            train_total += images.size(0)

        avg_train_loss = train_loss / max(train_total, 1)
        train_acc = train_correct / max(train_total, 1)

        # Validate
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for batch in val_loader:
                images = batch["image"].to(device)
                grade_labels = batch["grade_label"].to(device)
                viability_labels = batch["viability_label"].float().to(device)
                numeric_meta = batch["numeric_meta"].to(device)
                categorical_meta = {k: v.to(device) for k, v in batch["categorical_meta"].items()}

                grade_logits, viability_pred = model(images, numeric_meta, categorical_meta)

                loss_g = grade_criterion(grade_logits, grade_labels)
                loss_v = viability_criterion(viability_pred, viability_labels)
                loss = loss_g + 0.5 * loss_v

                val_loss += loss.item() * images.size(0)
                val_correct += (grade_logits.argmax(1) == grade_labels).sum().item()
                val_total += images.size(0)

        avg_val_loss = val_loss / max(val_total, 1)
        val_acc = val_correct / max(val_total, 1)

        scheduler.step(avg_val_loss)

        history.append({
            "epoch": epoch,
            "train_loss": avg_train_loss,
            "train_acc": train_acc,
            "val_loss": avg_val_loss,
            "val_acc": val_acc,
        })

        if epoch % 5 == 0 or epoch == 1:
            logger.info(
                f"Epoch {epoch}/{epochs} | "
                f"Train Loss: {avg_train_loss:.4f} Acc: {train_acc:.3f} | "
                f"Val Loss: {avg_val_loss:.4f} Acc: {val_acc:.3f}"
            )

        # Early stopping
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            best_epoch = epoch
            patience_counter = 0

            save_dir.mkdir(parents=True, exist_ok=True)
            model_path = save_dir / "grading_model.pt"
            torch.save(model.state_dict(), model_path)
        else:
            patience_counter += 1
            if patience_counter >= max_patience:
                logger.info(f"Early stopping at epoch {epoch} (best: {best_epoch})")
                break

    # Save training metadata
    meta = {
        "type": "grading_model",
        "best_epoch": best_epoch,
        "best_val_loss": best_val_loss,
        "final_val_acc": history[-1]["val_acc"],
        "n_train": len(train_dataset),
        "n_val": len(val_dataset),
        "n_grades": NUM_GRADES,
        "label_distribution": dict(class_counts),
        "device": str(device),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "history": history,
    }
    with open(save_dir / "grading_history.json", "w") as f:
        json.dump(meta, f, indent=2, default=str)

    model_path = save_dir / "grading_model.pt"
    logger.info(f"Best grading model saved to {model_path} (epoch {best_epoch})")
    return model_path


# ═══════════════════════════════════════════════════════════
# Full Pipeline
# ═══════════════════════════════════════════════════════════

def run_full_pipeline(image_dir: Path = IMAGE_DIR, csv_path: Path | None = None):
    """Run complete two-stage training pipeline.

    Stage 1: SimCLR pretraining (self-supervised)
    Stage 2: Supervised grading (with pseudo-labels)
    """
    logging.basicConfig(level=logging.INFO)

    logger.info("=" * 60)
    logger.info("Stage 1: SimCLR Self-Supervised Pretraining")
    logger.info("=" * 60)
    backbone_path = train_simclr(image_dir=image_dir)

    logger.info("=" * 60)
    logger.info("Stage 2: Supervised Grading Training")
    logger.info("=" * 60)
    model_path = train_grading(
        image_dir=image_dir,
        csv_path=csv_path,
        simclr_backbone_path=backbone_path,
    )

    logger.info("=" * 60)
    logger.info(f"Training complete! Model: {model_path}")
    logger.info("=" * 60)
    return model_path


if __name__ == "__main__":
    run_full_pipeline()
