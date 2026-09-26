"""002: formations-Tabelle für Bestands-DBs nachziehen.

Desktop-DBs (per ``stamp 001`` auf Baseline gesetzt) kennen keine
``formations``-Tabelle — 001 läuft dort nie. Idempotent: auf frischen
DBs (001 bereits gelaufen) No-op. Verfahren siehe backend/README.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "formations" in inspector.get_table_names():
        return
    op.create_table(
        "formations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255)),
        sa.Column("rows", sa.Integer, nullable=False),
        sa.Column("cols", sa.Integer, nullable=False),
        sa.Column("staggered", sa.Integer),
        sa.Column("voicing_config", sa.Text),
        sa.Column("singers", sa.Text),
        sa.Column("placed", sa.Text),
        sa.Column("metadata", sa.Text),
        sa.Column("event_id", sa.String(64)),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "formations" in inspector.get_table_names():
        op.drop_table("formations")
