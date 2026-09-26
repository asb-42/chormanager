"""Portable table definitions (SQLite + MariaDB/MySQL).

Mirrors ``chormanager/data/database.py::create_tables``. Only
``String``/``Integer`` columns — no Postgres-only types, no
server defaults that differ per dialect (Analyse §5.6).
"""
from sqlalchemy import Column, Integer, MetaData, String, Table, Text

metadata = MetaData()

singers_table = Table(
    "singers",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("full_name", String(255), nullable=False),
    Column("short_name", String(128)),
    Column("birth_date", String(16)),
    Column("voice_group", String(64)),
    Column("height", Integer),
    Column("email", String(255)),
    Column("phone", String(64)),
    Column("street", String(255)),
    Column("postal_code", String(32)),
    Column("city", String(128)),
    Column("gender", String(32)),
    Column("guardian1", String(255)),
    Column("guardian1_phone", String(64)),
    Column("guardian2", String(255)),
    Column("guardian2_phone", String(64)),
    Column("social_contacts", String(1024)),
    Column("joined_year", Integer),
    Column("joined_month", Integer),
    Column("left_year", Integer),
    Column("left_month", Integer),
    Column("affinity_uuid", String(64)),
    Column("created_at", String(32), nullable=False),
    Column("updated_at", String(32), nullable=False),
)

events_table = Table(
    "events",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("date", String(32), nullable=False),
    Column("event_type", String(64), nullable=False),
    Column("location", String(255)),
    Column("description", Text),
    Column("project_id", String(64)),
    Column("created_at", String(32), nullable=False),
    Column("updated_at", String(32), nullable=False),
)

projects_table = Table(
    "projects",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("description", Text),
    Column("is_active", Integer),
    Column("spielzeit", String(64)),
    Column("created_at", String(32), nullable=False),
    Column("updated_at", String(32), nullable=False),
)

availability_table = Table(
    "availability",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("singer_id", String(64), nullable=False),
    Column("event_id", String(64), nullable=False),
    Column("status", String(32), nullable=False),
    Column("created_at", String(32), nullable=False),
    Column("updated_at", String(32), nullable=False),
)

besetzung_table = Table(
    "besetzung",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("project_id", String(64)),
    Column("singer_ids", Text, nullable=False),
    Column("created_at", String(32), nullable=False),
    Column("updated_at", String(32), nullable=False),
)

repertoire_table = Table(
    "repertoire",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("composer", String(255)),
    Column("title", String(255), nullable=False),
    Column("dates", String(255)),
    Column("country", String(128)),
    Column("publisher", String(255)),
    Column("arrangement", String(255)),
    Column("location", String(255)),
    Column("project_id", String(64)),
    Column("created_at", String(32), nullable=False),
    Column("updated_at", String(32), nullable=False),
)

selbstdarstellung_table = Table(
    "selbstdarstellung",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("content", Text),
    Column("updated_at", String(32), nullable=False),
)

formations_table = Table(
    "formations",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("name", String(255)),
    Column("rows", Integer, nullable=False),
    Column("cols", Integer, nullable=False),
    Column("staggered", Integer),
    Column("voicing_config", Text),
    Column("singers", Text),
    Column("placed", Text),
    Column("metadata", Text),
    Column("event_id", String(64)),
    Column("created_at", String(32), nullable=False),
    Column("updated_at", String(32), nullable=False),
)
