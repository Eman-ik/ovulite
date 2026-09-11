"""A single observation of an embryo during culture.

The development timeline — Day 3 cleavage, Day 5 morula, Day 6 early
blastocyst, Day 7 blastocyst, Day 8 expanded or hatched. ``Embryo.stage`` and
``Embryo.grade`` record only where the embryo ended up; they cannot say when
it got there, or that it arrested on day 5. Those are different questions and
they need a row per look, not a wider embryo row.

This is also what would make an outcome-supervised grading model trainable:
morphology at a known hour, paired with what the embryo went on to do.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.embryo import Embryo
    from app.models.technician import Technician

# IETS developmental stages 1-9. Stored as the numeric code the embryologist
# already writes, with the label kept in the frontend rather than duplicated
# here where it would drift.
MIN_STAGE, MAX_STAGE = 1, 9
MIN_GRADE, MAX_GRADE = 1, 4


class EmbryoObservation(OrganizationScopedMixin, Base):
    __tablename__ = "embryo_observations"

    observation_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    embryo_id: Mapped[int] = mapped_column(
        ForeignKey("embryos.embryo_id"), nullable=False, index=True
    )

    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Days since fertilisation. Stored rather than derived because an embryo
    # whose IVF date is missing still has a meaningful "this was the day 7
    # look", and that is how the lab refers to it.
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)

    stage: Mapped[Optional[int]] = mapped_column(Integer)
    grade: Mapped[Optional[int]] = mapped_column(Integer)
    # Free text for morphology: fragmentation, ICM and trophectoderm quality,
    # zona condition. Deliberately not an enum — labs describe these
    # differently and a forced vocabulary would lose the detail.
    morphology: Mapped[Optional[str]] = mapped_column(Text)
    is_arrested: Mapped[Optional[bool]] = mapped_column()
    cell_count: Mapped[Optional[int]] = mapped_column(Integer)
    expansion_diameter_um: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))

    embryologist_id: Mapped[Optional[int]] = mapped_column(ForeignKey("technicians.technician_id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    embryo: Mapped["Embryo"] = relationship(back_populates="observations")
    embryologist: Mapped[Optional["Technician"]] = relationship()

    __table_args__ = (
        # One look per embryo per day; a second look the same day is a
        # correction to the first, not a new data point.
        UniqueConstraint("embryo_id", "day_number", name="uq_embryo_observations_embryo_day"),
        CheckConstraint("day_number BETWEEN 0 AND 12", name="ck_embryo_observations_day_number"),
        CheckConstraint(
            f"stage IS NULL OR stage BETWEEN {MIN_STAGE} AND {MAX_STAGE}",
            name="ck_embryo_observations_stage",
        ),
        CheckConstraint(
            f"grade IS NULL OR grade BETWEEN {MIN_GRADE} AND {MAX_GRADE}",
            name="ck_embryo_observations_grade",
        ),
    )


class ObservationStageLabel:
    """Stage codes as the lab names them, for API responses.

    Kept beside the model so the numeric codes above have a single readable
    reference, without storing the label per row.
    """

    LABELS = {
        1: "Unfertilised / 1-cell",
        2: "2 to 12-cell",
        3: "Early morula",
        4: "Compact morula",
        5: "Early blastocyst",
        6: "Blastocyst",
        7: "Expanded blastocyst",
        8: "Hatching blastocyst",
        9: "Hatched blastocyst",
    }
