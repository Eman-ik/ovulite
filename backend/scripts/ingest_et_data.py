"""
CSV Ingestion Script — parses ET Data.csv into normalized database tables.

Handles:
- 488 ET records from the main CSV
- Data cleaning: dirty donor IDs, date parsing, duplicate columns
- Normalization into: donors, sires, recipients, technicians, protocols, embryos, et_transfers
- Missing value handling: '.' treated as NULL

Usage:
    python -m backend.scripts.ingest_et_data
    (or run directly from project root)
"""

import csv
import logging
import os
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

# Add project root so 'app' package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, Base
from app.models.donor import Donor
from app.models.embryo import Embryo
from app.models.et_transfer import ETTransfer
from app.models.protocol import Protocol
from app.models.recipient import Recipient
from app.models.sire import Sire
from app.models.technician import Technician

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Column indices in ET Data.csv
COL = {
    "et_number": 0,
    "lab": 1,
    "satellite": 2,
    "customer_id": 3,
    "et_date": 4,
    "farm_location": 5,
    "recipient_id_1": 6,
    "recipient_id_2": 7,
    "cow_or_heifer": 8,
    "heat_1": 9,
    "cl_side": 10,
    "cl_measure_mm": 11,
    "protocol": 12,
    "fresh_or_frozen": 13,
    "cane_number": 14,
    "freezing_date": 15,
    "et_tech": 16,
    "et_assistant": 17,
    "bc_score": 18,
    "embryo_stage": 19,
    "embryo_grade": 20,
    "heat_2": 21,
    "heat_day": 22,
    "pc1_date": 23,
    "pc1_result": 24,
    "pc2_date": 25,
    "pc2_result": 26,
    "fetal_sexing": 27,
    "opu_date": 28,
    "donor": 29,
    "donor_breed": 30,
    "donor_bw_epd": 31,
    "sire_name": 32,
    "sire_bw_epd": 33,
    "semen_type": 34,
    "sire_breed": 35,
    "client": 36,
    "dip_1": 37,
    "dip_2": 38,
}


def clean_str(val: str) -> str | None:
    """Strip whitespace, treat '.' and empty string as None."""
    val = val.strip()
    if val in ("", ".", "-", "N/A", "n/a"):
        return None
    return val


