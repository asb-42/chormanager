"""ChorAufstellung dialogs.

M-2 Schritt 4: extracted the three small ``QDialog`` subclasses that
used to live in ``chormanager/choraufstellung/main.py`` (formerly
Z. 1207-1327) into their own module:

- :class:`AddSingerDialog` — create or edit a single :class:`Singer`.
- :class:`AffinityDialog` — pick the affinity (Singpartner) for a
  given singer, or clear it.
- :class:`VoicingConfigDialog` — toggle which voice groups are
  currently active for the Besatzung.

The classes are re-exported from :mod:`choraufstellung.main` for
backward compatibility with any external caller that did
``from chormanager.choraufstellung.main import AddSingerDialog``.

See plans/2026-06-12_m2_choraufstellung_refactor.md, Schritt 4.
"""
from __future__ import annotations

# PyQt5/PyQt6 cross-compat: all Qt classes used below are re-exported
# from the central ``qt_compat`` module (see M-2 Schritt 1).
from qt_compat import (
    QDialog,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QCompleter,
    QPushButton,
    QCheckBox,
    QScrollArea,
    QWidget,
    Qt,
)

# Domain models — same package-relative imports as the rest of the
# choraufstellung subapp.  ``singer_model`` provides the ``Singer``
# dataclass and the ``VoiceGroup`` enum; ``config`` provides the
# voice-group config loader.
#
# We deliberately do NOT bind ``load_voice_groups_config`` to a local
# name: ``VoicingConfigDialog.__init__`` looks the function up via
# the module attribute at construction time so tests can monkeypatch
# ``config.load_voice_groups_config`` and have the change take effect
# immediately.
from singer_model import Singer, VoiceGroup
import config as _choraufstellung_config


class AddSingerDialog(QDialog):
    """Dialog for adding or editing a single :class:`Singer`.

    When constructed with a ``singer`` argument the dialog pre-fills
    its fields and preserves the singer's ``singer_id`` on save.
    When constructed without one a fresh ``Singer`` is created on
    save (with a brand-new id assigned by the caller).
    """

    def __init__(self, p=None, singer=None):
        super().__init__(p)
        self.singer = singer
        self.setWindowTitle(
            "Sänger bearbeiten" if singer else "Sänger hinzufügen"
        )
        l = QFormLayout(self)
        self.n = QLineEdit()
        self.n.setPlaceholderText("Nachname, Vorname")
        if singer:
            self.n.setText(singer.name)
        l.addRow("Name:", self.n)

        self.v = QComboBox()
        for vg in VoiceGroup:
            self.v.addItem(
                vg.value if hasattr(vg, "value") else str(vg), vg
            )
        if singer:
            vg_val = (
                singer.voice_group.value
                if hasattr(singer.voice_group, "value")
                else str(singer.voice_group)
            )
            idx = self.v.findText(vg_val)
            if idx >= 0:
                self.v.setCurrentIndex(idx)
        l.addRow("Stimmgruppe:", self.v)

        self.h = QLineEdit()
        if singer and singer.height > 0:
            self.h.setText(str(singer.height))
        l.addRow("Größe (cm):", self.h)

        bl = QHBoxLayout()
        bl.addWidget(QPushButton("Speichern", clicked=self.accept))
        bl.addWidget(QPushButton("Abbrechen", clicked=self.reject))
        l.addRow(bl)

    def get_singer(self):
        """Return a :class:`Singer` built from the form fields, or
        ``None`` if the name field is blank.

        On edit, the original singer's ``singer_id`` is preserved so
        load/save round-trips keep stable identities.
        """
        n = self.n.text().strip()
        if not n:
            return None
        h = 0
        try:
            h = int(self.h.text().strip()) if self.h.text().strip() else 0
        except (ValueError, TypeError):
            # Non-numeric input silently falls back to 0; the
            # downstream code path accepts any integer.
            pass
        if self.singer:
            return Singer(
                n, self.v.currentData(), h, self.singer.singer_id
            )
        return Singer(n, self.v.currentData(), h)


