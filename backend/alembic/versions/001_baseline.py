"""Baseline: alle 7 Desktop-Tabellen + neue M1-Tabelle ``formations``.

Spiegelt ``chormanager/data/database.py::create_tables`` (inkl.
nachträglicher ALTERs: spielzeit, Adress-/Guardian-Spalten, height)
plus ``backend/app/tables.py::formations_table``. Nur portable
Typen (VARCHAR via String, TEXT via Text, INTEGER) — SQLite und
MariaDB/MySQL (Analyse §5.6).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "singers",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("short_name", sa.String(128)),
        sa.Column("birth_date", sa.String(16)),
        sa.Column("voice_group", sa.String(64)),
        sa.Column("height", sa.Integer),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(64)),
        sa.Column("street", sa.String(255)),
        sa.Column("postal_code", sa.String(32)),
        sa.Column("city", sa.String(128)),
        sa.Column("gender", sa.String(32)),
        sa.Column("guardian1", sa.String(255)),
        sa.Column("guardian1_phone", sa.String(64)),
        sa.Column("guardian2", sa.String(255)),
        sa.Column("guardian2_phone", sa.String(64)),
        sa.Column("social_contacts", sa.String(1024)),
        sa.Column("joined_year", sa.Integer),
        sa.Column("joined_month", sa.Integer),
        sa.Column("left_year", sa.Integer),
        sa.Column("left_month", sa.Integer),
        sa.Column("affinity_uuid", sa.String(64)),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
    )
    op.create_table(
        "events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("date", sa.String(32), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("location", sa.String(255)),
        sa.Column("description", sa.Text),
        sa.Column("project_id", sa.String(64)),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
    )
    op.create_table(
        "projects",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("is_active", sa.Integer),
        sa.Column("spielzeit", sa.String(64)),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
    )
    op.create_table(
        "selbstdarstellung",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("content", sa.Text),
        sa.Column("updated_at", sa.String(32), nullable=False),
    )
    op.create_table(
        "availability",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("singer_id", sa.String(64), nullable=False),
        sa.Column("event_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
        sa.UniqueConstraint("singer_id", "event_id"),
    )
    op.create_table(
        "besetzung",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("project_id", sa.String(64)),
        sa.Column("singer_ids", sa.Text, nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
    )
    op.create_table(
        "repertoire",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("composer", sa.String(255)),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("dates", sa.String(255)),
        sa.Column("country", sa.String(128)),
        sa.Column("publisher", sa.String(255)),
        sa.Column("arrangement", sa.String(255)),
        sa.Column("location", sa.String(255)),
        sa.Column("project_id", sa.String(64)),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
    )
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
    # formations gehört 002 (idempotentes Nachziehen); hier nur die
    # 7 Desktop-Tabellen, damit downgrade base nicht doppelt droppt.
    for table in (
        "repertoire",
        "besetzung",
        "availability",
        "selbstdarstellung",
        "projects",
        "events",
        "singers",
    ):
        op.drop_table(table)
