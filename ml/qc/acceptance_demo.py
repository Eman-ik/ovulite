#!/usr/bin/env python
"""Acceptance demonstration for the QC module.

Proves the detection chain end to end on one run:

    no data        -> declines, no crash
    normal data    -> baseline established
    injected fault -> Isolation Forest flags the batch that was broken
                   -> alert names the metric, period, severity and baseline

This adds no detector. Everything it exercises already existed in ml/qc; the
point is to show the chain works, and to state plainly where it does not reach.

Scope of what QC actually watches
---------------------------------
The pipeline reads the transfer-level ET CSV, so its feature space is pregnancy
rate, CL measurement and embryo grade, aggregated per technician per month.
Cleavage and blastocyst rates are not in it: those live on ivf_batches, and in
this database every one of those numbers was written by the demo seeder.
Monitoring them would be monitoring fabricated data.

No causal claims
----------------
An alert says a metric moved in a period, against what baseline, and how far.
It never says why. Protocol, technician and month changed together here, so
"technician X caused a drop" is exactly the inference the data cannot support.

Run:  python -m ml.qc.acceptance_demo
"""

from __future__ import annotations

import logging
import sys
import tempfile
from pathlib import Path

import pandas as pd

logging.disable(logging.INFO)

RULE = "-" * 74


def _header(title: str) -> None:
    print(f"\n{RULE}\n{title}\n{RULE}")


def _fmt(value) -> str:
    if value is None:
        return "none"
    return f"{value:.4f}" if isinstance(value, float) else str(value)


def _show_alerts(alerts: list[dict], limit: int = 8) -> None:
    if not alerts:
        print("  (no alerts)")
        return
    for a in alerts[:limit]:
        print(
            f"  [{str(a.get('severity', '?')).upper():<8}] {a.get('metric', '?'):<22}"
            f" period={str(a.get('period', '-')):<9}"
            f" observed={_fmt(a.get('metric_value')):<9}"
            f" baseline={_fmt(a.get('baseline_value'))}"
        )
        print(f"             {a.get('description', '')[:96]}")


def _chart_status(charts: dict) -> None:
    if not charts:
        print("  (no charts built)")
        return
    for metric, data in charts.items():
        status = data.get("status", "ok")
        have, need = data.get("periods_available"), data.get("periods_required")
        note = f"{have} periods, needs {need}" if have is not None else ""
        print(f"  {metric:<20} {status:<22} {note}")


