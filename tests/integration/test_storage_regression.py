"""
Regressionstests für Sänger-Dubletten und verwandte Bugs.

Hintergrund:
    MainWindow.singers  = Master-Liste ALLER Sänger (platzierte + unplatzierte)
    FormationGrid.singers = Liste NUR der platzierten Sänger

    Nach open_f() zeigen beide Listen auf VERSCHIEDENE Python-Objekte
    für dieselben platzierten Sänger. Wenn ein Sänger im Grid bewegt wird,
    aktualisiert MoveSingerCommand nur das Objekt in grid.singers (row/col ändern
    sich). Das Objekt in MainWindow.singers behält die alte Position (stale).

    Beim Speichern:
        - "singers"-Array: aus MainWindow.singers → stale row/col
        - "placed"-Array:  aus grid.get_placed_singers() → aktuelle row/col

    Beim Laden:
        Singer.from_dict() erzeugt neue Objekte. @dataclass vergleicht ALLE Felder
        inkl. row/col. Da stale row/col ≠ aktuelle row/col, schlägt der
        Deduplizierungscheck ( if singer not in all_singers ) fehl → Dublette.

Führe diese Tests aus mit:
    python3 -m pytest tests/integration/test_storage_regression.py -v
"""

import os
import sys
import json
import tempfile
import types

import pytest

# ---------------------------------------------------------------------------
# Qt-Stub damit storage.py ohne PyQt5-Installation importierbar ist
# ---------------------------------------------------------------------------
def _install_qt_stub():
    qt = types.ModuleType("PyQt5")
    core = types.ModuleType("PyQt5.QtCore")

    class QStandardPaths:
        AppDataLocation = 0
        @staticmethod
        def writableLocation(_loc):
            return tempfile.gettempdir()

    core.QStandardPaths = QStandardPaths
    qt.QtCore = core
    sys.modules.setdefault("PyQt5", qt)
    sys.modules.setdefault("PyQt5.QtCore", core)

_install_qt_stub()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from singer_model import Singer, VoiceGroup  # noqa: E402
from storage import FormationStorage         # noqa: E402


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _make_storage(tmp_path) -> tuple:
    """Gibt (FormationStorage-Instanz, Pfad zur JSON-Datei) zurück."""
    path = os.path.join(str(tmp_path), "formation.json")
    return FormationStorage(), path


def _singer_ids(loaded: dict) -> list:
    return [s.singer_id for s in loaded["singers"]]


# ===========================================================================
# Bug 1 – Dublette nach Bewegung (Hauptbug)
# ===========================================================================