class AffinityDialog(QDialog):
    """Dialog for choosing the affinity (Singpartner) for ``singer``.

    The combo is editable with a QCompleter so users can type a name;
    if the typed name matches one of ``all_singers`` exactly, that
    singer's id is returned.  An empty result string means "no
    affinity" (cleared).
    """

    def __init__(self, p=None, singer=None, all_singers=None):
        super().__init__(p)
        self.singer = singer
        self.all_singers = all_singers or []
        self.setWindowTitle(f"Nähe setzen für {singer.name}")
        self.setMinimumWidth(350)
        l = QVBoxLayout(self)
        l.addWidget(
            QLabel(f"Singpartner für <b>{singer.name}</b> auswählen:")
        )

        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.lineEdit().setPlaceholderText(
            "Name eingeben oder auswählen..."
        )

        other_singers = [
            s
            for s in self.all_singers
            if s.singer_id != singer.singer_id
        ]
        for s in other_singers:
            self.combo.addItem(s.name, s.singer_id)

        if singer.affinity:
            idx = self.combo.findData(singer.affinity)
            if idx >= 0:
                self.combo.setCurrentIndex(idx)

        completer = QCompleter(
            [s.name for s in other_singers], self
        )
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.combo.setCompleter(completer)

        l.addWidget(self.combo)

        clear_btn = QPushButton("Keine Nähe")
        clear_btn.clicked.connect(self.clear_affinity)
        l.addWidget(clear_btn)

        bl = QHBoxLayout()
        bl.addWidget(QPushButton("Speichern", clicked=self.accept))
        bl.addWidget(QPushButton("Abbrechen", clicked=self.reject))
        l.addLayout(bl)

    def clear_affinity(self):
        """Reset the combo to an empty selection."""
        self.combo.setCurrentIndex(-1)
        self.combo.setCurrentText("")

    def get_affinity_singer_id(self):
        """Return the chosen singer's id, or ``""`` if none / the
        typed text did not match any known singer."""
        text = self.combo.currentText().strip()
        data = self.combo.currentData()
        if data:
            return data
        for s in self.all_singers:
            if s.name == text:
                return s.singer_id
        return ""


class VoicingConfigDialog(QDialog):
    """Dialog for toggling which voice groups are currently active.

    The list of available voice groups is loaded from
    :func:`config.load_voice_groups_config` at construction time and
    rendered as colored checkboxes.
    """

    def __init__(self, p=None):
        super().__init__(p)
        self.setStyleSheet("QDialog { background: #f9f6f0; }")
        self.setWindowTitle("Besatzung konfigurieren")
        self.resize(300, 350)
        l = QVBoxLayout(self)
        l.addWidget(QLabel("Aktive Stimmgruppen:"))
        s = QScrollArea()
        s.setWidgetResizable(True)
        l.addWidget(s)
        c = QWidget()
        self.vl = QVBoxLayout(c)
        s.setWidget(c)
        self.chk = {}
        for vg in _choraufstellung_config.load_voice_groups_config():
            cb = QCheckBox(vg["id"])
            color = vg["color"]
            cb.setStyleSheet(
                f"""
                QCheckBox::indicator {{
                    width: 20px;
                    height: 20px;
                    border: 2px solid {color};
                    background-color: white;
                    border-radius: 3px;
                }}
                QCheckBox::indicator:hover {{
                    background-color: #f8f8f8;
                }}
                QCheckBox::indicator:checked {{
                    background-color: {color};
                    border: 2px solid {color};
                    color: white;
                }}
                QCheckBox {{
                    spacing: 12px;
                    font-size: 10pt;
                }}
            """
            )
            self.chk[vg["id"]] = cb
            self.vl.addWidget(cb)
        bl = QHBoxLayout()
        bl.addWidget(QPushButton("OK", clicked=self.accept))
        bl.addWidget(QPushButton("Abbrechen", clicked=self.reject))
        l.addLayout(bl)

    def set_active(self, act):
        """Mark the voice groups in the iterable ``act`` as checked.

        Groups not in ``act`` are unchecked.  ``act`` may be a
        ``set``, ``list`` or any iterable of group-name strings.
        """
        act_set = set(act)
        for g, c in self.chk.items():
            c.setChecked(g in act_set)

    def get_active(self):
        """Return the list of currently checked voice-group names."""
        return [g for g, c in self.chk.items() if c.isChecked()]
