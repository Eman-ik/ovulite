import hashlib
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import LAB_WRITE_ROLES, get_current_user, require_role
from app.database import get_db
from app.models.literature import LiteratureDocument
from app.models.user import User
from app.services.literature_rag import answer_question, settings

router = APIRouter()


class DocumentInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=3, max_length=500)
    authors: str = Field(min_length=2, max_length=1000)
    year: int = Field(ge=1900, le=2100)
    source_url: HttpUrl
    source_kind: Literal["peer_reviewed", "approved_sop"]
    rights: str = Field(min_length=5, max_length=1000)
    content: str = Field(min_length=100, max_length=200000)


class Question(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    question: str = Field(min_length=3, max_length=2000)


def organization(user: User) -> int:
    if user.organization_id is None:
        raise HTTPException(403, "An organization is required")
    return user.organization_id


@router.get("/documents")
def documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(LiteratureDocument).filter_by(organization_id=organization(user)).order_by(LiteratureDocument.document_id.desc()).all()
    return {"total": len(rows), "target": 50, "items": [
        {key: getattr(row, key) for key in ("document_id", "title", "authors", "year", "source_url", "source_kind", "rights", "created_by", "created_at")}
        for row in rows]}


@router.post("/documents", status_code=201)
def add_document(payload: DocumentInput, db: Session = Depends(get_db),
                 user: User = Depends(require_role(*LAB_WRITE_ROLES))):
    values = payload.model_dump()
    values["source_url"] = str(payload.source_url)
    if len(values["source_url"]) > 2000:
        raise HTTPException(422, "Source URL must be at most 2000 characters")
    row = LiteratureDocument(**values, organization_id=organization(user), created_by=user.username,
                             checksum=hashlib.sha256(payload.content.encode()).hexdigest())
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This document text is already in your corpus")
    db.refresh(row)
    return {"document_id": row.document_id, "title": row.title}


@router.post("/query")
def query(payload: Question, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(LiteratureDocument).filter_by(organization_id=organization(user)).all()
    return answer_question(db, payload.question, rows)


@router.get("/status")
def status(user: User = Depends(get_current_user)):
    organization(user)
    config = settings()
    return {key: config[key] for key in ("enabled", "provider", "model", "embedding_model")}


@router.post("/seed", status_code=201)
def seed(db: Session = Depends(get_db), user: User = Depends(require_role(*LAB_WRITE_ROLES))):
    from app.services.literature_seed import seed_corpus
    return seed_corpus(db, organization(user), user.username)