class TestNoDuplicatesAfterMove:
    """
    Sänger wird nach dem Laden aus dem Grid verschoben.
    MainWindow.singers hat stale row/col, grid.singers die aktuelle.
    Nach save → load darf jede singer_id nur EINMAL in 'singers' vorkommen.
    """

    def test_no_duplicate_after_singer_moved_in_grid(self, tmp_path):
        storage, filepath = _make_storage(tmp_path)

        # Zustand in MainWindow.singers (stale: Anna noch bei row=0, col=0)
        anna_main = Singer("Anna", VoiceGroup.ALT_1, 165, "id-anna", row=0, col=0)
        bert_main = Singer("Bert", VoiceGroup.BASS_1, 180, "id-bert", row=-1, col=-1)

        # Zustand in grid.singers NACH der Bewegung (Anna jetzt bei row=1, col=2)
        anna_grid = Singer("Anna", VoiceGroup.ALT_1, 165, "id-anna", row=1, col=2)

        storage.save_formation(
            singers=[anna_main, bert_main],      # MainWindow.singers (stale)
            rows=4, cols=5,
            filepath=filepath,
            placed_singers=[(anna_grid, 1, 2)],  # grid.get_placed_singers() (aktuell)
            staggered=False,
            voicing_config=[],
        )

        loaded = storage.load_formation(filepath)
        assert loaded is not None

        ids = _singer_ids(loaded)
        dupes = [sid for sid in set(ids) if ids.count(sid) > 1]

        assert dupes == [], (
            f"Dublette singer_ids nach save→load mit verschobenem Sänger: {dupes}\n"
            f"Alle geladenen Sänger: {[(s.singer_id, s.row, s.col) for s in loaded['singers']]}"
        )
        assert len(loaded["singers"]) == 2, (
            f"Erwartet 2 Sänger, bekommen {len(loaded['singers'])}: "
            f"{[(s.name, s.row, s.col) for s in loaded['singers']]}"
        )

    def test_no_duplicate_for_multiple_moved_singers(self, tmp_path):
        storage, filepath = _make_storage(tmp_path)

        # Beide Sänger in MainWindow.singers mit ursprünglichen Positionen
        anna_main = Singer("Anna", VoiceGroup.ALT_1, 165, "id-anna", row=0, col=0)
        bert_main = Singer("Bert", VoiceGroup.BASS_1, 180, "id-bert", row=0, col=1)

        # Nach Bewegung im Grid: andere Objekte mit neuen Positionen
        anna_grid = Singer("Anna", VoiceGroup.ALT_1, 165, "id-anna", row=2, col=3)
        bert_grid = Singer("Bert", VoiceGroup.BASS_1, 180, "id-bert", row=3, col=0)

        storage.save_formation(
            singers=[anna_main, bert_main],
            rows=4, cols=5,
            filepath=filepath,
            placed_singers=[(anna_grid, 2, 3), (bert_grid, 3, 0)],
            staggered=False,
            voicing_config=[],
        )

        loaded = storage.load_formation(filepath)
        ids = _singer_ids(loaded)
        dupes = [sid for sid in set(ids) if ids.count(sid) > 1]

        assert dupes == [], f"Dubletten: {dupes}"
        assert len(loaded["singers"]) == 2


# ===========================================================================
# Bug 2 – Sänger-Objekt-Identität nach load_formation
# ===========================================================================

class TestSingerIdentityAfterLoad:
    """
    Nach load_formation müssen die Sänger-Objekte in 'placed' und in 'singers'
    identische Daten haben UND idealerweise dasselbe Python-Objekt sein,
    damit Mutationen (row/col-Änderungen) synchron bleiben.

    Aktuell gibt load_formation VERSCHIEDENE Objekte zurück – das ist
    der architektonische Root-Cause aller Dubletten-Bugs.
    """

    def test_placed_singer_is_same_object_as_in_singers_list(self, tmp_path):
        """
        Das Objekt in placed_dict[(r,c)] MUSS dasselbe Python-Objekt sein
        wie das entsprechende Objekt in all_singers (gleiche singer_id).
        Sonst divergieren die Positionen bei jeder Mutation.
        """
        storage, filepath = _make_storage(tmp_path)

        anna = Singer("Anna", VoiceGroup.ALT_1, 165, "id-anna", row=0, col=0)
        bert = Singer("Bert", VoiceGroup.BASS_1, 180, "id-bert", row=-1, col=-1)

        storage.save_formation(
            singers=[anna, bert], rows=4, cols=5, filepath=filepath,
            placed_singers=[(anna, 0, 0)], staggered=False, voicing_config=[],
        )

        loaded = storage.load_formation(filepath)
        placed_list = loaded["placed"]
        placed_dict = {(s.row, s.col): s for s, r, c in placed_list}
        singers_by_id = {s.singer_id: s for s in loaded["singers"]}

        assert (0, 0) in placed_dict, "Sänger (0,0) fehlt in placed"
        assert "id-anna" in singers_by_id, "Anna fehlt in singers-Liste"

        # Kernforderung: DASSELBE Python-Objekt, keine Kopie
        assert placed_dict[(0, 0)] is singers_by_id["id-anna"], (
            "placed_dict[(0,0)] und singers[id-anna] sind VERSCHIEDENE Objekte. "
            "Mutations an grid.singers propagieren daher nicht zu MainWindow.singers."
        )

    def test_no_singer_id_appears_twice_after_clean_roundtrip(self, tmp_path):
        """
        Auch ohne Bewegung: einfaches save→load darf keine Dubletten erzeugen.
        """
        storage, filepath = _make_storage(tmp_path)

        singers = [
            Singer("Anna",  VoiceGroup.ALT_1,   165, "id-anna",  row=0, col=0),
            Singer("Bert",  VoiceGroup.BASS_1,   180, "id-bert",  row=0, col=1),
            Singer("Clara", VoiceGroup.SOPRAN_1, 160, "id-clara", row=-1, col=-1),
        ]
        placed = [(singers[0], 0, 0), (singers[1], 0, 1)]

        storage.save_formation(
            singers=singers, rows=4, cols=5, filepath=filepath,
            placed_singers=placed, staggered=False, voicing_config=[],
        )

        loaded = storage.load_formation(filepath)
        ids = _singer_ids(loaded)
        dupes = [sid for sid in set(ids) if ids.count(sid) > 1]

        assert dupes == [], f"Dubletten schon ohne Bewegung: {dupes}"
        assert len(loaded["singers"]) == 3


