"""Exercise the real local model with an isolated corpus/database, saving evidence."""
import json
import os
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["LITERATURE_RAG_ENABLED"] = "true"
os.environ["LITERATURE_GENERATION_PROVIDER"] = "llama_cpp"
os.environ["LITERATURE_MODEL_URL"] = "http://127.0.0.1:8012"
os.environ["LITERATURE_EMBEDDING_MODEL"] = "hash-512-v1"
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database import Base
from app.models import Organization, LiteratureDocument
from app.services.literature_seed import seed_corpus
from app.services.literature_rag import answer_question

engine = create_engine("sqlite://")
Base.metadata.create_all(engine)
with Session(engine) as db:
    db.add(Organization(organization_id=1, name="Isolated RAG verification", slug="rag-smoke"))
    db.commit()
    seed_corpus(db, 1, "software-test")
    started = time.perf_counter()
    answer = answer_question(db, "What effect did CSF2 and DKK1 have on pregnancy rate for embryos cultured without serum?", db.query(LiteratureDocument).all())
    report = {"elapsed_seconds": round(time.perf_counter() - started, 2), **answer}
    destination = BASE.parent / "outputs" / "literature-rag-smoke.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("mode", "model", "elapsed_seconds", "answer", "fallback_reason")}, ensure_ascii=False), flush=True)
    if report["mode"] != "generative_rag" or not report["claims"]:
        raise SystemExit("Live generation did not produce a cited answer; inspect the report")
    print(f"Live RAG transport/schema/citation verification passed: {destination}. Scientific interpretation requires review.", flush=True)
