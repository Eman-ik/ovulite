"""Ordinal (rank-consistent) loss for embryo grading.

Why this exists
---------------
IETS grades are ordered: 1 (excellent) < 2 (fair) < 3 (poor). Plain
cross-entropy treats them as three unrelated labels, so confusing Grade 1 with
Grade 3 costs exactly the same as confusing Grade 1 with Grade 2. That is wrong
both statistically and clinically — an embryo called "fair" when it is "poor" is
a smaller error than one called "excellent".

It is also the concrete cause of the failure in the cross-entropy baseline
(``ml/artifacts/grading/real_labels_v1``): Grade 2 recall was **0.192**, with 13
of 26 middle-grade embryos pushed into Grade 3. With no ordering in the loss the
model has no reason to keep the middle class as a band between its neighbours,
so it collapses into the majority class on either side.

The method
----------
CORAL — COnsistent RAnk Logits (Cao, Mirjalili & Raschka, 2020, *Pattern
Recognition Letters*). A K-class ordinal problem is recast as K-1 binary
questions:

    P(y > 1),  P(y > 2)

Each shares one weight vector and gets its own bias. Sharing the weights is what
makes the predictions **rank-monotonic by construction**: the model can never
output P(y > 2) > P(y > 1), which an independent set of binary heads can, and
which produces incoherent probabilities that cannot be turned into a grade.

The predicted grade is then the number of thresholds passed:

    grade_index = sum_k [ P(y > k) > 0.5 ]

Reading the metrics
-------------------
Accuracy alone under-reports an ordinal model. Also track:

* **MAE in grade units** — how far off, not just how often.
* **Adjacent accuracy** — predictions within one grade. For a label whose own
  three human raters agree unanimously only 58.7% of the time, being within one
  grade is often the honest bar.
"""

from __future__ import annotations

import numpy as np

try:
    import torch
    import torch.nn as nn

    HAS_TORCH = True
except ImportError:  # pragma: no cover - torch is optional at import time
    HAS_TORCH = False
    nn = object  # type: ignore


def levels_from_labels(labels, n_classes: int):
    """Turn class indices into CORAL's cumulative binary targets.

    A label of class 1 (of 0,1,2) becomes ``[1, 0]``: it passed the first
    threshold (y > 0) but not the second (y > 1).
    """
    if not HAS_TORCH:
        raise ImportError("PyTorch required")
    labels = labels.view(-1, 1)
    thresholds = torch.arange(n_classes - 1, device=labels.device).view(1, -1)
    return (labels > thresholds).float()


class CoralLoss(nn.Module):
    """Rank-consistent ordinal loss with **per-threshold** imbalance weighting.

    The first version of this class weighted each *example* by its class weight,
    applied to the sum over both thresholds. That was wrong, and it had a
    specific, visible consequence: an example of the middle class was upweighted
    equally on "is y > 1?" and "is y > 2?", which pushes both thresholds the same
    way and never prises them apart. The two biases stayed at their zero
    initialisation (0.018 and -0.019, a gap of 0.037 in logit space), the
    Grade-2 band closed, and the model predicted the middle class exactly zero
    times across the whole test set.

    CORAL's actual formulation weights each binary subtask separately. Threshold
    k asks "is y > k?", which has its own positive rate, so it gets its own
    ``pos_weight`` in the standard binary-cross-entropy sense: negatives and
    positives are balanced *within* that threshold rather than across classes.
    """

    def __init__(self, n_classes: int = 3, pos_weights=None):
        super().__init__()
        if not HAS_TORCH:
            raise ImportError("PyTorch required")
        self.n_classes = n_classes
        self.register_buffer(
            "pos_weights",
            torch.as_tensor(pos_weights, dtype=torch.float32)
            if pos_weights is not None
            else torch.ones(n_classes - 1),
        )

    def forward(self, logits, labels):
        levels = levels_from_labels(labels, self.n_classes)
        return nn.functional.binary_cross_entropy_with_logits(
            logits, levels, pos_weight=self.pos_weights, reduction="mean"
        )


def threshold_pos_weights(labels, n_classes: int = 3):
    """``pos_weight`` per threshold: negatives / positives for "is y > k?"."""
    labels = np.asarray(labels)
    out = []
    for k in range(n_classes - 1):
        pos = float((labels > k).sum())
        neg = float((labels <= k).sum())
        out.append(neg / max(pos, 1.0))
    return out


def init_bias_from_prevalence(labels, n_classes: int = 3):
    """Starting biases at the cumulative log-odds of the training labels.

    Opens the band at the empirical class proportions instead of making the
    model discover a separation from zero — which, on 335 images, it did not.
    """
    labels = np.asarray(labels)
    n = len(labels)
    biases = []
    for k in range(n_classes - 1):
        p = float((labels > k).sum()) / max(n, 1)
        p = min(max(p, 1e-4), 1 - 1e-4)
        biases.append(float(np.log(p / (1 - p))))
    return biases


def logits_to_class(logits) -> "torch.Tensor":
    """Grade index = how many ordered thresholds the example clears."""
    return (torch.sigmoid(logits) > 0.5).sum(dim=1)


def logits_to_probs(logits) -> "torch.Tensor":
    """Per-class probabilities from the cumulative ones.

    P(y=0) = 1 - P(y>0);  P(y=k) = P(y>k-1) - P(y>k);  P(y=K-1) = P(y>K-2).
    Differences are clamped at zero: monotonicity holds by construction, but
    floating-point noise can still produce a tiny negative.
    """
    cum = torch.sigmoid(logits)
    ones = torch.ones(cum.size(0), 1, device=cum.device)
    zeros = torch.zeros(cum.size(0), 1, device=cum.device)
    upper = torch.cat([ones, cum], dim=1)
    lower = torch.cat([cum, zeros], dim=1)
    probs = (upper - lower).clamp(min=0.0)
    return probs / probs.sum(dim=1, keepdim=True).clamp(min=1e-8)


def ordinal_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Metrics that respect the ordering, alongside the usual ones."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    diff = np.abs(y_true - y_pred)
    return {
        "accuracy": float((y_true == y_pred).mean()),
        "mae_grades": float(diff.mean()),
        "adjacent_accuracy": float((diff <= 1).mean()),
        "off_by_two": int((diff >= 2).sum()),
    }
