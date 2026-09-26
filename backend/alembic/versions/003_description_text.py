"""003: description-Spalten auf TEXT erweitern.

Echte Desktop-Daten sprengen VARCHAR(1024) (Projekt-Beschreibungen
>1024 Zeichen); das Desktop-Schema kennt nur TEXT. Dialekt-bewusst:
SQLite kennt kein MODIFY — dort No-op (TEXT bereits unbegrenzt).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "mysql":
        return
    op.alter_column(
        "projects", "description",
        existing_type=sa.String(1024), type_=sa.Text(),
    )
    op.alter_column(
        "events", "description",
        existing_type=sa.String(1024), type_=sa.Text(),
    )


def downgrade() -> None:
    # Kein Weg zurück (Daten könnten länger als 1024 sein).
    pass
