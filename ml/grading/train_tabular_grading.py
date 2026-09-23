#!/usr/bin/env python
"""Tabular embryo grading on the published morphometrics.

Why this is the baseline now
----------------------------
A fine-tuned EfficientNet-B0 on 335 training images reaches 0.542 accuracy. A
plain L2 logistic regression on the 36 morphometric variables Rocha et al.
published alongside the same images reaches 0.611 — better, far cheaper, and
fully interpretable. With a training set this small the CNN is starved, while
the morphometrics already encode what an embryologist looks at: inner-cell-mass
area and eccentricity, trophectoderm texture, grey-level distribution.

Circularity was checked before trusting this. Out-of-sample, the morphometrics
reproduce the three individual graders at only 0.50-0.65 (5-fold CV), nowhere
near the ~1.0 that would appear if a rater were computed from these same
variables. The labels are genuine judgements, so the signal is real.

Two feature sources
-------------------
``--features published`` uses Rocha's own values. It is a research benchmark
only: those numbers came from their pipeline and cannot be produced for a new
photo, so a model fitted to them is not servable.

``--features extracted`` uses ``ml/grading/morphometrics.py``, this repo's own
extractor. That is what ``POST /grade/embryo`` now serves, because training and
inference then measure identically. It scores 0.587 +/- 0.041 cross-validated,
statistically indistinguishable from the published-feature model and ahead of
every CNN arm.

Honest ceiling
--------------
The label is the modal grade of three embryologists who agree unanimously on
only 58.7% of these images (pairwise Cohen's kappa 0.411-0.727). Anything near
0.75 is at the label's noise floor, not headroom.

Run:  python -m ml.grading.train_tabular_grading
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .config import PROJECT_ROOT, SEED
from .ordinal import ordinal_metrics
from .real_labels import (
    CLASS_NAMES,
    load_labeled_images,
    load_morphometrics,
    morphometric_columns,
    stratified_split,
)

ARTIFACT_ROOT = PROJECT_ROOT / "ml" / "artifacts" / "grading"
CNN_BASELINE = {"accuracy": 0.5417, "macro_f1": 0.4753, "grade2_recall": 0.1923}
MAJORITY = 0.403


class FrankHallOrdinal(ClassifierMixin, BaseEstimator):
    """Ordinal classification by binary decomposition (Frank & Hall, 2001).

    Fits one binary model per threshold — "is grade > 1?", "is grade > 2?" —
    then differences the cumulative probabilities into per-class ones. Unlike
    CORAL the thresholds do not share weights, so monotonicity is enforced
    afterwards by clamping; on tabular data that is cheap and works well.

    Included because grades are ordered and a 1-vs-3 error is worse than a
    1-vs-2 one, which plain multinomial fitting ignores.
    """

    def __init__(self, base_estimator=None, n_classes: int = 3):
        self.base_estimator = base_estimator
        self.n_classes = n_classes

    def fit(self, X, y):
        base = self.base_estimator if self.base_estimator is not None else LogisticRegression(
            max_iter=5000, class_weight="balanced"
        )
        self.classes_ = np.arange(self.n_classes)
        self.models_ = []
        for k in range(self.n_classes - 1):
            model = clone(base)
            model.fit(X, (np.asarray(y) > k).astype(int))
            self.models_.append(model)
        return self

    def predict_proba(self, X):
        cum = np.column_stack([m.predict_proba(X)[:, 1] for m in self.models_])
        # Enforce P(y>0) >= P(y>1); independent fits can violate it.
        cum = np.minimum.accumulate(cum, axis=1)
        probs = np.zeros((len(X), self.n_classes))
        probs[:, 0] = 1 - cum[:, 0]
        for k in range(1, self.n_classes - 1):
            probs[:, k] = cum[:, k - 1] - cum[:, k]
        probs[:, -1] = cum[:, -1]
        probs = np.clip(probs, 0, None)
        return probs / probs.sum(axis=1, keepdims=True)

    def predict(self, X):
        return self.predict_proba(X).argmax(axis=1)


def candidates(seed: int):
    logistic = lambda: LogisticRegression(max_iter=5000, class_weight="balanced", random_state=seed)
    return {
        "logistic_l2": make_pipeline(StandardScaler(), logistic()),
        "logistic_elasticnet": make_pipeline(
            StandardScaler(),
            LogisticRegression(
                max_iter=5000, penalty="elasticnet", solver="saga", l1_ratio=0.5,
                C=0.5, class_weight="balanced", random_state=seed,
            ),
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=500, class_weight="balanced", random_state=seed, n_jobs=-1
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(random_state=seed),
        "ordinal_logistic": make_pipeline(
            StandardScaler(), FrankHallOrdinal(base_estimator=logistic())
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument(
        "--features", choices=["published", "extracted"], default="published",
        help="published = Rocha's own values (benchmark only, not servable); "
             "extracted = this repo's ml/grading/morphometrics.py (what ships)",
    )
    args = parser.parse_args()

    labels = load_labeled_images()
    if args.features == "extracted":
        # Our own pipeline, so training and inference measure identically.
        extracted = pd.read_csv(
            PROJECT_ROOT / "ml" / "artifacts" / "grading" / "extracted" / "extracted_features.csv"
        )
        features = [c for c in extracted.columns if c not in ("figure_name", "grade_class")]
        morph = extracted.drop(columns=["grade_class"], errors="ignore")
    else:
        morph = load_morphometrics()
        features = morphometric_columns()
    data = labels.merge(morph, on="figure_name", how="inner", validate="one_to_one")

    # Identical split to the CNN arms, so the comparison is like for like.
    train_df, val_df, test_df = stratified_split(data, seed=args.seed)
    fit_df = pd.concat([train_df, val_df], ignore_index=True)

    X_fit, y_fit = fit_df[features].to_numpy(), fit_df["grade_class"].to_numpy()
    X_test, y_test = test_df[features].to_numpy(), test_df["grade_class"].to_numpy()

    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=4, random_state=args.seed)
    results = {}

    print(f"fit on {len(fit_df)} (train+val), held-out test {len(test_df)}")
    print(f"features: {len(features)}\n")
    print("cross-validated on the fitting set (5-fold x 4 repeats):\n")

    for name, model in candidates(args.seed).items():
        scores = cross_val_score(model, X_fit, y_fit, cv=cv, scoring="accuracy", n_jobs=-1)
        results[name] = {"cv_accuracy_mean": float(scores.mean()), "cv_accuracy_std": float(scores.std())}
        print(f"  {name:<24} {scores.mean():.3f} +/- {scores.std():.3f}")

    best_name = max(results, key=lambda k: results[k]["cv_accuracy_mean"])
    print(f"\nselected by CV: {best_name}")

    best = candidates(args.seed)[best_name]
    best.fit(X_fit, y_fit)
    y_pred = best.predict(X_test)

    metrics = ordinal_metrics(y_test, y_pred)
    metrics["macro_f1"] = float(f1_score(y_test, y_pred, average="macro"))
    metrics["confusion_matrix"] = confusion_matrix(y_test, y_pred).tolist()
    metrics["classification_report"] = classification_report(
        y_test, y_pred, target_names=CLASS_NAMES, output_dict=True, zero_division=0
    )

    # A single 72-image test split is small; state the interval rather than
    # letting a point estimate look more precise than it is.
    n = len(y_test)
    acc = metrics["accuracy"]
    half = 1.96 * float(np.sqrt(acc * (1 - acc) / n))
    metrics["accuracy_95ci"] = [round(max(0.0, acc - half), 3), round(min(1.0, acc + half), 3)]

    # Which morphometrics carry the signal — the interpretability argument for
    # preferring this model is only worth making if it is actually inspectable.
    importance = None
    if best_name.startswith("logistic") or best_name == "ordinal_logistic":
        est = best.steps[-1][1]
        coefs = (
            np.abs(np.column_stack([m.coef_[0] for m in est.models_])).mean(axis=1)
            if isinstance(est, FrankHallOrdinal)
            else np.abs(est.coef_).mean(axis=0)
        )
        importance = sorted(zip(features, coefs.tolist()), key=lambda t: -t[1])[:10]
    elif hasattr(best, "feature_importances_"):
        importance = sorted(
            zip(features, best.feature_importances_.tolist()), key=lambda t: -t[1]
        )[:10]

    artifact_dir = ARTIFACT_ROOT / f"tabular_{args.features}_v1"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    import joblib

    joblib.dump({"model": best, "features": features}, artifact_dir / "model.joblib")

    meta = {
        "type": "embryo_grade_classifier",
        "family": "tabular",
        "feature_source": args.features,
        "servable": args.features == "extracted",
        "selected_model": best_name,
        "class_names": CLASS_NAMES,
        "n_features": len(features),
        "features": features,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "split": {"fit": len(fit_df), "test": len(test_df)},
        "cv_results": results,
        "test_metrics": metrics,
        "comparison": {"cnn_efficientnet_b0": CNN_BASELINE, "majority_class": MAJORITY},
        "top_features": importance,
        "caveats": [
            "Consumes 36 derived morphometrics, not an image. Ovulite cannot yet compute "
            "them for a newly uploaded photo — the ICM geometry needs a segmentation step "
            "that does not exist. Not servable from POST /grade/embryo until it does.",
            "The label is the modal grade of three embryologists who agree unanimously on "
            "58.7% of these images (kappa 0.411-0.727). That agreement is the ceiling.",
            "Test split is 72 images; the 95% interval on accuracy is roughly +/-0.11.",
            "Predicts IETS grade only, never pregnancy. Do not feed its output into the "
            "pregnancy model — that would manufacture circular leakage.",
        ],
    }
    (artifact_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    rep = metrics["classification_report"]
    print("\n" + "=" * 74)
    print(f"{'':<26}{'tabular':>12}{'CNN':>12}{'majority':>12}")
    print("-" * 74)
    print(f"{'accuracy':<26}{acc:>12.3f}{CNN_BASELINE['accuracy']:>12.3f}{MAJORITY:>12.3f}")
    print(f"{'macro F1':<26}{metrics['macro_f1']:>12.3f}{CNN_BASELINE['macro_f1']:>12.3f}{'-':>12}")
    print(f"{'Grade 2 recall':<26}{rep[CLASS_NAMES[1]]['recall']:>12.3f}{CNN_BASELINE['grade2_recall']:>12.3f}{'-':>12}")
    print(f"{'MAE (grades)':<26}{metrics['mae_grades']:>12.3f}{'-':>12}{'-':>12}")
    print(f"{'adjacent accuracy':<26}{metrics['adjacent_accuracy']:>12.3f}{'-':>12}{'-':>12}")
    print("=" * 74)
    print(f"95% CI on accuracy: {metrics['accuracy_95ci']}  (n=72)")
    print("Human ceiling: unanimous on 58.7%; pairwise kappa 0.411-0.727.")
    if importance:
        print("\ntop morphometrics:")
        for name, w in importance[:8]:
            print(f"  {name.strip():<22} {w:.4f}")


if __name__ == "__main__":
    main()