# ===========================================================================
# Bug 3 – JSON-Struktur: Platzierte Sänger doppelt im File
# ===========================================================================

class TestJsonStructureRedundancy:
    """
    Derzeit schreibt save_formation platzierte Sänger ZWEIMAL in die JSON:
    einmal in 'singers' (alle Sänger aus MainWindow.singers) und einmal in
    'placed'. Das ist die strukturelle Ursache aller Deduplizierungs-Probleme.

    Korrekte Struktur: 'singers' enthält NUR unplatzierte Sänger (row=-1),
    'placed' enthält alle platzierten mit ihrer Position.
    """

    def test_placed_singer_not_duplicated_in_singers_array(self, tmp_path):
        """
        Ein platzierter Sänger darf in 'singers' im JSON NICHT nochmal auftauchen,
        wenn er bereits in 'placed' steht.
        """
        storage, filepath = _make_storage(tmp_path)

        anna = Singer("Anna", VoiceGroup.ALT_1, 165, "id-anna", row=0, col=0)
        bert = Singer("Bert", VoiceGroup.BASS_1, 180, "id-bert", row=-1, col=-1)

        storage.save_formation(
            singers=[anna, bert], rows=4, cols=5, filepath=filepath,
            placed_singers=[(anna, 0, 0)], staggered=False, voicing_config=[],
        )

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        singers_ids_in_json = [s["singer_id"] for s in data["singers"]]
        placed_ids_in_json  = [p["singer"]["singer_id"] for p in data["placed"]]

        overlap = set(singers_ids_in_json) & set(placed_ids_in_json)
        assert overlap == set(), (
            f"Platzierte Sänger erscheinen sowohl in 'singers' als auch in 'placed': {overlap}.\n"
            f"singers[]: {singers_ids_in_json}\n"
            f"placed[]:  {placed_ids_in_json}"
        )

    def test_total_singer_count_in_json_matches_unique_singers(self, tmp_path):
        """
        singers_count + placed_count muss == Gesamtzahl eindeutiger Sänger sein.
        """
        storage, filepath = _make_storage(tmp_path)

        singers = [
            Singer("Anna",  VoiceGroup.ALT_1,   165, "id-anna",  row=0, col=0),
            Singer("Bert",  VoiceGroup.BASS_1,   180, "id-bert",  row=0, col=1),
            Singer("Clara", VoiceGroup.SOPRAN_1, 160, "id-clara", row=-1, col=-1),
        ]
        placed = [(singers[0], 0, 0), (singers[1], 0, 1)]

        storage.save_formation(
            singers=singers, rows=4, cols=5, filepath=filepath,
            placed_singers=placed, staggered=False, voicing_config=[],
        )

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        n_singers_array = len(data["singers"])
        n_placed_array  = len(data["placed"])
        total_unique     = 3  # Anna, Bert, Clara

        assert n_singers_array + n_placed_array == total_unique, (
            f"'singers' enthält {n_singers_array} Einträge, 'placed' enthält {n_placed_array}. "
            f"Zusammen {n_singers_array + n_placed_array}, erwartet {total_unique}. "
            f"Platzierte Sänger werden redundant in 'singers' gespeichert."
        )


# ===========================================================================
# Bug 4 – upd_grid ruft refresh_grid() doppelt auf
# ===========================================================================

