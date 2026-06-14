# Sub-Plan: Mixin-Inflation auflösen (A-1)

| Feld | Wert |
|------|------|
| **Quelle** | `docs/reports/2026-06-14_code-review.md` — **A-1** (Mixin-Klassen-Pyramide) |
| **Bezug** | `plans/2026-06-14_m4_findings.md` — Sprint 2 / Cluster E / A1-SUBPLAN-A |
| **Status** | 📝 **Vorbereitet** (Sprint 2.8) — Implementation Sprint 3 |
| **Prio** | P1 |
| **Aufwand** | L (2-3 Personentage) |
| **Risiko** | Hoch (Diamond-Problem-Auflösung) |

## 🎯 Ziel

`MainWindow`'s Mixin-Pyramide auflösen durch **Komposition**:

- `ExportCoreMixin`, `ExportJsonSyncMixin`, `ExportTabSpecificMixin` → `ExportController(QObject)`
- `UpdateController` als eigenständige `QObject`-Klasse (nicht Mixin)
- `TabRouter` analog
- `ChorAufstellungLauncherMixin` → `ChorAufstellungTab` (reine Komposition)

Akzeptanz: `MainWindow` < 200 LOC, alle Controller eigenständig testbar.

## 🏗️ Architektur

### Variante A — Komposition (empfohlen ✅)

```
MainWindow (QMainWindow)
   ├── self.export_controller = ExportController(self)
   ├── self.update_controller = UpdateController(self)
   ├── self.tab_router = TabRouter(self)
   ├── self.choraufstellung_tab = ChorAufstellungTab(self)
   └── self.menu, self.toolbar, ... (nur noch UI-Shell)
```

**Vorteile:**
- Diamond-Problem aufgelöst
- Controller einzeln testbar
- MRO bleibt linear
- Klare Lifecycle (Controller als QObject-Members)

**Nachteile:**
- Boilerplate für `self.export_controller.foo()` statt `self.foo()`
- Etwas mehr Tipparbeit beim Methoden-Aufruf
- Bestehende Tests müssen `self.export_controller` statt `self` aufrufen

### Variante B — Mixin beibehalten (abgelehnt ❌)

- Vorteile: Kein Refactor.
- Nachteile: Diamond-Problem bleibt, MRO wächst.

### Variante C — Trait-Bibliothek (z. B. `traits`, `pyface`) (abgelehnt ❌)

- Vorteile: Saubere Komposition.
- Nachteile: Neue Dependency, nicht im Standard-Stack.

## 📋 Akzeptanzkriterien

| # | Kriterium | Verifikation |
|---|-----------|--------------|
| A1 | `MainWindow` < 200 LOC (aktuell: 924 LOC) | `wc -l main_window.py` |
| A2 | `ExportController`, `UpdateController`, `TabRouter` als eigenständige Klassen mit `setUp(self, host)` | Inspektion |
| A3 | Kein Mixin-MRO-Konflikt beim Import | pytest mit `-W error::DeprecationWarning` |
| A4 | Alle bestehenden Tests gruen | pytest |
| A5 | `ExportController` hat `pyqtSignal(str) export_finished` | Test mit `qtbot.waitSignal` |

## 🧩 Implementation-Skizze

### Phase 1 — `ExportController(QObject)` extrahieren (1 d)

```python
class ExportController(QObject):
    export_finished = pyqtSignal(str)  # path
    export_failed = pyqtSignal(str)    # error_message

    def __init__(self, host, parent=None):
        super().__init__(parent)
        self._host = host

    def export_csv(self): ...
    def export_pdf(self): ...
    def export_libreoffice(self): ...
    # etc — Methoden aus den 3 Mixins konsolidieren
```

### Phase 2 — `UpdateController(QObject)` extrahieren (0,5 d)

```python
class UpdateController(QObject):
    check_finished = pyqtSignal(dict)  # version info
    update_finished = pyqtSignal(bool, str)  # success, msg

    def __init__(self, parent=None):
        super().__init__(parent)
        self._check_worker = None
        self._pull_worker = None

    def check_version(self): ...
    def do_update(self): ...
```

### Phase 3 — `TabRouter` extrahieren (0,5 d)

```python
class TabRouter(QObject):
    tab_changed = pyqtSignal(int)

    def __init__(self, tab_widget, parent=None):
        super().__init__(parent)
        self._tabs = tab_widget
        self._tabs.currentChanged.connect(self.tab_changed.emit)

    def switch_to(self, name: str): ...
    def current_index(self) -> int: ...
```

### Phase 4 — `MainWindow` verkleinern (0,5 d)

```python
class MainWindow(QMainWindow):
    def __init__(self, db_path=None):
        super().__init__()
        self.db = Database(db_path)
        # Controller als Komposition:
        self.export_controller = ExportController(self)
        self.update_controller = UpdateController(self)
        self.tab_router = TabRouter(self.tabs)
        # UI-Setup:
        self._setup_ui()  # 100-200 LOC
        self._create_menu_bar()  # 50-100 LOC
        # etc.
```

### Phase 5 — Test-Migration (0,5 d)

```python
# Vorher:
class TestExportCoreMixin:
    def test_export_csv(self, stub_main_window):
        stub_main_window._export_csv()  # Mixin-Methode

# Nachher:
class TestExportController:
    def test_export_csv(self, stub_host):
        controller = ExportController(stub_host)
        controller.export_csv()  # Komposition
```

## 🛡️ Risk-Assessment

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Tests brechen weil `self._foo()` zu `self.controller.foo()` wird | Hoch | Mittel | Phase 5 mit schrittweiser Migration |
| `host` (MainWindow) wird zur zirkulaeren Referenz | Mittel | Niedrig | `weakref` oder expliziter `set_host()` |
| Diamond-Problem zur Laufzeit nicht erkennbar | Niedrig | Mittel | MRO-Inspektion in Test |
| `ExportController` zu gross (> 500 LOC) | Mittel | Niedrig | Sub-Controller: `CsvExportController`, `PdfExportController` |

## 📅 Sprint-Einordnung

- **Vorbereitung** (Sprint 2.8, dieses Dokument): ✅
- **Implementation** (Sprint 3, ~3 Tage)

## 🔗 Verweise

- Code-Review: `docs/reports/2026-06-14_code-review.md` — A-1
- Haupt-Plan: `plans/2026-06-14_m4_findings.md` — Sprint 2
- Sub-Plan-Index: `plans/2026-06-14_m4_anhang_b_subplans.md`
- Original-Dateien:
  - `chormanager/ui/main_window.py:924` (Ziel: < 200 LOC)
  - `chormanager/ui/export_controller.py:1-883` (Mixins)
  - `chormanager/ui/update_controller.py:1-114` (Mixins)
  - `chormanager/ui/tab_router.py:1-...` (Mixins)
  - `chormanager/ui/choraufstellung_launcher.py:88-308` (Mixins)

---

**Erstellt:** 2026-06-14 — Sprint 2.8
