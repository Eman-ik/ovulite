import hashlib
import json
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.literature import LiteratureDocument
from app.models.organization import Organization


def seed_corpus(db: Session, organization_id: int, username: str):
    path = Path(__file__).resolve().parents[2] / "resources" / "literature_seed" / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    db.query(Organization).filter_by(organization_id=organization_id).with_for_update().one()
    known = {checksum for checksum, in db.query(LiteratureDocument.checksum).filter_by(organization_id=organization_id)}
    inserted = 0
    for item in manifest["documents"]:
        checksum = hashlib.sha256(item["content"].encode()).hexdigest()
        if checksum != item["checksum"]:
            raise ValueError("Bundled corpus checksum does not match source text")
        if checksum in known:
            continue
        values = {key: item[key] for key in ("title", "authors", "year", "source_url", "source_kind", "rights", "content")}
        db.add(LiteratureDocument(**values, checksum=checksum, organization_id=organization_id, created_by=username))
        known.add(checksum)
        inserted += 1
    db.commit()
    return {"inserted": inserted, "total": len(known), "scope": "Licensed paper text; not a formal evidence-quality appraisal", "retrieved_at": manifest["retrieved_at"]}
