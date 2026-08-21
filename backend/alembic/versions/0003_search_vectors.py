"""search vectors

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-21
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE documents ADD COLUMN IF NOT EXISTS search_vector tsvector
        GENERATED ALWAYS AS (to_tsvector('english', coalesce(ocr_text, ''))) STORED
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_search ON documents USING GIN (search_vector)"
    )
    op.execute(
        """
        ALTER TABLE timeline_events ADD COLUMN IF NOT EXISTS search_vector tsvector
        GENERATED ALWAYS AS (
            to_tsvector('english',
                coalesce(payload->>'summary', '') || ' ' ||
                coalesce(payload->>'content_text', '') || ' ' ||
                coalesce(payload->>'text', '')
            )
        ) STORED
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_events_search ON timeline_events USING GIN (search_vector)"
    )


def downgrade() -> None:
    op.drop_index("idx_events_search", table_name="timeline_events")
    op.drop_column("timeline_events", "search_vector")
    op.drop_index("idx_documents_search", table_name="documents")
    op.drop_column("documents", "search_vector")
