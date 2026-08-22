"""lab tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-22
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lab_tests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("unit", sa.String(50)),
    )
    op.create_table(
        "lab_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id")),
        sa.Column("test_name", sa.String(200), nullable=False),
        sa.Column("value", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit", sa.String(50)),
        sa.Column("ref_low", sa.Numeric(12, 4)),
        sa.Column("ref_high", sa.Numeric(12, 4)),
        sa.Column("flag", sa.String(10), nullable=False, server_default="normal"),
        sa.Column("taken_at", sa.Date()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("idx_lab_results_patient_test", "lab_results", ["patient_id", "test_name"])


def downgrade() -> None:
    op.drop_index("idx_lab_results_patient_test", table_name="lab_results")
    op.drop_table("lab_results")
    op.drop_table("lab_tests")
