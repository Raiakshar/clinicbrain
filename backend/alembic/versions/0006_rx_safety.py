"""rx safety checker tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-22
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "drug_reference",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("generic_name", sa.String(200)),
        sa.Column("drug_class", sa.String(100)),
        sa.Column("max_daily_dose_mg", sa.Numeric(12, 2)),
    )
    op.get_bind().execute(
        sa.text("ALTER TABLE patients ADD COLUMN IF NOT EXISTS allergies JSONB DEFAULT '[]'")
    )
    op.create_table(
        "prescriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "patient_id",
            sa.Integer(),
            sa.ForeignKey("patients.id"),
            nullable=False,
        ),
        sa.Column("prescriber_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_table(
        "prescription_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "prescription_id",
            sa.Integer(),
            sa.ForeignKey("prescriptions.id"),
            nullable=False,
        ),
        sa.Column("drug_name", sa.String(200), nullable=False),
        sa.Column("dose_mg", sa.Numeric(12, 2), nullable=False),
        sa.Column("frequency_per_day", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("duration_days", sa.Integer()),
        sa.Column("instructions", sa.Text()),
    )


def downgrade() -> None:
    op.drop_table("prescription_items")
    op.drop_table("prescriptions")
    op.drop_column("patients", "allergies")
    op.drop_table("drug_reference")