def main() -> int:
    from ml.qc.features import build_qc_feature_matrix, load_et_data
    from ml.qc.run_pipeline import run_qc_pipeline
    from ml.qc.synthetic import inject_synthetic_anomalies, verify_detection

    scratch = Path(tempfile.mkdtemp(prefix="qc_acceptance_"))

    # -- 1. No data --
    _header("1. NO DATA: the pipeline declines instead of crashing")

    _, empty_batches = build_qc_feature_matrix(pd.DataFrame())
    print(f"  empty frame      -> {len(empty_batches)} batches, no exception")

    header_only = scratch / "empty.csv"
    header_only.write_text(
        "ET Date,ET Tech,Protocol,CL measure (mm),Embryo Grade,"
        "Embryo Stage 4-8,BCScore,1st PC Result,Heat day\n",
        encoding="utf-8",
    )
    no_data = run_qc_pipeline(csv_path=header_only)
    print(f"  header-only CSV  -> status={no_data['summary'].get('status')!r}, "
          f"{no_data['summary']['total_alerts']} alerts, no exception")
    no_data_ok = (
        len(empty_batches) == 0
        and no_data["summary"].get("status") == "no_data"
        and no_data["summary"]["total_alerts"] == 0
    )

    # -- 2. Normal state --
    _header("2. NORMAL STATE: real data, establishing the baseline")
    baseline = run_qc_pipeline(with_synthetic=False)
    summary, monthly = baseline["summary"], baseline["monthly_metrics"]

    print(f"  {summary['total_records']} records, {summary['total_batches']} "
          f"technician-month batches, {summary['technicians_analyzed']} technicians")
    print("\n  monthly history:")
    for _, row in monthly.iterrows():
        rate = row["pregnancy_rate"]
        rate_text = "no outcome yet" if pd.isna(rate) else f"{rate * 100:.1f}%"
        print(f"    {row['year_month']}  n={int(row['transfer_count']):>3}"
              f"  pregnancy {rate_text:>14}  CL {row['avg_cl_measure']:.1f}mm")

    print("\n  control charts:")
    _chart_status(baseline["charts"])

    print(f"\n  alerts on untouched data: {len(baseline['alerts'])}")
    _show_alerts(baseline["alerts"])

    # -- 3. Anomalous state --
    _header("3. ANOMALOUS STATE: injecting known faults")
    _, ground_truth = inject_synthetic_anomalies(load_et_data())
    print(f"  injected {len(ground_truth)} faults:")
    for g in ground_truth:
        print(f"    {g.get('type', '?'):<22} {g.get('technician', '?'):<10}"
              f" {g.get('period', '?'):<9} {str(g.get('description', ''))[:46]}")

    injected = run_qc_pipeline(with_synthetic=True)
    isummary = injected["summary"]
    print(f"\n  {isummary['total_records']} records "
          f"(was {summary['total_records']}), "
          f"{isummary['anomalous_batches']} batches flagged, "
          f"{isummary['total_alerts']} alerts")

    # -- 4. The detection chain --
    _header("4. DETECTION CHAIN: did it find what was broken?")
    detection = verify_detection(ground_truth, injected["anomalies"])
    print(f"  {detection['total_injected']} faults in "
          f"{detection['batches_injected']} distinct batches; "
          f"{detection['batches_detected']} of those batches flagged "
          f"(recall {detection['detection_rate']:.0%})")
    for hit in detection["detected"]:
        print(f"    FOUND  {hit['type']:<22} {hit['technician']}/{hit['period']}")
    for miss in detection["missed"]:
        print(f"    MISSED {miss['type']:<22} {miss['technician']}/{miss['period']}")
    print(f"  flagged but not injected: {detection['flagged_not_injected']}")

    # Is the shortfall just the flag budget? contamination=0.10 over 12 batches
    # buys about one flag, so the obvious reading is that the detector ran out
    # of room. Sweeping it settles that rather than assuming either way.
    print("\n  Ruling out the flag budget -- same data, contamination swept:")
    from sklearn.ensemble import IsolationForest

    from ml.qc.config import IFOREST_CONTAMINATION, IFOREST_N_ESTIMATORS, SEED

    X_inj, batch_inj = build_qc_feature_matrix(
        inject_synthetic_anomalies(load_et_data())[0]
    )
    truth_keys = {(g["technician"], g["period"]) for g in ground_truth}
    for contamination in (IFOREST_CONTAMINATION, 0.2, 0.3, 0.42):
        model = IsolationForest(
            contamination=contamination,
            n_estimators=IFOREST_N_ESTIMATORS,
            random_state=SEED,
        ).fit(X_inj)
        flagged = {
            (row.technician_name, row.period)
            for row, pred in zip(batch_inj.itertuples(), model.predict(X_inj))
            if pred == -1
        }
        print(f"    contamination={contamination:.2f}  "
              f"flagged {len(flagged):>2}/{len(batch_inj)}  "
              f"injected batches found {len(flagged & truth_keys)}/{len(truth_keys)}  "
              f"false positives {len(flagged - truth_keys)}")
    print("  Flagging 5 of 12 batches still finds the same one. The detector")
    print("  does not rank the injected faults above this dataset's own")
    print("  variation: 12 technician-month batches over 4 technicians give it")
    print("  no cohort to call anything unusual against.")

    # -- 5. What an alert reports --
    _header("5. WHAT AN ALERT REPORTS")
    _show_alerts(injected["alerts"])

    required = ("severity", "metric", "period", "metric_value", "baseline_value")
    incomplete = [
        (a.get("metric"), f)
        for a in injected["alerts"] for f in required
        if a.get(f) in (None, "")
    ]

    # -- 6. No causal claims --
    _header("6. NO CAUSAL CLAIMS")
    causal = ("caused", "because", "due to", "responsible for", "blame", "led to")
    offenders = [
        a["description"] for a in injected["alerts"]
        if any(word in str(a.get("description", "")).lower() for word in causal)
    ]
    if offenders:
        for text in offenders[:3]:
            print(f"  CAUSAL LANGUAGE: {text[:92]}")
    else:
        print("  No alert claims a cause. Each reports metric, period, observed")
        print("  against baseline, and nothing more.")

    # -- Verdict --
    _header("VERDICT: REPORTING CONTRACT")
    alerts = injected["alerts"]
    checks = [
        ("no-data state", no_data_ok),
        ("normal-state baseline", not monthly.empty),
        ("anomalous state reaches an alert", bool(alerts)),
        ("severity reported", bool(alerts) and all(a.get("severity") for a in alerts)),
        ("affected period reported", bool(alerts) and all(a.get("period") for a in alerts)),
        ("affected metric reported", bool(alerts) and all(a.get("metric") for a in alerts)),
        ("historical baseline reported",
         bool(alerts) and all(a.get("baseline_value") is not None for a in alerts)),
        ("no causal claims", not offenders),
    ]
    for label, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")

    if incomplete:
        print(f"\n  incomplete alert fields: {sorted(set(incomplete))}")

    failed = [label for label, ok in checks if not ok]
    if failed:
        print(f"\n  FAILED: {', '.join(failed)}")
    else:
        print("\n  The chain is intact: data arrives, a fault reaches an alert, and")
        print("  the alert names its metric, period, severity and baseline.")

    # Reported, not scored. The contract above is a property of the code and
    # either holds or does not; detection quality is a measurement, and
    # printing it as PASS beside 25% would be the kind of green tick this
    # repository keeps having to remove.
    _header("VERDICT: DETECTION QUALITY")
    print(f"  {detection['batches_detected']} of {detection['batches_injected']} "
          f"injected batches found; {detection['flagged_not_injected']} flagged "
          "that were not injected.")
    unreported = detection["batches_injected"] - detection["batches_detected"]
    print(f"  {unreported} deliberately broken batches went unreported, and raising")
    print(f"  the contamination rate does not recover them. On {len(batch_inj)} "
          "technician-month")
    print("  batches the detector has no cohort to judge against, so this is a")
    print("  sample-size result, not a tuning one.")

    periods = ", ".join(
        f"{m} {d.get('periods_available')}" for m, d in baseline["charts"].items()
    )
    needed = next(
        (d.get("periods_required") for d in baseline["charts"].values()), 8
    )
    print("\n  Limits of this demonstration:")
    print(f"   - Control charts need {needed} monthly periods; this dataset has")
    print(f"     {periods}. Detection here is Isolation Forest alone;")
    print("     EWMA and CUSUM run only on longer series.")
    print("   - Cleavage and blastocyst rates are outside the feature space:")
    print("     they live on ivf_batches and are seeded demo values.")
    print("   - Faults are injected, not observed. Recall here is recall against")
    print("     a generator, not against real laboratory failure.")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
