"""An AI grading result, kept apart from the embryologist's own grade.

``embryos.grade`` is the human assessment and nothing here ever writes it. The
two are reported side by side and allowed to disagree — a disagreement is a
finding, not an error to be reconciled by overwriting one with the other.

Assessments accumulate rather than replace. The served grader changed from
EfficientNet-B0 to a morphometric model, so "what grade did the AI give" is
only answerable together with "which model, on which image, when".
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, ForeignKey, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.embryo import Embryo
    from app.models.user import User


class EmbryoAIAssessment(OrganizationScopedMixin, Base):
    __tablename__ = "embryo_ai_assessments"

    assessment_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Nullable: an image can be graded before it is attached to a record.
    embryo_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("embryos.embryo_id"), index=True
    )

    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)

    predicted_grade: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    probabilities: Mapped[Optional[dict]] = mapped_column(JSON)

    # The measured morphometrics, so an assessment is auditable without the
    # original image.
    features: Mapped[Optional[dict]] = mapped_column(JSON)
    image_sha256: Mapped[Optional[str]] = mapped_column(String(64))

    assessed_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id"))
    assessed_at: Mapped[datetime] = mapped_column(server_default=func.now())
    notes: Mapped[Optional[str]] = mapped_column(Text)

    embryo: Mapped[Optional["Embryo"]] = relationship(back_populates="ai_assessments")
    assessed_by: Mapped[Optional["User"]] = relationship()

    __table_args__ = (
        CheckConstraint("predicted_grade BETWEEN 1 AND 4", name="ck_embryo_ai_grade_range"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_embryo_ai_confidence"),
    )
