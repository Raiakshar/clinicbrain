"""core tables

Revision ID: 0001
Revises:
Create Date: 2026-08-21
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clinics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("address", sa.String(500)),
        sa.Column("phone", sa.String(20)),
        sa.Column("settings", sa.JSON(), nullable=True),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(300), nullable=False),
    )
    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("dob", sa.Date()),
        sa.Column("gender", sa.String(20)),
        sa.Column(
            "allergies",
            sa.ARRAY(sa.String()),
            nullable=True,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "chronic_conditions",
            sa.ARRAY(sa.String()),
            nullable=True,
            server_default=sa.text("'{}'::text[]"),
        ),
    )
    op.create_table(
        "timeline_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("event_date", sa.Date()),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("mime", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("ocr_text", sa.Text()),
        sa.Column("extracted", sa.JSON()),
        sa.Column("error", sa.Text()),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("documents")
    op.drop_table("timeline_events")
    op.drop_table("patients")
    op.drop_table("users")
    op.drop_table("clinics")
