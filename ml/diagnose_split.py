#!/usr/bin/env python3
"""Diagnose why the pregnancy model evaluates at chance.

The shipped artifact reports ROC-AUC 0.487 on a temporal holdout cut at
2025-12-01. That cut sits exactly on a regime boundary: the programme's
pregnancy rate roughly doubled in December 2025 (23.2% -> 43.6%), holding
protocol, farm, technician and breed constant.

The obvious story -- "the base rate shifted, so the model broke" -- does not
actually explain the number. **ROC-AUC is rank-based and invariant to class
prevalence.** A pure prior shift (P(Y) changes, P(X|Y) does not) degrades
calibration, not AUC. So AUC at chance means one of:

  A. Concept drift -- P(Y|X) itself changed across the boundary, so a model
     fit on the old regime genuinely mis-ranks the new one; or
  B. There is no learnable signal in these features at all, and the temporal
     split is a red herring.

Those imply completely different responses, so this script separates them by
evaluating the same model family under several schemes:

  1. temporal      -- the shipped split, for comparison
  2. pooled_cv     -- GroupKFold by donor over ALL data. Ignores deployment
                      realism on purpose: it asks only "is there signal?"
  3. pre_regime_cv -- GroupKFold within the pre-December rows only
  4. post_regime_cv-- GroupKFold within December+ only
  5. rolling       -- walk-forward origins, so no single cutoff decides

Grouping is by donor throughout: the same donor contributes many transfers,
and letting a donor straddle a fold leaks donor quality into validation.

Run:  python -m ml.diagnose_split
"""

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
warnings.filterwarnings("ignore")

from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402
from sklearn.model_selection import GroupKFold  # noqa: E402

from ml.config import SEED, TARGET_COL  # noqa: E402
from ml.features import build_feature_matrix, preprocess_for_model  # noqa: E402

REGIME_CUTOFF = pd.Timestamp("2025-12-01")


def _fit_predict(X_tr, y_tr, X_te, model: str):
    """Fit one model and return holdout probabilities.

    Two families on purpose: logistic captures monotone linear structure,
    random forest captures interactions and thresholds. If both sit at 0.5,
    the absence of signal is a property of the features, not the model class.
    """
    if model == "logistic":
        clf = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)
    else:
        clf = RandomForestClassifier(
            n_estimators=400,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=SEED,
            n_jobs=-1,
        )
    clf.fit(X_tr, y_tr)
    return clf.predict_proba(X_te)[:, 1]


def _auc(y_true, y_prob) -> float | None:
    """AUC, or None when the fold has only one class (undefined, not 0.5)."""
    if len(np.unique(y_true)) < 2:
        return None
    return roc_auc_score(y_true, y_prob)


def grouped_cv_auc(df: pd.DataFrame, model: str, n_folds: int = 5) -> tuple[float | None, int]:
    """Out-of-fold AUC under GroupKFold by donor.

    Pooling out-of-fold predictions before scoring (rather than averaging
    per-fold AUCs) keeps the estimate stable when folds are small.
    """
    if len(df) < n_folds * 4:
        return (None, len(df))
    groups = df["donor_tag"].fillna("UNKNOWN").values
    n_folds = min(n_folds, len(np.unique(groups)))
    if n_folds < 2:
        return (None, len(df))

    y = df[TARGET_COL].values
    oof = np.full(len(df), np.nan)
    gkf = GroupKFold(n_splits=n_folds)
    for tr_idx, te_idx in gkf.split(df, y, groups=groups):
        tr, te = df.iloc[tr_idx], df.iloc[te_idx]
        if len(np.unique(tr[TARGET_COL])) < 2:
            continue
        X_tr, _, _, enc = preprocess_for_model(tr, fit=True)
        X_te, _, _, _ = preprocess_for_model(te, fit=False, encoder_map=enc)
        oof[te_idx] = _fit_predict(X_tr, tr[TARGET_COL].values, X_te, model)

    mask = ~np.isnan(oof)
    return (_auc(y[mask], oof[mask]), int(mask.sum()))


