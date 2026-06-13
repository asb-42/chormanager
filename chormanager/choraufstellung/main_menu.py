"""Main-menu builder for ChorAufstellung (M-2 Schritt 13).

Encapsulates the menu/toolbar construction that was previously inlined
in :meth:`MainWindow.menu` (Z. 386-466 in the post-Schritt-12 main.py,
~80 LOC).

The builder:

* Creates the sub-menus: Datei, Bearbeiten, Aufstellen, Konfigurieren,
  Ansicht, Hilfe
* Wires the QAction ``triggered`` signals to the host's methods
* Stashes the action handles (``swap_action``, ``undo_action``,
  ``redo_action``, ``actionLight``, ``actionDark``, ``theme_group``)
  on the host so other code paths can toggle/enable them

Design
------
* **Duck-typed host:** the builder reads ``host.menuBar()``,
  ``host.grid`` (with the auto-arrange methods), and various
  ``host.<action>`` callables. No import of :class:`MainWindow`.
* **Pure-Qt:** runs only inside a real QApplication (the legacy
  ``menu()`` method was no different). Tests use ``qtbot`` with
  ``QT_QPA_PLATFORM=offscreen``.
* **Action-Group pattern:** the light/dark actions live in an
  exclusive :class:`QActionGroup` so only one is checked at a time.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:  # pragma: no cover
    pass


class MainMenuBuilder:
    """Build the main menu bar for a :class:`MainWindow`-like host."""

    def __init__(self, host: Any) -> None:
        """Store the host (the MainWindow)."""
        self._host = host

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def build(self) -> None:
        """Populate ``host.menuBar()`` with the six sub-menus."""
        m = self._host.menuBar()
        self._build_datei(m)
        self._build_bearbeiten(m)
        self._build_aufstellen(m)
        self._build_konfigurieren(m)
        self._build_ansicht(m)
        # Optional: legend (was inline in the legacy method)
        if hasattr(self._host, "_menu_legenda"):
            self._host._menu_legenda()
        self._build_hilfe(m)

    # ------------------------------------------------------------------
    # sub-menu builders (one per logical group)
    # ------------------------------------------------------------------

    def _add(self, menu: Any, label: str, *, shortcut: Optional[str] = None,
             triggered: Any = None) -> Any:
        """Helper: create a QAction and add it to ``menu``."""
        from PyQt6.QtGui import QAction  # type: ignore

        kwargs: dict = {}
        if shortcut is not None:
            kwargs["shortcut"] = shortcut
        if triggered is not None:
            kwargs["triggered"] = triggered
        action = QAction(label, self._host, **kwargs)
        menu.addAction(action)
        return action

    def _build_datei(self, m: Any) -> None:
        from PyQt6.QtGui import QAction  # type: ignore

        f = m.addMenu("Datei")
        f.addAction(QAction("Neu", self._host, shortcut="Ctrl+N", triggered=self._host.new_f))
        f.addAction(QAction("Öffnen...", self._host, shortcut="Ctrl+O", triggered=self._host.open_f))
        f.addAction(QAction("Speichern", self._host, shortcut="Ctrl+S", triggered=self._host.save_f))
        f.addAction(QAction("Speichern unter...", self._host, shortcut="Ctrl+Shift+S", triggered=self._host.save_as_f))
        f.addSeparator()
        f.addAction(QAction("PDF Export...", self._host, shortcut="Ctrl+E", triggered=self._host.export_pdf))
        f.addSeparator()
        f.addAction(QAction("Beenden", self._host, shortcut="Ctrl+Q", triggered=self._host.close))

    def _build_bearbeiten(self, m: Any) -> None:
        from PyQt6.QtGui import QAction  # type: ignore

        e = m.addMenu("Bearbeiten")
        e.addAction(QAction("Sänger hinzufügen", self._host,
                            shortcut="Ctrl+Shift+A", triggered=self._host.add_singer_via_menu))

        # Swap action: starts disabled, toggled by grid selection
        self._host.swap_action = QAction(
            "Positionen tauschen", self._host, shortcut="Ctrl+T",
            triggered=self._host.swap_selected_singers,
        )
        self._host.swap_action.setEnabled(False)
        e.addAction(self._host.swap_action)

        # Undo/Redo: start disabled
        self._host.undo_action = QAction(
            "Rückgängig", self._host, shortcut="Ctrl+Z",
            triggered=self._host.undo_last_action,
        )
        self._host.redo_action = QAction(
            "Wiederholen", self._host, shortcut="Ctrl+Y",
            triggered=self._host.redo_last_action,
        )
        self._host.undo_action.setEnabled(False)
        self._host.redo_action.setEnabled(False)
        e.addAction(self._host.undo_action)
        e.addAction(self._host.redo_action)

    def _build_aufstellen(self, m: Any) -> None:
        from PyQt6.QtGui import QAction  # type: ignore

        a = m.addMenu("Aufstellen")

        def _add(label: str, fn) -> None:
            act = QAction(label, self._host)
            act.triggered.connect(fn)
            a.addAction(act)

        _add("Aufstellung nach Größe", self._host.grid.auto_arrange_by_height)
        _add("Männer geteilt außen", self._host.grid.auto_arrange_men_outer)
        _add("SATB", self._host.grid.auto_arrange_satb)
        _add("SBTA", self._host.grid.auto_arrange_sbta)
        _add("S1 S2 B2 B1 T2 T1 A2 A1", self._host.grid.auto_arrange_s1s2b2b1t2t1a2a1)
        _add("S1 S2 A1 A2 T1 T2 B1 B2", self._host.grid.auto_arrange_s1s2a1a2t1t2b1b2)
        _add("S1 S2 B1 B2 T1 T2 A1 A2", self._host.grid.auto_arrange_s1s2b1b2t1t2a1a2)
        a.addSeparator()
        _add("Nähe (Singpartner)", self._host.apply_all_affinity_proximity)
        a.addSeparator()
        _add("Aufstellung zurücksetzen", self._host.reset_formation)
        a.addSeparator()
        _add("Optimiert aufstellen...", self._host.run_optimizer)

    def _build_konfigurieren(self, m: Any) -> None:
        from PyQt6.QtGui import QAction  # type: ignore

        k = m.addMenu("Konfigurieren")
        cfg_action = QAction("Besetzung konfigurieren...", self._host)
        cfg_action.setEnabled(True)
        cfg_action.triggered.connect(self._host.show_cfg)
        k.addAction(cfg_action)

    def _build_ansicht(self, m: Any) -> None:
        from PyQt6.QtGui import QAction, QActionGroup  # type: ignore

        v = m.addMenu("&Ansicht")
        self._host.theme_group = QActionGroup(self._host)
        self._host.theme_group.setExclusive(True)

        self._host.actionLight = QAction("Light", self._host)
        self._host.actionLight.setCheckable(True)
        self._host.actionLight.triggered.connect(lambda: self._host._apply_theme("light"))
        v.addAction(self._host.actionLight)
        self._host.theme_group.addAction(self._host.actionLight)

        self._host.actionDark = QAction("Dark", self._host)
        self._host.actionDark.setCheckable(True)
        self._host.actionDark.triggered.connect(lambda: self._host._apply_theme("dark"))
        v.addAction(self._host.actionDark)
        self._host.theme_group.addAction(self._host.actionDark)

    def _build_hilfe(self, m: Any) -> None:
        from PyQt6.QtGui import QAction  # type: ignore

        h = m.addMenu("&Hilfe")
        h.addAction(QAction("Über", self._host, triggered=self._host.show_about))
