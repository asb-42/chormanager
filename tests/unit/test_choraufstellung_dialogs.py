"""TDD RED: Regression tests for M-2 Schritt 4 — 3 Dialoge nach widgets/dialogs.py.

The three dialog classes (``AddSingerDialog``, ``AffinityDialog``,
``VoicingConfigDialog``) currently live inside
``chormanager/choraufstellung/main.py`` (Z. 1207-1327).  M-2 Schritt 4
moves them to ``chormanager/choraufstellung/widgets/dialogs.py`` and
re-exports them from ``main.py`` for backward compatibility with any
external caller.

The new module is tested both via the new import path
(``widgets.dialogs``) and via the old re-export path
(``choraufstellung.main``).  See plans/2026-06-12_m2_choraufstellung_refactor.md,
Schritt 4.
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Module shape: widgets/dialogs.py exists and exports the 3 classes
# ---------------------------------------------------------------------------

class TestDialogsModuleShape:
    def test_widgets_dialogs_module_exists(self):
        try:
            import widgets.dialogs as m  # noqa: F401
        except ModuleNotFoundError as exc:
            pytest.fail(
                f"widgets.dialogs module not yet created: {exc}"
            )

    def test_widgets_dialogs_exports_add_singer_dialog(self):
        from widgets.dialogs import AddSingerDialog
        assert AddSingerDialog is not None

    def test_widgets_dialogs_exports_affinity_dialog(self):
        from widgets.dialogs import AffinityDialog
        assert AffinityDialog is not None

    def test_widgets_dialogs_exports_voicing_config_dialog(self):
        from widgets.dialogs import VoicingConfigDialog
        assert VoicingConfigDialog is not None


# ---------------------------------------------------------------------------
# AddSingerDialog
# ---------------------------------------------------------------------------

class _MockSinger:
    """Stand-in for ``singer_model.Singer`` carrying the four
    attributes the dialog actually touches: ``name``, ``voice_group``,
    ``height``, ``singer_id`` and ``affinity`` (the last is ``None``
    by default and only set when the singer has a partner)."""

    def __init__(self, name="", vg="Sopran 1", height=0, singer_id="42",
                 affinity=None):
        self.name = name
        self.voice_group = vg
        self.height = height
        self.singer_id = singer_id
        self.affinity = affinity


class TestAddSingerDialog:
    def test_new_singer_returns_none_when_name_empty(self, qtbot):
        from widgets.dialogs import AddSingerDialog
        dlg = AddSingerDialog()
        # Simulate empty name (the default).
        assert dlg.get_singer() is None

    def test_new_singer_creates_singer_with_typed_name(self, qtbot):
        from widgets.dialogs import AddSingerDialog
        from singer_model import Singer, VoiceGroup
        dlg = AddSingerDialog()
        dlg.n.setText("Müller, Anna")
        dlg.v.setCurrentText("Sopran 1")
        dlg.h.setText("170")
        result = dlg.get_singer()
        assert isinstance(result, Singer)
        assert result.name == "Müller, Anna"
        assert result.height == 170

    def test_new_singer_zero_height_when_field_empty(self, qtbot):
        from widgets.dialogs import AddSingerDialog
        from singer_model import Singer
        dlg = AddSingerDialog()
        dlg.n.setText("X")
        dlg.h.setText("")
        result = dlg.get_singer()
        assert isinstance(result, Singer)
        assert result.height == 0

    def test_edit_singer_preserves_id_and_voice_group(self, qtbot):
        from widgets.dialogs import AddSingerDialog
        from singer_model import VoiceGroup
        original = _MockSinger(
            name="Schmidt",
            vg=VoiceGroup.SOPRAN_2 if hasattr(VoiceGroup, "SOPRAN_2") else "Sopran 2",
            height=165,
            singer_id="abc-123",
        )
        dlg = AddSingerDialog(singer=original)
        dlg.n.setText("Schmidt, Maria")
        dlg.h.setText("166")
        result = dlg.get_singer()
        assert result.singer_id == "abc-123"  # ID preserved
        assert result.name == "Schmidt, Maria"
        assert result.height == 166


# ---------------------------------------------------------------------------
# AffinityDialog
# ---------------------------------------------------------------------------

class TestAffinityDialog:
    def test_get_affinity_singer_id_returns_selected_id(self, qtbot):
        from widgets.dialogs import AffinityDialog
        singer = _MockSinger(name="Anna", singer_id="s1")
        other = [
            _MockSinger(name="Bert", singer_id="s2"),
            _MockSinger(name="Carla", singer_id="s3"),
        ]
        dlg = AffinityDialog(singer=singer, all_singers=[singer, *other])
        # Pick the "Carla" entry (index 2 in the combo: 0 -> Bert, 1 -> Carla).
        # We use setCurrentIndex with a single call to avoid the
        # editable QComboBox text-already-changed edge case.
        dlg.combo.setCurrentIndex(1)  # Bert (s2)
        dlg.combo.setCurrentText("Carla")  # Editable: text matches s3
        # get_affinity_singer_id falls back to name-match if currentData
        # is None (which happens when the user types into the editable
        # combo), so this path must return s3.
        assert dlg.get_affinity_singer_id() == "s3"

    def test_get_affinity_returns_empty_when_combo_cleared(self, qtbot):
        from widgets.dialogs import AffinityDialog
        singer = _MockSinger(name="Anna", singer_id="s1")
        other = _MockSinger(name="Bert", singer_id="s2")
        dlg = AffinityDialog(singer=singer, all_singers=[singer, other])
        dlg.clear_affinity()
        # After clear, get_affinity_singer_id must return "".
        assert dlg.get_affinity_singer_id() == ""


# ---------------------------------------------------------------------------
# VoicingConfigDialog
# ---------------------------------------------------------------------------

class TestVoicingConfigDialog:
    def test_set_active_marks_checkboxes(self, qtbot, monkeypatch):
        # The dialog calls ``load_voice_groups_config()`` from
        # ``config`` at construction time.  Patch it to a stable,
        # test-only fixture.
        monkeypatch.setattr(
            "config.load_voice_groups_config",
            lambda: [
                {"id": "Sopran 1", "color": "#ff0000"},
                {"id": "Alt", "color": "#00ff00"},
                {"id": "Tenor", "color": "#0000ff"},
            ],
        )
        from widgets.dialogs import VoicingConfigDialog
        dlg = VoicingConfigDialog()
        dlg.set_active({"Sopran 1", "Tenor"})
        active = set(dlg.get_active())
        assert active == {"Sopran 1", "Tenor"}

    def test_get_active_initially_empty(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            "config.load_voice_groups_config",
            lambda: [{"id": "Sopran 1", "color": "#ff0000"}],
        )
        from widgets.dialogs import VoicingConfigDialog
        dlg = VoicingConfigDialog()
        assert dlg.get_active() == []
