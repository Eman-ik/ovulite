"""Record AI grading separately from the embryologist's own grade.

The SRS requires AI output to be kept apart from the manual assessment.
Separation technically held before this — nothing wrote ``embryos.ai_grade`` —
but only because grading results were never persisted at all. Each call to
POST /grade/embryo returned a grade and forgot it.

Two columns could not fix that. An assessment is only interpretable alongside
the model that produced it, and the model changes: the served grader moved from
EfficientNet-B0 to a morphometric model this month. Overwriting one row per
embryo would erase exactly the provenance that makes the record worth keeping,
so assessments accumulate and ``embryos.grade`` is never touched.

``embryos.ai_grade`` and ``ai_viability`` are left in place and still unwritten;
removing them is a separate decision about an unused column.

Revision ID: 018_embryo_ai_assessment
Revises: 017_laboratory_entity
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "018_embryo_ai_assessment"
down_revision = "017_laboratory_entity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "embryo_ai_assessments",
        sa.Column("assessment_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("embryo_id", sa.Integer(), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("predicted_grade", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("probabilities", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        # The measured features, so an assessment can be re-derived and audited
        # without the original image.
        sa.Column("features", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        # Identifies the exact pixels assessed. Two assessments of the same
        # embryo from different photographs are different evidence.
        sa.Column("image_sha256", sa.String(length=64), nullable=True),
        sa.Column("assessed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("assessed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"]),
        sa.ForeignKeyConstraint(["embryo_id"], ["embryos.embryo_id"]),
        sa.ForeignKeyConstraint(["assessed_by_user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("assessment_id"),
        sa.CheckConstraint("predicted_grade BETWEEN 1 AND 4", name="ck_embryo_ai_grade_range"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_embryo_ai_confidence"),
    )
    op.create_index("ix_embryo_ai_assessments_embryo_id", "embryo_ai_assessments", ["embryo_id"])
    op.create_index(
        "ix_embryo_ai_assessments_organization_id", "embryo_ai_assessments", ["organization_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_embryo_ai_assessments_organization_id", table_name="embryo_ai_assessments")
    op.drop_index("ix_embryo_ai_assessments_embryo_id", table_name="embryo_ai_assessments")
    op.drop_table("embryo_ai_assessments")
