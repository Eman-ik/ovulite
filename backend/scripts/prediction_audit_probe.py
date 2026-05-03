"""Probe prediction pipeline using real ET records from PostgreSQL.

Usage:
  D:/Ovulite new/backend/venv/Scripts/python.exe backend/scripts/prediction_audit_probe.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import joinedload

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ["DATABASE_URL"] = (
    "postgresql://ovulite:ovulite_dev_password@localhost:5432/ovulite_api_audit"
)

from scripts.api_audit_runner import ensure_audit_database, setup_schema

from app.main import app
from app.database import SessionLocal
from app.models.embryo import Embryo
from app.models.et_transfer import ETTransfer
from scripts.ingest_et_data import ingest_et_data

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "docs" / "dataset" / "ET Summary - ET Data.csv"


def _build_payload(transfer: ETTransfer) -> dict:
    embryo = transfer.embryo
    donor = embryo.donor if embryo else None
    sire = embryo.sire if embryo else None

    return {
        "transfer_id": transfer.transfer_id,
        "cl_measure_mm": float(transfer.cl_measure_mm) if transfer.cl_measure_mm is not None else None,
        "embryo_stage": embryo.stage if embryo else None,
        "embryo_grade": embryo.grade if embryo else None,
        "heat_day": transfer.heat_day,
        "donor_bw_epd": float(donor.birth_weight_epd) if donor and donor.birth_weight_epd is not None else None,
        "sire_bw_epd": float(sire.birth_weight_epd) if sire and sire.birth_weight_epd is not None else None,
        "days_opu_to_et": (transfer.et_date - embryo.opu_date).days if embryo and embryo.opu_date and transfer.et_date else None,
        "bc_score": float(transfer.bc_score) if transfer.bc_score is not None else None,
        "cl_side": transfer.cl_side,
        "protocol_name": transfer.protocol.name if transfer.protocol else None,
        "fresh_or_frozen": embryo.fresh_or_frozen if embryo else None,
        "technician_name": transfer.technician.name if transfer.technician else None,
        "donor_breed": donor.breed if donor else None,
        "semen_type": sire.semen_type if sire else None,
        "customer_id": transfer.customer_id,
    }


def main() -> None:
    ensure_audit_database()
    setup_schema()

    session = SessionLocal()
    if session.query(ETTransfer).count() == 0 and DATASET_PATH.exists():
        stats = ingest_et_data(str(DATASET_PATH), session)
        session.commit()
        print(
            "Imported dataset:",
            f"rows_ingested={stats.get('rows_ingested', 0)}",
            f"rows_skipped={stats.get('rows_skipped', 0)}",
        )

    rows = (
        session.query(ETTransfer)
        .options(
            joinedload(ETTransfer.embryo).joinedload(Embryo.donor),
            joinedload(ETTransfer.embryo).joinedload(Embryo.sire),
            joinedload(ETTransfer.protocol),
            joinedload(ETTransfer.technician),
        )
        .filter(ETTransfer.embryo_id.isnot(None))
        .order_by(ETTransfer.transfer_id)
        .limit(5)
        .all()
    )

    print("=== REAL ET FIELD COVERAGE (first 5 transfers) ===")
    for transfer in rows:
        payload = _build_payload(transfer)
        non_null = sum(value is not None for value in payload.values())
        print(f"transfer_id={transfer.transfer_id} non_null_fields={non_null}/{len(payload)}")

    if not rows:
        print("No ET transfer rows found.")
        session.close()
        return

    first_payload = _build_payload(rows[0])
    with TestClient(app) as client:
        client.post("/auth/seed")
        login = client.post(
            "/auth/login",
            data={"username": "admin", "password": "ovulite2026"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token = login.json().get("access_token") if login.status_code == 200 else None
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        response = client.post("/predict/pregnancy", json=first_payload, headers=headers)
        print("=== PREDICTION RESULT ===")
        print(f"status={response.status_code}")
        print(f"body={response.text[:800]}")

    session.close()


if __name__ == "__main__":
    main()