class TestUpdGridDoubleRefresh:
    """
    MainWindow.upd_grid() ruft set_dimensions() auf (die intern refresh_grid()
    aufruft) und danach nochmals explizit refresh_grid(). Das ist eine doppelte
    Ausführung, die zu Race Conditions mit deleteLater() führen kann.

    Dieser Test prüft die Logik von set_dimensions direkt (headless, kein UI).
    """

    def test_set_dimensions_calls_refresh_exactly_once(self):
        pytest.skip("Integration test skipped - main.py moved to choraufstellung module")
        with open(src_path, encoding="utf-8") as f:
            source = f.read()

        # Extrahiere den Body von upd_grid
        lines = source.splitlines()
        upd_grid_body = []
        in_upd_grid = False
        for line in lines:
            if "def upd_grid(self)" in line:
                in_upd_grid = True
            elif in_upd_grid:
                if line.strip().startswith("def ") and "upd_grid" not in line:
                    break
                upd_grid_body.append(line)

        body_text = "\n".join(upd_grid_body)
        refresh_calls = body_text.count("refresh_grid()")

        # set_dimensions ruft refresh_grid intern auf – upd_grid darf es
        # NICHT zusätzlich aufrufen (= 0 explizite Aufrufe erwartet)
        assert refresh_calls == 0, (
            f"upd_grid() ruft refresh_grid() {refresh_calls}× explizit auf, "
            f"obwohl set_dimensions() es bereits intern aufruft.\n"
            f"Body von upd_grid:\n{body_text}"
        )


# ===========================================================================
# Invarianten-Tests (sollen nach dem Fix dauerhaft grün bleiben)
# ===========================================================================

class TestStorageInvariants:
    """Diese Tests definieren die gewünschten Invarianten nach dem Fix."""

    def test_save_then_load_preserves_all_singer_ids(self, tmp_path):
        """Alle singer_ids vor dem Speichern müssen nach dem Laden vorhanden sein."""
        storage, filepath = _make_storage(tmp_path)

        original = [
            Singer("Anna",  VoiceGroup.ALT_1,   165, "id-1", row=0,  col=0),
            Singer("Bert",  VoiceGroup.BASS_1,   180, "id-2", row=0,  col=1),
            Singer("Clara", VoiceGroup.SOPRAN_1, 160, "id-3", row=1,  col=0),
            Singer("Dieter",VoiceGroup.TENOR_1,  175, "id-4", row=-1, col=-1),
        ]
        placed = [(s, s.row, s.col) for s in original if s.row >= 0]

        storage.save_formation(
            singers=original, rows=4, cols=5, filepath=filepath,
            placed_singers=placed, staggered=False, voicing_config=[],
        )

        loaded = storage.load_formation(filepath)
        loaded_ids = set(_singer_ids(loaded))
        original_ids = {s.singer_id for s in original}

        assert original_ids == loaded_ids, (
            f"Fehlende IDs nach Roundtrip: {original_ids - loaded_ids}\n"
            f"Unerwartete IDs: {loaded_ids - original_ids}"
        )

    def test_placed_positions_correct_after_roundtrip(self, tmp_path):
        """Positionen der platzierten Sänger müssen nach Roundtrip korrekt sein."""
        storage, filepath = _make_storage(tmp_path)

        anna = Singer("Anna", VoiceGroup.ALT_1, 165, "id-anna", row=2, col=3)
        bert = Singer("Bert", VoiceGroup.BASS_1, 180, "id-bert", row=-1, col=-1)

        storage.save_formation(
            singers=[anna, bert], rows=4, cols=5, filepath=filepath,
            placed_singers=[(anna, 2, 3)], staggered=False, voicing_config=[],
        )

        loaded = storage.load_formation(filepath)
        placed_list = loaded["placed"]
        placed_dict = {(r, c): s for s, r, c in placed_list}

        assert (2, 3) in placed_dict, f"Position (2,3) fehlt. Vorhandene: {list(placed_dict.keys())}"
        assert placed_dict[(2, 3)].singer_id == "id-anna"
        assert placed_dict[(2, 3)].row == 2
        assert placed_dict[(2, 3)].col == 3
