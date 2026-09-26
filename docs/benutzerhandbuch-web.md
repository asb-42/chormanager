# ChorManager Web – Benutzerhandbuch

> Für die Desktop-Anwendung (Qt) gilt weiterhin das
> [Benutzerhandbuch](benutzerhandbuch.md). Diese Anleitung beschreibt
> die Web-Version (Browser), Stand M5 / MS4.

## Inhalt

- [Start und Anmeldung](#start-und-anmeldung)
- [Navigation](#navigation)
- [Sänger, Termine, Projekte](#sänger-termine-projekte)
- [Verfügbarkeit erfassen](#verfügbarkeit-erfassen)
- [Aufstellung planen (Formation Editor)](#aufstellung-planen-formation-editor)
- [Exporte und PDF](#exporte-und-pdf)
- [Backup](#backup)
- [Assistent](#assistent)
- [Problemlösung](#problemlösung)

## Start und Anmeldung

1. Adresse im Browser öffnen (z. B. `http://server:8080`).
   Empfohlen: Notebook oder Desktop-PC mit Maus oder Trackpad.
2. Solange kein API-Token vergeben ist, ist alles offen
   (Entwicklungs-Default). Mit Token: Bei schreibenden Aktionen
   ggf. anmelden (der Chorleiter hinterlegt das Token).
3. Die Versionsnummer steht in der Fußzeile.

## Navigation

Oben: Start, Sänger, Termine, Projekte, Besetzung, Repertoire,
Verfügbarkeit, Assistent, Backup, Aufstellungen. Alles ist über
die Tastatur erreichbar; Tabellen lassen sich durchsuchen.

## Sänger, Termine, Projekte

- **Sänger:** Suchfeld filtert live. „Neu" legt an (Name ist
  Pflicht), „Bearbeiten" ändert, „Löschen" fragt zweimal nach.
- **Termine:** Filter nach Projekt, Suche und Typ. Die Spalten
  „Zusagen" und „Vorbehalt" zählen automatisch.
- **Projekte:** Projekt anklicken → Auswertung je Termin und je
  Stimmgruppe.

## Verfügbarkeit erfassen

1. Oben „Verfügbarkeit", Termin wählen (der neueste steht voraus).
2. Je Sänger den Status setzen: ✓ Zusage, ✗ Absage,
   ○ keine Rückmeldung, ✓? Vorbehalt, ? Weiß nicht, ~ Vielleicht.
3. „Speichern" sichert alles auf einmal („Gespeichert." erscheint).

## Aufstellung planen (Formation Editor)

1. „Aufstellungen" → Aufstellung wählen (oder über den Assistenten
   neu anlegen: Projekt → Termin → „Aufstellung anlegen").
2. Kacheln mit der Maus auf freie Zellen ziehen; auf eine belegte
   Zelle ziehen tauscht die Plätze. Mehrere Kacheln: leere Fläche
   aufziehen (Gummiband), Strg+Klick schaltet einzeln um,
   Auswahl gemeinsam ziehen.
3. „Versetzt" schaltet das versetzte Raster um. Jede Änderung wird
   sofort gespeichert („Gespeichert um …" erscheint oben).
4. „Optimieren": Regel ankreuzen (z. B. Größe), „Vorschau" zeigt
   die Änderungen, „Übernehmen" wendet sie an (rückgängig geht
   nicht — bei Bedarf neu optimieren oder manuell ziehen).
5. „Reihen/Spalten" + „Anwenden" ändert die Rastergröße. Fallen
   dabei Sänger raus, fragt die App vorher („Trotzdem anwenden"
   legt sie zurück in den Pool).

## Exporte und PDF

- Die Zusagen-Liste eines Projekts gibt es als PDF (Druck) — die
  Fußzeile der App zeigt die Version, PDFs sind maßfrei (das
  Raster ist auch im Desktop nie maßstabsgetreu).
- Sängerdaten zusätzlich als CSV; JSON-Sync für die
  Choraufstellung.

## Backup

„Backup" listet Sicherungen (neueste zuerst). „Backup anlegen"
sichert sofort. „Wiederherstellen" fragt zweimal nach und ersetzt
die laufende Datenbank — danach kurz warten und neu laden.
Hinweis: Auf MariaDB-Servern meldet die Seite ggf.
„Backups nur für SQLite-Dateien" — dort sichert der Admin die
Datenbank mit den datenbankeigenen Werkzeugen.

## Assistent

Der Assistent führt in Schritten durch: Aufstellung planen
(Projekt → Termin → Zusagen-Hinweis → Raster anlegen), Termin
eintragen, Chormitglied aufnehmen. Jeder Schritt lässt sich
abbrechen.

## Problemlösung

- **Seite lädt nicht:** Adresse prüfen, Server läuft? (Admin fragen).
- **Speichern schlägt fehl:** Seite neu laden und erneut versuchen;
  bei „401" fehlt das API-Token (Admin).
- **Aufstellung weg?** Unter „Aufstellungen" liegt jede gespeicherte
  Version; nichts geht durch Ziehen verloren (abgebrochene Züge
  werden zurückgesetzt).
- **Druckbild prüfen:** PDF herunterladen und vor dem Ausdruck
  ansehen (Kurznamen zentriert, alle Kacheln drauf).