def parse_date(val: str) -> date | None:
    """Parse M/D/YYYY date format. Returns None for missing."""
    s = clean_str(val)
    if s is None:
        return None
    try:
        return datetime.strptime(s, "%m/%d/%Y").date()
    except ValueError:
        # Try other formats
        for fmt in ("%m-%d-%Y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
    logger.warning("Unparseable date: %r", val)
    return None


def parse_decimal(val: str) -> Decimal | None:
    """Parse numeric string to Decimal. Returns None for missing."""
    s = clean_str(val)
    if s is None:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        logger.warning("Unparseable decimal: %r", val)
        return None


def parse_int(val: str) -> int | None:
    """Parse integer string. Returns None for missing."""
    s = clean_str(val)
    if s is None:
        return None
    try:
        return int(float(s))
    except (ValueError, OverflowError):
        logger.warning("Unparseable int: %r", val)
        return None


def parse_bool_heat(val: str) -> bool | None:
    """Parse heat observed field. Various formats in data."""
    s = clean_str(val)
    if s is None:
        return None
    if s.lower() in ("yes", "y", "true", "1"):
        return True
    if s.lower() in ("no", "n", "false", "0"):
        return False
    return None


def normalize_cl_side(val: str) -> str | None:
    """Normalize CL side to Left/Right."""
    s = clean_str(val)
    if s is None:
        return None
    s_lower = s.lower()
    if s_lower == "left":
        return "Left"
    if s_lower == "right":
        return "Right"
    return s


def normalize_semen_type(val: str) -> str | None:
    """Normalize semen type to Conventional/Sexed/Unknown."""
    s = clean_str(val)
    if s is None:
        return None
    s_lower = s.lower()
    if "conventional" in s_lower:
        return "Conventional"
    if "sexed" in s_lower or "sorted" in s_lower or "female" in s_lower:
        return "Sexed"
    return "Unknown"


def normalize_pc_result(val: str) -> str | None:
    """Normalize pregnancy check result."""
    s = clean_str(val)
    if s is None:
        return None
    s_lower = s.lower()
    if "pregnant" in s_lower:
        return "Pregnant"
    if "open" in s_lower:
        return "Open"
    if "recheck" in s_lower:
        return "Recheck"
    return s


def normalize_donor_tag(val: str) -> str | None:
    """Clean donor tag. Some have dirty IDs (dates, etc.)."""
    s = clean_str(val)
    if s is None:
        return None
    # Some donor IDs are dates like 5/14/2025 — keep as-is, they're real tags
    return s


def get_or_create_donor(db: Session, tag_id: str, breed: str | None, bw_epd: Decimal | None) -> Donor:
    """Find existing donor by tag or create new one."""
    donor = db.query(Donor).filter(Donor.tag_id == tag_id).first()
    if donor:
        # Update breed/epd if we have better data
        if breed and not donor.breed:
            donor.breed = breed
        if bw_epd is not None and donor.birth_weight_epd is None:
            donor.birth_weight_epd = bw_epd
        return donor
    donor = Donor(tag_id=tag_id, breed=breed, birth_weight_epd=bw_epd)
    db.add(donor)
    db.flush()
    return donor


def get_or_create_sire(
    db: Session, name: str, breed: str | None, bw_epd: Decimal | None, semen_type: str | None
) -> Sire:
    """Find existing sire by name or create new one."""
    sire = db.query(Sire).filter(Sire.name == name).first()
    if sire:
        if breed and not sire.breed:
            sire.breed = breed
        if bw_epd is not None and sire.birth_weight_epd is None:
            sire.birth_weight_epd = bw_epd
        if semen_type and not sire.semen_type:
            sire.semen_type = semen_type
        return sire
    sire = Sire(name=name, breed=breed, birth_weight_epd=bw_epd, semen_type=semen_type)
    db.add(sire)
    db.flush()
    return sire


def get_or_create_recipient(
    db: Session, tag_id: str, farm_location: str | None, cow_or_heifer: str | None
) -> Recipient:
    """Find existing recipient by tag + farm or create new one."""
    # Recipients may share tag IDs across farms, so match on tag_id + farm
    q = db.query(Recipient).filter(Recipient.tag_id == tag_id)
    if farm_location:
        q = q.filter(Recipient.farm_location == farm_location)
    recipient = q.first()
    if recipient:
        return recipient
    recipient = Recipient(tag_id=tag_id, farm_location=farm_location, cow_or_heifer=cow_or_heifer)
    db.add(recipient)
    db.flush()
    return recipient


def get_or_create_technician(db: Session, name: str) -> Technician:
    """Find existing technician by name or create new one."""
    tech = db.query(Technician).filter(Technician.name == name).first()
    if tech:
        return tech
    tech = Technician(name=name)
    db.add(tech)
    db.flush()
    return tech


def get_or_create_protocol(db: Session, name: str) -> Protocol:
    """Find existing protocol by name or create new one."""
    proto = db.query(Protocol).filter(Protocol.name == name).first()
    if proto:
        return proto
    proto = Protocol(name=name)
    db.add(proto)
    db.flush()
    return proto


def ingest_et_data(csv_path: str, db: Session) -> dict:
    """Parse ET Data.csv and insert into normalized tables.

    Returns a summary dict with counts.
    """
    stats = {"rows_read": 0, "rows_ingested": 0, "rows_skipped": 0, "errors": []}

    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)  # skip header
        logger.info("CSV header: %d columns", len(header))

        for row_num, row in enumerate(reader, start=2):
            # Skip empty rows
            et_num_str = row[COL["et_number"]].strip() if len(row) > COL["et_number"] else ""
            if not et_num_str:
                continue

            stats["rows_read"] += 1

            try:
                et_number = parse_int(et_num_str)

                # --- Donor ---
                donor_tag = normalize_donor_tag(row[COL["donor"]])
                donor = None
                if donor_tag:
                    donor_breed = clean_str(row[COL["donor_breed"]])
                    donor_bw_epd = parse_decimal(row[COL["donor_bw_epd"]])
                    # Filter out dirty breed values (dates, IDs)
                    if donor_breed and ("/" in donor_breed or donor_breed.isdigit()):
                        logger.warning("Row %d: dirty donor breed %r for donor %s, setting to None", row_num, donor_breed, donor_tag)
                        donor_breed = None
                    donor = get_or_create_donor(db, donor_tag, donor_breed, donor_bw_epd)

                # --- Sire ---
                sire_name = clean_str(row[COL["sire_name"]])
                sire = None
                if sire_name:
                    sire_breed = clean_str(row[COL["sire_breed"]])
                    sire_bw_epd = parse_decimal(row[COL["sire_bw_epd"]])
                    semen_type = normalize_semen_type(row[COL["semen_type"]])
                    sire = get_or_create_sire(db, sire_name, sire_breed, sire_bw_epd, semen_type)

                # --- Recipient ---
                recip_tag = clean_str(row[COL["recipient_id_1"]])
                recipient = None
                if recip_tag:
                    farm = clean_str(row[COL["farm_location"]])
                    cow_heifer = clean_str(row[COL["cow_or_heifer"]])
                    recipient = get_or_create_recipient(db, recip_tag, farm, cow_heifer)

                # --- Technician ---
                tech_name = clean_str(row[COL["et_tech"]])
                technician = None
                if tech_name:
                    technician = get_or_create_technician(db, tech_name)

                # --- Protocol ---
                proto_name = clean_str(row[COL["protocol"]])
                protocol = None
                if proto_name:
                    protocol = get_or_create_protocol(db, proto_name)

                # --- Embryo ---
                embryo = Embryo(
                    donor_id=donor.donor_id if donor else None,
                    sire_id=sire.sire_id if sire else None,
                    opu_date=parse_date(row[COL["opu_date"]]),
                    stage=parse_int(row[COL["embryo_stage"]]),
                    grade=parse_int(row[COL["embryo_grade"]]),
                    fresh_or_frozen=clean_str(row[COL["fresh_or_frozen"]]),
                    cane_number=clean_str(row[COL["cane_number"]]),
                    freezing_date=parse_date(row[COL["freezing_date"]]),
                )
                db.add(embryo)
                db.flush()

                # --- ET Transfer ---
                et_date = parse_date(row[COL["et_date"]])
                if et_date is None:
                    stats["rows_skipped"] += 1
                    stats["errors"].append(f"Row {row_num}: missing ET date")
                    continue

                transfer = ETTransfer(
                    et_number=et_number,
                    lab=clean_str(row[COL["lab"]]),
                    satellite=clean_str(row[COL["satellite"]]),
                    customer_id=clean_str(row[COL["customer_id"]]),
                    et_date=et_date,
                    farm_location=clean_str(row[COL["farm_location"]]),
                    recipient_id=recipient.recipient_id if recipient else None,
                    bc_score=parse_decimal(row[COL["bc_score"]]),
                    cl_side=normalize_cl_side(row[COL["cl_side"]]),
                    cl_measure_mm=parse_decimal(row[COL["cl_measure_mm"]]),
                    protocol_id=protocol.protocol_id if protocol else None,
                    heat_observed=parse_bool_heat(row[COL["heat_1"]]),
                    heat_day=parse_int(row[COL["heat_day"]]),
                    embryo_id=embryo.embryo_id,
                    technician_id=technician.technician_id if technician else None,
                    assistant_name=clean_str(row[COL["et_assistant"]]),
                    pc1_date=parse_date(row[COL["pc1_date"]]),
                    pc1_result=normalize_pc_result(row[COL["pc1_result"]]),
                    pc2_date=parse_date(row[COL["pc2_date"]]),
                    pc2_result=normalize_pc_result(row[COL["pc2_result"]]),
                    fetal_sexing=clean_str(row[COL["fetal_sexing"]]),
                    days_in_pregnancy=parse_int(row[COL["dip_1"]]),
                )
                db.add(transfer)
                stats["rows_ingested"] += 1

            except Exception as exc:
                stats["rows_skipped"] += 1
                stats["errors"].append(f"Row {row_num}: {exc}")
                logger.error("Row %d failed: %s", row_num, exc)

    db.commit()
    return stats