def temporal_auc(df: pd.DataFrame, model: str, cutoff: pd.Timestamp) -> tuple[float | None, int, int]:
    """Train on everything before `cutoff`, evaluate on everything after."""
    tr = df[df["et_date"] < cutoff]
    te = df[df["et_date"] >= cutoff]
    if len(tr) < 20 or len(te) < 20 or len(np.unique(tr[TARGET_COL])) < 2:
        return (None, len(tr), len(te))
    X_tr, _, _, enc = preprocess_for_model(tr, fit=True)
    X_te, _, _, _ = preprocess_for_model(te, fit=False, encoder_map=enc)
    prob = _fit_predict(X_tr, tr[TARGET_COL].values, X_te, model)
    return (_auc(te[TARGET_COL].values, prob), len(tr), len(te))


def main() -> None:
    df = build_feature_matrix()
    df = df.drop(columns=["et_number"], errors="ignore")
    df = df.sort_values("et_date", kind="stable").reset_index(drop=True)

    pre = df[df["et_date"] < REGIME_CUTOFF]
    post = df[df["et_date"] >= REGIME_CUTOFF]

    print("=" * 74)
    print("DATA")
    print("=" * 74)
    for name, part in (("all", df), ("pre-Dec 2025", pre), ("Dec 2025+", post)):
        rate = part[TARGET_COL].mean() if len(part) else float("nan")
        print(f"  {name:<14} n={len(part):>4}  pregnancy_rate={rate:6.1%}  donors={part['donor_tag'].nunique()}")

    # Constant columns cannot contribute; naming them explains part of the result.
    feature_cols = [c for c in df.columns if c not in (TARGET_COL, "et_date", "donor_tag")]
    constant = [c for c in feature_cols if df[c].nunique(dropna=True) <= 1]
    print(f"\n  features: {len(feature_cols)}   constant (contribute nothing): {constant or 'none'}")

    print("\n" + "=" * 74)
    print("EVALUATION SCHEMES  (AUC 0.5 = chance; rank-based, so prevalence-invariant)")
    print("=" * 74)
    print(f"  {'scheme':<26} {'logistic':>10} {'forest':>10}   n_eval")
    print("  " + "-" * 62)

    rows: list[tuple[str, float | None, float | None, str]] = []

    auc_l, n_tr, n_te = temporal_auc(df, "logistic", REGIME_CUTOFF)
    auc_f, _, _ = temporal_auc(df, "forest", REGIME_CUTOFF)
    rows.append(("temporal (shipped split)", auc_l, auc_f, f"train {n_tr} / test {n_te}"))

    for label, part in (
        ("pooled CV (all data)", df),
        ("CV within pre-Dec", pre),
        ("CV within Dec+", post),
    ):
        auc_l, n_l = grouped_cv_auc(part, "logistic")
        auc_f, _ = grouped_cv_auc(part, "forest")
        rows.append((label, auc_l, auc_f, f"{n_l} oof"))

    for name, auc_l, auc_f, detail in rows:
        fl = f"{auc_l:.3f}" if auc_l is not None else "n/a"
        ff = f"{auc_f:.3f}" if auc_f is not None else "n/a"
        print(f"  {name:<26} {fl:>10} {ff:>10}   {detail}")

    print("\n  rolling origin (walk-forward):")
    for cutoff in ("2025-10-01", "2025-11-01", "2025-12-01"):
        ts = pd.Timestamp(cutoff)
        auc_l, n_tr, n_te = temporal_auc(df, "logistic", ts)
        auc_f, _, _ = temporal_auc(df, "forest", ts)
        fl = f"{auc_l:.3f}" if auc_l is not None else "n/a"
        ff = f"{auc_f:.3f}" if auc_f is not None else "n/a"
        print(f"    cut {cutoff}   logistic {fl:>6}  forest {ff:>6}   train {n_tr:>3} / test {n_te:>3}")

    # A label-permutation run fixes the true chance level for this sample size,
    # so a mediocre-looking AUC is not mistaken for weak-but-real signal.
    print("\n  permutation control (labels shuffled — establishes the null):")
    rng = np.random.default_rng(SEED)
    null = []
    for _ in range(5):
        shuffled = df.copy()
        shuffled[TARGET_COL] = rng.permutation(shuffled[TARGET_COL].values)
        auc, _ = grouped_cv_auc(shuffled, "logistic")
        if auc is not None:
            null.append(auc)
    if null:
        print(f"    pooled CV on shuffled labels: {np.mean(null):.3f} ± {np.std(null):.3f}  (n={len(null)} runs)")


if __name__ == "__main__":
    main()
