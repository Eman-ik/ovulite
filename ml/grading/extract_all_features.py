#!/usr/bin/env python
"""Extract morphometrics for every Rocha image, and check them against the published values.

Two outputs:

1. ``extracted_features.csv`` — this pipeline's measurements for all 482 images.
   The grader is retrained on these, so training and inference share one code
   path and a newly uploaded photo is measured exactly as the training set was.

2. A per-feature agreement report against Rocha's published columns. This is a
   *diagnostic*, not a gate. High agreement means the reimplementation tracks
   theirs; low agreement means the two measure different things, which matters
   only for citing their numbers, not for whether ours carry signal.

Spearman rather than Pearson: the question is whether the two rank embryos the
same way, not whether they share a scale. Several features here are deliberately
normalised differently (Area ICM is a fraction of the disc, not a pixel count).

Run:  python -m ml.grading.extract_all_features
"""

from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .config import PROJECT_ROOT
from .morphometrics import FEATURE_NAMES, extract_features
from .real_labels import LABELS_CSV, load_labeled_images

OUT_DIR = PROJECT_ROOT / "ml" / "artifacts" / "grading" / "extracted"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    images = load_labeled_images()
    if args.limit:
        images = images.head(args.limit)

    rows, failures = [], []
    started = time.time()
    for i, row in images.iterrows():
        try:
            features = extract_features(row["image_path"])
        except Exception as exc:  # a bad image must not kill the batch
            failures.append({"figure_name": row["figure_name"], "error": str(exc)})
            continue
        features["figure_name"] = row["figure_name"]
        features["grade_class"] = int(row["grade_class"])
        rows.append(features)
        if (i + 1) % 50 == 0:
            rate = (time.time() - started) / (i + 1)
            print(f"  {i+1}/{len(images)}  ({rate:.2f}s/image)", flush=True)

    extracted = pd.DataFrame(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    extracted.to_csv(OUT_DIR / "extracted_features.csv", index=False)

    print(f"\nextracted {len(extracted)}/{len(images)} in {(time.time()-started)/60:.1f} min")
    if failures:
        print(f"failures: {len(failures)}")
        for f in failures[:5]:
            print(f"  {f['figure_name']}: {f['error'][:70]}")

    # ── Agreement with the published values ──
    published = pd.read_csv(LABELS_CSV)
    merged = extracted.merge(
        published, on="figure_name", how="inner", suffixes=("_ours", "_theirs")
    )

    report = []
    for name in FEATURE_NAMES:
        theirs_col = next(
            (c for c in (f"{name}_theirs", name, f"{name} ", name.strip()) if c in merged.columns),
            None,
        )
        ours_col = f"{name}_ours" if f"{name}_ours" in merged.columns else name
        if theirs_col is None or ours_col not in merged.columns:
            report.append({"feature": name, "spearman": None, "note": "no matching published column"})
            continue
        a = pd.to_numeric(merged[ours_col], errors="coerce")
        b = pd.to_numeric(merged[theirs_col], errors="coerce")
        ok = a.notna() & b.notna()
        if ok.sum() < 30 or a[ok].nunique() < 2 or b[ok].nunique() < 2:
            report.append({"feature": name, "spearman": None, "note": "insufficient variation"})
            continue
        rho = float(spearmanr(a[ok], b[ok]).statistic)
        report.append({"feature": name, "spearman": round(rho, 3), "note": ""})

    (OUT_DIR / "agreement_with_published.json").write_text(
        json.dumps({"features": report, "failures": failures}, indent=2), encoding="utf-8"
    )

    scored = [r for r in report if r["spearman"] is not None]
    strong = [r for r in scored if abs(r["spearman"]) >= 0.6]
    moderate = [r for r in scored if 0.3 <= abs(r["spearman"]) < 0.6]
    weak = [r for r in scored if abs(r["spearman"]) < 0.3]

    print("\nagreement with Rocha's published values (Spearman |rho|):")
    print(f"  strong  >=0.6 : {len(strong):>2} / {len(scored)}")
    print(f"  moderate 0.3-0.6: {len(moderate):>2}")
    print(f"  weak    <0.3  : {len(weak):>2}")
    print("\n  strongest:")
    for r in sorted(scored, key=lambda r: -abs(r["spearman"]))[:8]:
        print(f"    {r['feature']:<20} {r['spearman']:+.3f}")
    print("\n  weakest:")
    for r in sorted(scored, key=lambda r: abs(r["spearman"]))[:6]:
        print(f"    {r['feature']:<20} {r['spearman']:+.3f}")
    print(f"\nwritten: {OUT_DIR}")


if __name__ == "__main__":
    main()