def main():
    csv_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "docs", "dataset", "ET Summary - ET Data.csv"
    )
    csv_path = os.path.normpath(csv_path)

    if not os.path.exists(csv_path):
        logger.error("CSV not found: %s", csv_path)
        sys.exit(1)

    logger.info("Starting ET Data ingestion from %s", csv_path)

    db = SessionLocal()
    try:
        # Check if data already exists
        existing = db.query(ETTransfer).count()
        if existing > 0:
            logger.warning("Database already has %d transfers. Skipping ingestion.", existing)
            logger.info("To re-ingest, truncate the tables first.")
            return

        stats = ingest_et_data(csv_path, db)

        logger.info("=== Ingestion Complete ===")
        logger.info("Rows read: %d", stats["rows_read"])
        logger.info("Rows ingested: %d", stats["rows_ingested"])
        logger.info("Rows skipped: %d", stats["rows_skipped"])
        logger.info("Donors: %d", db.query(Donor).count())
        logger.info("Sires: %d", db.query(Sire).count())
        logger.info("Recipients: %d", db.query(Recipient).count())
        logger.info("Technicians: %d", db.query(Technician).count())
        logger.info("Protocols: %d", db.query(Protocol).count())
        logger.info("Embryos: %d", db.query(Embryo).count())
        logger.info("Transfers: %d", db.query(ETTransfer).count())

        if stats["errors"]:
            logger.warning("Errors (%d):", len(stats["errors"]))
            for err in stats["errors"][:20]:
                logger.warning("  %s", err)
    finally:
        db.close()


if __name__ == "__main__":
    main()
