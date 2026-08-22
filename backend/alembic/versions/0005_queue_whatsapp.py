"""queue + whatsapp log

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-22
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "queue_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="waiting"),
        sa.Column(
            "checked_in_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_queue_clinic_date_number", "queue_tokens", ["clinic_id", "date", "number"], unique=True
    )
    op.create_table(
        "whatsapp_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("template", sa.String(50), nullable=False),
        sa.Column("body", sa.Text()),
        sa.Column("status", sa.String(20), nullable=False, server_default="retrying"),
        sa.Column("retries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text()),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "patients",
        sa.Column("whatsapp_consent", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("patients", "whatsapp_consent")
    op.drop_table("whatsapp_log")
    op.drop_index("idx_queue_clinic_date_number", table_name="queue_tokens")
    op.drop_table("queue_tokens")
