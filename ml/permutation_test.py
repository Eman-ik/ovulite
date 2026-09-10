#!/usr/bin/env python3
"""Permutation test: is the pregnancy model's discrimination real?

A low ROC-AUC is not self-interpreting. 0.55 could be weak-but-genuine signal,
or it could be exactly what shuffled labels produce at this sample size. The
only way to tell is to measure the null directly: refit the same pipeline on
permuted labels and see where the observed value falls in that distribution.

Result on the current dataset (n=476, 136 positives, 16 features):

    logistic  observed 0.552   null 0.501 +/- 0.040   permutation p = 0.143
    forest    observed 0.572   null 0.503 +/- 0.049   permutation p = 0.190

Both observed values sit *inside* the 95% null range. The model is not
distinguishable from chance, and this is not a split artefact -- see
ml/diagnose_split.py, which shows the same conclusion under pooled CV,
within-regime CV and rolling-origin evaluation.

Events per feature is 8.5, below the 10-20 rule of thumb, so the model is
underpowered by construction as well.

Run:  python -m ml.permutation_test
"""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
warnings.filterwarnings("ignore")
import numpy as np  # noqa: E402
from ml.config import SEED, TARGET_COL  # noqa: E402
from ml.diagnose_split import grouped_cv_auc  # noqa: E402
from ml.features import build_feature_matrix  # noqa: E402


def main() -> None:
    df = build_feature_matrix().drop(columns=["et_number"], errors="ignore")
    df = df.sort_values("et_date", kind="stable").reset_index(drop=True)
    y = df[TARGET_COL].values
    print(f"n={len(df)}  positives={y.sum()}  features=16")
    print(f"events-per-feature = {y.sum()/16:.1f}  (10-20 is the usual minimum for stable fitting)\n")

    obs = {m: grouped_cv_auc(df, m)[0] for m in ("logistic", "forest")}
    print("observed pooled-CV AUC:", {k: round(v,3) for k,v in obs.items()})

    rng = np.random.default_rng(SEED)
    null = {"logistic": [], "forest": []}
    for i in range(20):
        sh = df.copy(); sh[TARGET_COL] = rng.permutation(y)
        for m in null:
            a,_ = grouped_cv_auc(sh, m)
            if a is not None: null[m].append(a)

    print("\nnull distribution (labels shuffled, 20 runs):")
    for m, vals in null.items():
        v = np.array(vals); o = obs[m]
        p = (np.sum(v >= o) + 1) / (len(v) + 1)
        print(f"  {m:<9} null mean={v.mean():.3f} sd={v.std():.3f}  95% null range={np.percentile(v,2.5):.3f}-{np.percentile(v,97.5):.3f}"
              f"   observed={o:.3f}  permutation p={p:.3f}")


if __name__ == "__main__":
    main()
