#!/usr/bin/env python
"""Generate pregnancy predictions for existing transfers through the live API.

This deliberately calls ``POST /predict/pregnancy`` over HTTP rather than
importing the predictor directly. Going through the endpoint exercises the path
a user actually takes — authentication, ``PREDICTION_RUN_ROLES``, feature
assembly, artifact load, the explanation surrogate and the database write — so a
successful run is evidence the prediction feature works, not just that a joblib
file can be unpickled.

Nothing here is invented. Every feature value is read from the transfer, embryo,
donor, sire, protocol and technician rows already in the database, and
``actual_outcome`` is copied from the recorded ``pc1_result``. The predictions
are whatever the deployed model says about real cases.

Usage
-----
    python scripts/generate_predictions.py --limit 200
    python scripts/generate_predictions.py --purge
"""

from __future__ import annotations

import argparse
import os
import sys

import psycopg2
import requests

DEFAULT_DSN = "postgresql://ovulite:ovulite_dev_password@127.0.0.1:5432/ovulite"
DEFAULT_API = "http://localhost:8000"

FEATURE_SQL = """
SELECT
    t.transfer_id,
    t.cl_measure_mm,
    e.stage              AS embryo_stage,
    e.grade              AS embryo_grade,
    t.heat_day,
    d.birth_weight_epd   AS donor_bw_epd,
    s.birth_weight_epd   AS sire_bw_epd,
    (t.et_date - e.opu_date) AS days_opu_to_et,
    t.bc_score,
    t.cl_side,
    p.name               AS protocol_name,
    e.fresh_or_frozen,
    tech.name            AS technician_name,
    d.breed              AS donor_breed,
    s.semen_type,
    t.customer_id,
    t.pc1_result
FROM et_transfers t
LEFT JOIN embryos e      ON e.embryo_id = t.embryo_id
LEFT JOIN donors d       ON d.donor_id = e.donor_id
LEFT JOIN sires s        ON s.sire_id = e.sire_id
LEFT JOIN protocols p    ON p.protocol_id = t.protocol_id
LEFT JOIN technicians tech ON tech.technician_id = t.technician_id
WHERE NOT EXISTS (SELECT 1 FROM predictions x WHERE x.transfer_id = t.transfer_id)
  AND t.cl_measure_mm IS NOT NULL
  AND e.stage IS NOT NULL
ORDER BY
    -- Transfers still awaiting a result first: those are the ones a prediction
    -- is actually for. Resolved cases follow, so the model can be scored.
    (t.pc1_result IS NOT NULL), t.et_date DESC
"""


def login(api: str, username: str, password: str) -> str:
    response = requests.post(
        f"{api}/auth/login",
        data={"username": username, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def as_payload(row: dict) -> dict:
    numeric = ("cl_measure_mm", "embryo_grade", "heat_day", "donor_bw_epd",
               "sire_bw_epd", "days_opu_to_et", "bc_score")
    payload = {"transfer_id": row["transfer_id"], "embryo_stage": int(row["embryo_stage"])}
    for key in numeric:
        value = row.get(key)
        payload[key] = None if value is None else float(value)
    payload["embryo_grade"] = None if row["embryo_grade"] is None else int(row["embryo_grade"])
    for key in ("cl_side", "protocol_name", "fresh_or_frozen", "technician_name",
                "donor_breed", "semen_type", "customer_id"):
        payload[key] = row.get(key)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", DEFAULT_DSN))
    parser.add_argument("--api", default=os.getenv("OVULITE_API", DEFAULT_API))
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="ovulite2026")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--purge", action="store_true")
    args = parser.parse_args()

    dsn = args.database_url
    if dsn.startswith("postgresql+"):
        dsn = "postgresql://" + dsn.split("://", 1)[1]
    if "@db:" in dsn:
        dsn = DEFAULT_DSN

    conn = psycopg2.connect(dsn)
    cur = conn.cursor()

    if args.purge:
        cur.execute("DELETE FROM predictions")
        conn.commit()
        print(f"Deleted {cur.rowcount} predictions.")
        return

    token = login(args.api, args.username, args.password)
    headers = {"Authorization": f"Bearer {token}"}

    cur.execute(FEATURE_SQL)
    names = [d[0] for d in cur.description]
    rows = [dict(zip(names, r)) for r in cur.fetchall()][: args.limit]
    print(f"{len(rows)} transfers eligible for prediction.")

    ok = failed = 0
    bands: dict[str, int] = {}
    outcomes: list[tuple[str, int]] = []
    for row in rows:
        response = requests.post(
            f"{args.api}/predict/pregnancy", json=as_payload(row), headers=headers, timeout=60
        )
        if response.status_code != 200:
            failed += 1
            if failed <= 3:
                print(f"  transfer {row['transfer_id']}: {response.status_code} {response.text[:180]}")
            continue
        ok += 1
        band = response.json().get("risk_band") or "unknown"
        bands[band] = bands.get(band, 0) + 1
        if row["pc1_result"] in ("Pregnant", "Open"):
            outcomes.append((row["pc1_result"], row["transfer_id"]))

    # The recorded result is the ground truth for any prediction on a resolved
    # transfer. Writing it back is what makes the model's own history screen
    # able to compare what it said against what happened.
    if outcomes:
        cur.executemany(
            """UPDATE predictions SET actual_outcome = %s,
                   actual_outcome_recorded_at = now()
               WHERE transfer_id = %s AND actual_outcome IS NULL""",
            outcomes,
        )
        conn.commit()

    print(f"\n  succeeded {ok}   failed {failed}")
    print(f"  risk bands {bands}")
    print(f"  outcomes recorded {len(outcomes)}")
    conn.close()
    if ok == 0:
        sys.exit("No prediction succeeded.")


if __name__ == "__main__":
    main()
