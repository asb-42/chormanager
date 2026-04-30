#!/usr/bin/env python3
"""Import Sänger from CSV (Mitgliederliste) - mit Upsert-Logik."""

import sys
import csv
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path


def normalize_birth_date(date_str: str) -> str | None:
    """Normalize birth date to YYYY-MM-DD format."""
    if not date_str:
        return None

    date_str = date_str.strip()

    for fmt in ["%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"]:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    parts = date_str.split(".")
    if len(parts) == 3:
        day, month, year = parts
        try:
            day = int(day)
            month = int(month)

            if len(year) == 2:
                year_num = int(year)
                if year_num <= 25:
                    year = f"20{year}"
                else:
                    year = f"19{year}"

            dt = datetime(int(year), int(month), day)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None


def normalize_gender(g: str) -> str | None:
    """Normalize gender: w -> weiblich, m -> männlich."""
    if not g:
        return None
    g = g.strip().lower()
    if g == "w":
        return "weiblich"
    elif g == "m":
        return "männlich"
    return None


def compute_is_adult(birth_date: str | None) -> int:
    """Compute is_adult from birth_date."""
    if not birth_date:
        return 0
    try:
        birth = datetime.strptime(birth_date[:10], "%Y-%m-%d")
        age = (datetime.now() - birth).days / 365.25
        return 1 if age >= 18 else 0
    except (ValueError, OSError):
        return 0


def main():
    db_path = Path("/media/data/coding/chormanager/data/chor.db")
    csv_path = Path("/media/data/coding/chormanager/workdir/Mitgliederliste.csv")

    if not csv_path.exists():
        print(f"CSV file not found: {csv_path}")
        sys.exit(1)

    print(f"Importing from: {csv_path}")
    print(f"Database: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    imported = 0
    updated = 0
    skipped = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")

        for row_num, row in enumerate(reader, start=2):
            vorname = row.get("Vorname", "").strip()
            name = row.get("Name", "").strip()

            if not name or not vorname:
                print(f"Zeile {row_num}: Name/Vorname fehlt - übersprungen")
                skipped += 1
                continue

            full_name = f"{name}, {vorname}"
            voice_group = row.get("Stimmgruppe", "").strip() or None

            gender = normalize_gender(row.get("Geschlecht", ""))
            birth_date = normalize_birth_date(row.get("Geburtstag", ""))
            is_adult = compute_is_adult(birth_date)

            street = row.get("Straße, Hausnummer", "").strip() or None

            plz = row.get("PLZ", "").strip()
            postal_code = plz if plz else None

            city = row.get("Ort", "").strip() or None
            phone = row.get("Handy", "").strip() or None
            email = row.get("E-Mail", "").strip() or None

            guardian1 = row.get("Erziehungs-berechtigte/r #1", "").strip() or None
            guardian1_phone = row.get("Handy EB #1", "").strip() or None
            guardian2 = row.get("Erziehungs-berechtigte/r #2", "").strip() or None
            guardian2_phone = row.get("Handy EB #2", "").strip() or None

            now = datetime.now().isoformat()

            # Check if exists by full_name + voice_group (unique key)
            if voice_group:
                cursor.execute(
                    "SELECT id FROM singers WHERE full_name = ? AND voice_group = ?",
                    (full_name, voice_group),
                )
            else:
                cursor.execute(
                    "SELECT id FROM singers WHERE full_name = ? AND (voice_group IS NULL OR voice_group = '')",
                    (full_name,),
                )

            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    """UPDATE singers SET
                        gender = ?, birth_date = ?, is_adult = ?,
                        street = ?, postal_code = ?, city = ?,
                        phone = ?, email = ?,
                        guardian1 = ?, guardian1_phone = ?, guardian2 = ?, guardian2_phone = ?,
                        updated_at = ?
                    WHERE id = ?""",
                    (
                        gender,
                        birth_date,
                        is_adult,
                        street,
                        postal_code,
                        city,
                        phone,
                        email,
                        guardian1,
                        guardian1_phone,
                        guardian2,
                        guardian2_phone,
                        now,
                        existing["id"],
                    ),
                )
                updated += 1
                print(f"Zeile {row_num}: {full_name} aktualisiert")
            else:
                singer_id = str(uuid.uuid4())
                cursor.execute(
                    """INSERT INTO singers (
                        id, full_name, gender, birth_date, is_adult, voice_group,
                        street, postal_code, city,
                        phone, email,
                        guardian1, guardian1_phone, guardian2, guardian2_phone,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        singer_id,
                        full_name,
                        gender,
                        birth_date,
                        is_adult,
                        voice_group,
                        street,
                        postal_code,
                        city,
                        phone,
                        email,
                        guardian1,
                        guardian1_phone,
                        guardian2,
                        guardian2_phone,
                        now,
                        now,
                    ),
                )
                imported += 1
                print(f"Zeile {row_num}: {full_name} importiert")

    conn.commit()
    conn.close()

    print(f"\n=== Import abgeschlossen ===")
    print(f"Neu importiert: {imported}")
    print(f"Aktualisiert: {updated}")
    print(f"Übersprungen: {skipped}")


if __name__ == "__main__":
    main()
