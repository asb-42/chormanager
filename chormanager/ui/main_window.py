"""Main window for ChorManager."""

import sys
from pathlib import Path
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QAction

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QMenuBar,
    QMenu,
    QToolBar,
    QLabel,
    QSizePolicy,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QDialog,
    QDateEdit,
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QDate, QTimer
from PyQt6.QtGui import QAction, QKeySequence

from ..data.database import Database
from ..domain.repository import SingerRepository
from ..history.service import (
    HistoryService,
    CreateSingerCommand,
    UpdateSingerCommand,
    DeleteSingerCommand,
)
from ..backup.service import AutoBackupService
from ..config import load_voice_groups, load_fields, get_theme, set_theme


class SingerDialog(QDialog):
    """Dialog for adding/editing a singer."""

    def __init__(self, singer=None, parent=None):
        """Initialize dialog.

        Args:
            singer: Singer to edit, or None for new singer.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.singer = singer
        self._setup_ui()

        if singer:
            self._populate_from_singer()

    def _setup_ui(self):
        """Set up the UI."""
        self.setWindowTitle(
            "Sänger hinzufügen" if not self.singer else "Sänger bearbeiten"
        )
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        voice_choices = load_voice_groups()
        voice_names = [g["name"] for g in voice_choices]

        fields = load_fields()

        self.inputs = {}

        for field in fields:
            name = field["name"]
            label = field["label"]
            field_type = field["type"]

            if field_type == "computed":
                continue

            elif field_type == "integer":
                widget = QLineEdit()
                self.inputs[name] = widget
                layout.addRow(label, widget)

            if field_type == "string":
                widget = QLineEdit()
                self.inputs[name] = widget
                layout.addRow(label, widget)

            elif field_type == "text":
                widget = QTextEdit()
                widget.setMaximumHeight(80)
                self.inputs[name] = widget
                layout.addRow(label, widget)

            elif field_type == "date":
                widget = QDateEdit()
                widget.setCalendarPopup(True)
                widget.setDate(QDate.currentDate())
                self.inputs[name] = widget
                layout.addRow(label, widget)

            elif field_type == "yearmonth":
                layout.addRow(label, None)
                year_layout = QHBoxLayout()
                year_layout.addWidget(QLabel("Monat:"))
                month_combo = QComboBox()
                month_combo.addItem("", None)
                for i in range(1, 13):
                    month_combo.addItem(f"{i:02d}", i)
                year_layout.addWidget(month_combo)
                self.inputs[f"{name}_month"] = month_combo

                year_layout.addWidget(QLabel("Jahr:"))
                year_combo = QComboBox()
                year_combo.addItem("", None)
                for year in range(2015, 2031):
                    year_combo.addItem(str(year), year)
                year_layout.addWidget(year_combo)
                self.inputs[f"{name}_year"] = year_combo

                layout.addRow(year_layout)

            elif field_type == "voice_group":
                widget = QComboBox()
                widget.addItem("", None)
                for vg in voice_names:
                    widget.addItem(vg, vg)
                self.inputs[name] = widget
                layout.addRow(label, widget)

            elif field_type == "email":
                widget = QLineEdit()
                self.inputs[name] = widget
                layout.addRow(label, widget)

            elif field_type == "choice":
                widget = QComboBox()
                choices = field.get("choices", [])
                widget.addItem("", None)
                for choice in choices:
                    widget.addItem(choice, choice)
                self.inputs[name] = widget
                layout.addRow(label, widget)

            elif field_type == "uuid":
                widget = QLineEdit()
                self.inputs[name] = widget
                layout.addRow(label, widget)

        button_box = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Abbrechen")
        cancel_button.clicked.connect(self.reject)
        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)

        layout.addRow(button_box)

        if self.singer:
            age = self.singer.age()
            if age is not None:
                age_label = QLabel(f"Alter: {age} Jahre")
                layout.addRow(age_label)

    def _populate_from_singer(self):
        """Populate fields from singer data."""
        singer_dict = self.singer.to_dict()

        for name, widget in self.inputs.items():
            value = singer_dict.get(name)

            if value is None:
                continue

            if isinstance(widget, QLineEdit):
                widget.setText(str(value))

            elif isinstance(widget, QTextEdit):
                widget.setPlainText(str(value))

            elif isinstance(widget, QDateEdit):
                if value:
                    date = QDate.fromString(value, Qt.DateFormat.ISODate)
                    if date.isValid():
                        widget.setDate(date)

            elif isinstance(widget, QComboBox):
                if name.endswith("_year") or name.endswith("_month"):
                    val = singer_dict.get(name)
                    if val:
                        index = widget.findData(val)
                        if index >= 0:
                            widget.setCurrentIndex(index)

    def get_data(self):
        """Get form data as dictionary."""
        data = {}
        fields = load_fields()
        field_types = {f["name"]: f.get("type", "string") for f in fields}

        for name, widget in self.inputs.items():
            if isinstance(widget, QLineEdit):
                value = widget.text().strip()
                if not value:
                    data[name] = None
                elif field_types.get(name) == "integer":
                    try:
                        data[name] = int(value)
                    except ValueError:
                        data[name] = None
                else:
                    data[name] = value

            elif isinstance(widget, QTextEdit):
                value = widget.toPlainText().strip()
                data[name] = value if value else None

            elif isinstance(widget, QDateEdit):
                date = widget.date()
                if date.isValid():
                    data[name] = date.toString(Qt.DateFormat.ISODate)

            elif isinstance(widget, QComboBox):
                value = widget.currentData()
                data[name] = value

        # yearmonth fields are now split into name_year and name_month
        # so just pass through if present
        for name in ("joined_year", "joined_month", "left_year", "left_month"):
            if name in data and data[name] is None:
                del data[name]

        return data


class MainWindow(QMainWindow):
    """Main window for ChorManager."""

    def __init__(self, db_path: str = None):
        """Initialize main window.

        Args:
            db_path: Path to database file.
        """
        super().__init__()

        self.db_path = db_path
        self.db = Database(db_path)
        self.db.connect()
        self.db.create_tables()

        self.singer_repo = SingerRepository(self.db)
        self.history = HistoryService(max_entries=100)
        self.backup_service = AutoBackupService()

        if self.db_path:
            self.backup_service.backup_on_start(self.db_path)

        self._setup_ui()

        # Initialize context toolbar after UI setup
        self._update_context_toolbar(0, None)

        # Initialize info labels
        self._update_info_labels()

        # Apply last active project filter to tabs
        if self.projects_tab.current_project:
            self._on_project_changed()

        # Load last active event
        from ..config import get_last_active_event_id

        last_event_id = get_last_active_event_id()
        if last_event_id:
            event = self.events_tab.event_repo.get_by_id(last_event_id)
            if event:
                self.current_event = event
                self._update_info_labels()
                if hasattr(self, "choraufstellung_tab"):
                    self.choraufstellung_tab.set_event(event)

        saved_theme = get_theme()
        if saved_theme == "dark":
            self._set_dark_theme()

    def _setup_ui(self):
        """Set up the UI."""
        self.setWindowTitle("ChorManager")
        self.setGeometry(100, 100, 800, 600)

        self._create_menu_bar()
        self._create_info_bar()
        self._create_tool_bar()
        self._create_central_widget()
        self._create_status_bar()

    def _create_info_bar(self):
        """Create info bar below menu bar."""
        self.info_bar = QWidget()
        self.info_bar.setObjectName("infoBarWidget")
        self.info_bar.setMinimumHeight(45)
        self.info_bar.setStyleSheet("""
            QWidget {
                background-color: #e8f4f8;
                border-bottom: 2px solid #4a90d9;
                padding: 5px;
            }
            QLabel {
                font-weight: bold;
                color: #2c3e50;
                padding: 4px 12px;
                border-radius: 4px;
            }
            QLabel#projectInfoLabel {
                background-color: #4a90d9;
                color: white;
            }
            QLabel#eventInfoLabel {
                background-color: #e67e22;
                color: white;
            }
        """)

        info_layout = QHBoxLayout(self.info_bar)
        info_layout.setContentsMargins(15, 8, 15, 8)
        info_layout.setSpacing(15)

        # Projekt-Status Label
        project_status_label = QLabel("Aktives Projekt:")
        project_status_label.setStyleSheet("font-weight: normal; color: #666;")
        info_layout.addWidget(project_status_label)

        self.project_info_label = QLabel("Keines")
        self.project_info_label.setObjectName("projectInfoLabel")
        self.project_info_label.setVisible(True)
        self.project_info_label.setWordWrap(False)
        self.project_info_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        info_layout.addWidget(self.project_info_label)

        # Besetzung-Status Label
        besetzung_status_label = QLabel("Aktive Besetzung:")
        besetzung_status_label.setStyleSheet("font-weight: normal; color: #666;")
        info_layout.addWidget(besetzung_status_label)

        self.besetzung_info_label = QLabel("Keine")
        self.besetzung_info_label.setObjectName("besetzungInfoLabel")
        self.besetzung_info_label.setVisible(True)
        self.besetzung_info_label.setWordWrap(False)
        self.besetzung_info_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        info_layout.addWidget(self.besetzung_info_label)

        info_layout.addStretch()

        # Termin-Status Label
        event_status_label = QLabel("Aktiver Termin:")
        event_status_label.setStyleSheet("font-weight: normal; color: #666;")
        info_layout.addWidget(event_status_label)

        self.event_info_label = QLabel("Keiner")
        self.event_info_label.setObjectName("eventInfoLabel")
        self.event_info_label.setVisible(True)
        self.event_info_label.setWordWrap(False)
        self.event_info_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        info_layout.addWidget(self.event_info_label)

        info_layout.addStretch()

        # Add info bar to main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.menuBar())
        main_layout.addWidget(self.info_bar)

        # Create container for menu + info bar
        menu_container = QWidget()
        menu_container.setLayout(main_layout)
        self.setMenuWidget(menu_container)

    def _create_menu_bar(self):
        """Create menu bar."""
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&Datei")

        export_csv_action = QAction("Als CSV exportieren...", self)
        export_csv_action.triggered.connect(self._export_csv)
        file_menu.addAction(export_csv_action)

        export_pdf_action = QAction("Als PDF exportieren...", self)
        export_pdf_action.triggered.connect(self._export_pdf)
        file_menu.addAction(export_pdf_action)

        export_lo_action = QAction("Als LibreOffice exportieren...", self)
        export_lo_action.triggered.connect(self._export_libreoffice)
        file_menu.addAction(export_lo_action)

        file_menu.addSeparator()

        exit_action = QAction("Beenden", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menubar.addMenu("&Bearbeiten")

        undo_action = QAction("Rückgängig", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self._undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("Wiederholen", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self._redo)
        edit_menu.addAction(redo_action)

        view_menu = menubar.addMenu("&Ansicht")

        light_theme_action = QAction("Hell", self)
        light_theme_action.triggered.connect(self._set_light_theme)
        view_menu.addAction(light_theme_action)

        dark_theme_action = QAction("Dunkel", self)
        dark_theme_action.triggered.connect(self._set_dark_theme)
        view_menu.addAction(dark_theme_action)

        sync_menu = menubar.addMenu("&Sync")

        export_singers_action = QAction("Sänger exportieren (JSON)...", self)
        export_singers_action.triggered.connect(self._export_singers_json)
        sync_menu.addAction(export_singers_action)

        export_events_action = QAction("Termine exportieren (JSON)...", self)
        export_events_action.triggered.connect(self._export_events_json)
        sync_menu.addAction(export_events_action)

        export_availability_action = QAction(
            "Verfügbarkeit exportieren (JSON)...", self
        )
        export_availability_action.triggered.connect(self._export_availability_json)
        sync_menu.addAction(export_availability_action)

        sync_menu.addSeparator()

        export_all_action = QAction("Alle Sync-Dateien exportieren", self)
        export_all_action.triggered.connect(self._export_all_sync)
        sync_menu.addAction(export_all_action)

        export_csv_action = QAction("CSV-Fallback exportieren...", self)
        export_csv_action.triggered.connect(self._export_singers_csv)
        sync_menu.addAction(export_csv_action)

        projekt_menu = menubar.addMenu("&Projekt")

        new_projekt_action = QAction("Neu...", self)
        new_projekt_action.triggered.connect(self._new_projekt)
        projekt_menu.addAction(new_projekt_action)

        save_projekt_action = QAction("Speichern", self)
        save_projekt_action.triggered.connect(self._save_projekt)
        projekt_menu.addAction(save_projekt_action)

        open_projekt_action = QAction("Öffnen...", self)
        open_projekt_action.triggered.connect(self._open_projekt)
        projekt_menu.addAction(open_projekt_action)

        konfig_menu = menubar.addMenu("Konfiguration")

        konfig_action = QAction("Einstellungen...", self)
        konfig_action.triggered.connect(self._show_config)
        konfig_menu.addAction(konfig_action)

        marketing_menu = menubar.addMenu("Marketing")

        selbstdarstellung_action = QAction("Selbstdarstellung...", self)
        selbstdarstellung_action.triggered.connect(self._show_selbstdarstellung)
        marketing_menu.addAction(selbstdarstellung_action)

        choraufstellung_menu = menubar.addMenu("Choraufstellung")

        open_action = QAction("In Choraufstellung öffnen...", self)
        open_action.triggered.connect(self._open_choraufstellung)
        choraufstellung_menu.addAction(open_action)

        termin_menu = menubar.addMenu("&Termine")

        new_event_action = QAction("Neuer Termin...", self)
        new_event_action.triggered.connect(self._new_event)
        termin_menu.addAction(new_event_action)

        manage_availability_action = QAction("Verfügbarkeit verwalten...", self)
        manage_availability_action.triggered.connect(self._manage_availability)
        termin_menu.addAction(manage_availability_action)

        termin_menu.addSeparator()

        list_events_action = QAction("Terminliste anzeigen...", self)
        list_events_action.triggered.connect(self._list_events)
        termin_menu.addAction(list_events_action)

        extras_menu = menubar.addMenu("Extras")

        export_data_action = QAction("Daten exportieren...", self)
        export_data_action.triggered.connect(self._export_data)
        extras_menu.addAction(export_data_action)

        import_data_action = QAction("Daten importieren...", self)
        import_data_action.triggered.connect(self._import_data)
        extras_menu.addAction(import_data_action)

        hilfe_menu = menubar.addMenu("&Hilfe")

        about_action = QAction("Über", self)
        about_action.triggered.connect(self._show_about)
        hilfe_menu.addAction(about_action)

    def _create_tool_bar(self):
        """Create toolbar."""
        toolbar = QToolBar()
        self.addToolBar(toolbar)

    def _create_central_widget(self):
        """Create central widget with sidebar navigation."""
        central = QWidget()
        self.setCentralWidget(central)

        # Horizontal splitter: Sidebar links, Content rechts
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout = QHBoxLayout(central)
        layout.addWidget(splitter)
        layout.setContentsMargins(0, 0, 0, 0)

        # Sidebar (linke Navigationsspalte)
        sidebar = QWidget()
        sidebar.setMinimumWidth(140)
        sidebar.setMaximumWidth(140)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(5, 10, 5, 10)
        sidebar_layout.setSpacing(5)

        # Navigation buttons (OBEN zuerst) - mit Icons
        self.nav_projects = QPushButton("📁 Projekte")
        self.nav_projects.setCheckable(True)
        self.nav_projects.setChecked(True)
        self.nav_projects.clicked.connect(lambda: self._switch_view(0))
        sidebar_layout.addWidget(self.nav_projects)

        self.nav_singers = QPushButton("👤 Sänger")
        self.nav_singers.setCheckable(True)
        self.nav_singers.clicked.connect(lambda: self._switch_view(1))
        sidebar_layout.addWidget(self.nav_singers)

        self.nav_besetzung = QPushButton("👥 Besetzung")
        self.nav_besetzung.setCheckable(True)
        self.nav_besetzung.clicked.connect(lambda: self._switch_view(2))
        sidebar_layout.addWidget(self.nav_besetzung)

        self.nav_events = QPushButton("📅 Termine")
        self.nav_events.setCheckable(True)
        self.nav_events.clicked.connect(lambda: self._switch_view(3))
        sidebar_layout.addWidget(self.nav_events)

        self.nav_formations = QPushButton("🎵 Aufstellung")
        self.nav_formations.setCheckable(True)
        self.nav_formations.clicked.connect(lambda: self._switch_view(4))
        sidebar_layout.addWidget(self.nav_formations)

        sidebar_layout.addStretch()

        splitter.addWidget(sidebar)

        # Content-Bereich (rechts) - mit horizontaler Context Toolbar oben
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Context toolbar (horizontal oberhalb des Content)
        self.context_toolbar = QToolBar("Aktionen")
        self.context_toolbar.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.context_toolbar.setMovable(False)
        self.context_toolbar.setIconSize(QSize(16, 16))
        content_layout.addWidget(self.context_toolbar)

        self.current_event = None

        from .views.projects_tab import ProjectsTab

        self.projects_tab = ProjectsTab(self.db)
        self.projects_tab.current_project_changed.connect(self._on_project_changed)

        from .views.singers_tab import SingersTab

        self.singers_tab = SingersTab(self.db)

        from .views.events_tab import EventsTab

        self.events_tab = EventsTab(self.db)
        self.events_tab.event_selected.connect(self._on_event_selected)

        from .views.choraufstellung_tab import ChorAufstellungTab

        self.choraufstellung_tab = ChorAufstellungTab(self.db)

        from .views.besetzung_tab import BesetzungTab
        self.besetzung_tab = BesetzungTab(self.db)
        self.besetzung_tab.active_besetzung_changed.connect(self._on_besetzung_changed)

        # Stacked widget für Content
        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(self.projects_tab)
        self.content_stack.addWidget(self.singers_tab)
        self.content_stack.addWidget(self.besetzung_tab)
        self.content_stack.addWidget(self.events_tab)
        self.content_stack.addWidget(self.choraufstellung_tab)

        content_layout.addWidget(self.content_stack)

        splitter.addWidget(content_area)
        splitter.setStretchFactor(1, 1)

        # Initialize context toolbar for current view (projects)
        self._update_context_toolbar(0, None)

        # Connect selection signals
        self.projects_tab.table.selectionModel().selectionChanged.connect(
            lambda: self._emit_selection(0)
        )
        self.singers_tab.table.selectionModel().selectionChanged.connect(
            lambda: self._emit_selection(1)
        )
        self.besetzung_tab.table.selectionModel().selectionChanged.connect(
            lambda: self._emit_selection(2)
        )
        self.events_tab.table.selectionModel().selectionChanged.connect(
            lambda: self._emit_selection(3)
        )
        self.choraufstellung_tab.table.selectionModel().selectionChanged.connect(
            lambda: self._emit_selection(4)
        )

    def _switch_view(self, index):
        """Switch content view."""
        self.content_stack.setCurrentIndex(index)
        self.nav_projects.setChecked(index == 0)
        self.nav_singers.setChecked(index == 1)
        self.nav_besetzung.setChecked(index == 2)
        self.nav_events.setChecked(index == 3)
        self.nav_formations.setChecked(index == 4)
        self._emit_selection(index)

    def _emit_selection(self, tab_index):
        """Emit selection signal with current selected item for given tab.

        Args:
            tab_index: Index of tab (0-3)
        """
        selection = None
        if tab_index == 0 and self.projects_tab.current_project:
            selection = self.projects_tab.current_project
        elif tab_index == 1:
            row = self.singers_tab.table.currentRow()
            if row >= 0:
                item = self.singers_tab.table.item(row, 0)
                singer_id = item.data(Qt.ItemDataRole.UserRole)
                selection = (
                    self.singers_tab.singer_repo.get_by_id(singer_id)
                    if singer_id
                    else None
                )
        elif tab_index == 2:  # Besetzung
            row = self.besetzung_tab.table.currentRow()
            if row >= 0:
                besetzungen = self.besetzung_tab.besetzung_repo.get_all()
                selection = besetzungen[row] if row < len(besetzungen) else None
        elif tab_index == 3:  # Events
            row = self.events_tab.table.currentRow()
            if row >= 0:
                item = self.events_tab.table.item(row, 0)
                event_id = item.data(Qt.ItemDataRole.UserRole)
                selection = (
                    self.events_tab.event_repo.get_by_id(event_id)
                    if event_id
                    else None
                )
        elif tab_index == 4:  # Aufstellung
            row = self.choraufstellung_tab.table.currentRow()
            if row >= 0:
                filename = self.choraufstellung_tab.table.item(row, 0).text()
                selection = filename

        self._on_selection_changed(tab_index, selection)

    def _on_selection_changed(self, tab_index, selection):
        """Handle selection change from any tab to update context toolbar.

        Args:
            tab_index: Index of the tab (int)
            selection: Selected object (Project/Event/Singer) or None
        """
        self._update_context_toolbar(tab_index, selection)

    def _update_context_toolbar(self, tab_index, selection):
        """Update toolbar actions based on active tab and selection.

        Args:
            tab_index: Index of active tab (0=Projects, 1=Singers, 2=Events, 3=Aufstellung)
            selection: Selected item object (Project/Event/Singer/formation file) or None
        """
        if not hasattr(self, "context_toolbar"):
            return
        self.context_toolbar.clear()

        if tab_index == 0:  # Projects
            add_action = QAction("➕ Hinzufügen", self)
            add_action.triggered.connect(self._new_projekt)
            self.context_toolbar.addAction(add_action)

            refresh_action = QAction("🔄 Aktualisieren", self)
            refresh_action.triggered.connect(self._refresh_tabs)
            self.context_toolbar.addAction(refresh_action)

            if selection:
                set_active_action = QAction("Als aktives Projekt setzen", self)
                set_active_action.triggered.connect(self.projects_tab._set_active)
                self.context_toolbar.addAction(set_active_action)

                edit_action = QAction("Bearbeiten", self)
                edit_action.triggered.connect(self._edit_project)
                self.context_toolbar.addAction(edit_action)

                dup_action = QAction("Duplizieren", self)
                dup_action.triggered.connect(self._duplicate_project)
                self.context_toolbar.addAction(dup_action)

                delete_action = QAction("Löschen", self)
                delete_action.triggered.connect(self._delete_project)
                self.context_toolbar.addAction(delete_action)

        elif tab_index == 1:  # Singers
            add_action = QAction("➕ Hinzufügen", self)
            add_action.triggered.connect(self._add_singer)
            self.context_toolbar.addAction(add_action)

            refresh_action = QAction("🔄 Aktualisieren", self)
            refresh_action.triggered.connect(self._refresh_tabs)
            self.context_toolbar.addAction(refresh_action)

            if selection:
                edit_action = QAction("Bearbeiten", self)
                edit_action.triggered.connect(self._edit_singer)
                self.context_toolbar.addAction(edit_action)

                delete_action = QAction("Löschen", self)
                delete_action.triggered.connect(self._delete_singer)
                self.context_toolbar.addAction(delete_action)

        elif tab_index == 2:  # Besetzung
            add_action = QAction("➕ Neue Besetzung", self)
            add_action.triggered.connect(self.besetzung_tab._new_besetzung)
            self.context_toolbar.addAction(add_action)

            refresh_action = QAction("🔄 Aktualisieren", self)
            refresh_action.triggered.connect(self._refresh_tabs)
            self.context_toolbar.addAction(refresh_action)

            if selection:
                edit_action = QAction("✏️ Bearbeiten", self)
                edit_action.triggered.connect(self.besetzung_tab._edit_besetzung)
                self.context_toolbar.addAction(edit_action)

                active_action = QAction("⭐ Als aktiv setzen", self)
                active_action.triggered.connect(self.besetzung_tab._set_active_besetzung)
                self.context_toolbar.addAction(active_action)

                delete_action = QAction("🗑️ Löschen", self)
                delete_action.triggered.connect(self.besetzung_tab._delete_besetzung)
                self.context_toolbar.addAction(delete_action)

        elif tab_index == 3:  # Events
            add_action = QAction("➕ Neuer Termin", self)
            add_action.triggered.connect(self._new_event)
            self.context_toolbar.addAction(add_action)

            refresh_action = QAction("🔄 Aktualisieren", self)
            refresh_action.triggered.connect(self._refresh_tabs)
            self.context_toolbar.addAction(refresh_action)

            if selection:
                # Primary actions
                avail_action = QAction("Verfügbarkeit erfassen", self)
                avail_action.triggered.connect(self._manage_availability)
                self.context_toolbar.addAction(avail_action)

                # Aufstellung: prüfen, ob bereits Datei existiert
                formation_exists = False
                if hasattr(self, "choraufstellung_tab"):
                    formation_exists = self.choraufstellung_tab.has_formation_for_event(
                        selection
                    )

                if formation_exists:
                    open_action = QAction("Aufstellung bearbeiten", self)
                else:
                    open_action = QAction("Aufstellung öffnen", self)
                open_action.triggered.connect(
                    lambda checked=False, ev=selection: (
                        self._open_choraufstellung_for_event(ev)
                    )
                )
                self.context_toolbar.addAction(open_action)

                set_active_action = QAction("Als aktiven Termin setzen", self)
                set_active_action.triggered.connect(self.events_tab._set_selected_event)
                self.context_toolbar.addAction(set_active_action)

                self.context_toolbar.addSeparator()

                edit_action = QAction("Bearbeiten", self)
                edit_action.triggered.connect(self._edit_event)
                self.context_toolbar.addAction(edit_action)

                dup_action = QAction("Duplizieren", self)
                dup_action.triggered.connect(self._duplicate_event)
                self.context_toolbar.addAction(dup_action)

                delete_action = QAction("Löschen", self)
                delete_action.triggered.connect(self._delete_event)
                self.context_toolbar.addAction(delete_action)

        elif tab_index == 4:  # Aufstellung
            new_action = QAction("Neue Aufstellung", self)
            new_action.triggered.connect(self._new_formation)
            self.context_toolbar.addAction(new_action)

            if selection:
                edit_action = QAction("Bearbeiten", self)
                edit_action.triggered.connect(self._edit_formation)
                self.context_toolbar.addAction(edit_action)

                dup_action = QAction("Duplizieren", self)
                dup_action.triggered.connect(self._duplicate_formation)
                self.context_toolbar.addAction(dup_action)

                delete_action = QAction("Löschen", self)
                delete_action.triggered.connect(self._delete_formation)
                self.context_toolbar.addAction(delete_action)

    def _on_selection_changed(self, tab_index, selection):
        """Handle selection change from any tab to update context toolbar.

        Args:
            tab_index: Index of the tab (int)
            selection: Selected object (Project/Event/Singer) or None
        """
        self._update_context_toolbar(tab_index, selection)

    def _update_info_labels(self):
        """Update the info labels in the info bar."""
        # Update project info label
        if self.projects_tab.current_project:
            project = self.projects_tab.current_project
            self.project_info_label.setText(f"{project.name}")
        else:
            self.project_info_label.setText("Keines")

        # Update event info label
        if self.current_event:
            event = self.current_event
            self.event_info_label.setText(f"{event.name} ({event.date[:10]})")
        else:
            self.event_info_label.setText("Keiner")

    def _on_project_changed(self):
        """Handle project selection change."""
        project = self.projects_tab.current_project
        self._update_info_labels()
        self.current_project = project
        if project:
            self.project_info_label.setText(
                f"<b>Ausgewähltes Projekt:</b> {project.name}"
            )
            # Style is handled by QSS for both themes
            self.project_info_label.setVisible(True)
        else:
            self.project_info_label.setVisible(False)

        if hasattr(self, "singers_tab"):
            self.singers_tab.set_project_filter(project)
        if hasattr(self, "events_tab"):
            self.events_tab.set_project_filter(project)
        if hasattr(self, "besetzung_tab"):
            self.besetzung_tab.set_project(project)
        if hasattr(self, "choraufstellung_tab"):
            self.choraufstellung_tab.set_project(project)

        self._refresh_tabs()

    def _on_event_selected(self, event):
        """Handle event selection."""
        self.current_event = event
        self._update_info_labels()
        if hasattr(self, "choraufstellung_tab"):
            self.choraufstellung_tab.set_event(event)

        if event:
            self.event_info_label.setText(
                f"<b>Ausgewählter Termin:</b> {event.name} am {event.date[:10]}"
            )
            self.event_info_label.setVisible(True)
        else:
            self.event_info_label.setVisible(False)

    def _on_besetzung_changed(self, besetzung):
        """Handle active besetzung change."""
        if besetzung:
            self.besetzung_info_label.setText(
                f"<b>{besetzung.name}</b>"
            )
            self.besetzung_info_label.setVisible(True)
        else:
            self.besetzung_info_label.setText("Keine")
            self.besetzung_info_label.setVisible(False)

    def _on_tab_changed(self, index):
        if index == 2:
            self.events_tab._load_events()
        elif index == 3:
            QTimer.singleShot(0, self.choraufstellung_tab._load_formations)
        self._emit_selection(index)

    def _create_status_bar(self):
        """Create status bar."""
        self.statusBar().showMessage("Bereit")

    def _refresh_tabs(self):
        """Refresh all tabs."""
        self.singers_tab._load_singers()
        self.events_tab._load_events()

    def _on_search_text_changed(self, text):
        """Handle search text change."""
        self.singers_tab._load_singers()

    def _on_filter_changed(self, index):
        """Handle voice group filter change."""
        self.singers_tab._load_singers()

    def _add_singer(self):
        """Add new singer."""
        self.singers_tab._add_singer()

    def _edit_singer(self):
        """Edit selected singer."""
        self.singers_tab._edit_singer()

    def _delete_singer(self):
        self.singers_tab._delete_singer()

    def _edit_event(self):
        self.events_tab._edit_event()

    def _delete_event(self):
        self.events_tab._delete_event()

    def _duplicate_event(self):
        self.events_tab._duplicate_event()

    def _manage_availability(self):
        self.events_tab._manage_availability()

    def _open_choraufstellung_for_event(self, event):
        self.content_stack.setCurrentIndex(4)
        QTimer.singleShot(100, lambda: self.choraufstellung_tab.load_for_event(event))

    def _edit_formation(self):
        self.choraufstellung_tab._edit_formation()

    def _duplicate_formation(self):
        self.choraufstellung_tab._duplicate_formation()

    def _delete_formation(self):
        self.choraufstellung_tab._delete_formation()

    def _new_formation(self):
        self.choraufstellung_tab._load_from_chormanager()

    def _undo(self):
        """Undo last action."""
        if self.history.can_undo():
            self.history.undo()
            self._refresh_tabs()
            self.statusBar().showMessage("Rückgängig gemacht")

    def _redo(self):
        """Redo last undone action."""
        if self.history.can_redo():
            self.history.redo()
            self._refresh_tabs()
            self.statusBar().showMessage("Wiederholt")

    def _export_csv(self):
        """Export to CSV."""
        from PyQt6.QtWidgets import QFileDialog

        filename, _ = QFileDialog.getSaveFileName(
            self, "Als CSV exportieren", "", "CSV Dateien (*.csv)"
        )

        if filename:
            singers = self.singer_repo.get_all()
            fields = self.singers_tab.visible_fields

            import csv

            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[field["name"] for field in fields])
                writer.writeheader()

                for singer in singers:
                    row = {}
                    for field in fields:
                        name = field["name"]
                        value = getattr(singer, name, "")
                        row[name] = value if value else ""
                    writer.writerow(row)

            self.statusBar().showMessage(f"Exportiert nach {filename}")

    def _export_pdf(self):
        """Export to PDF."""
        from PyQt6.QtWidgets import QFileDialog
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate,
            Table,
            TableStyle,
            Paragraph,
            Spacer,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm

        filename, _ = QFileDialog.getSaveFileName(
            self, "Als PDF exportieren", "", "PDF Dateien (*.pdf)"
        )

        if not filename:
            return

        singers = self.singer_repo.get_all()

        doc = SimpleDocTemplate(filename, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "CustomTitle", parent=styles["Heading1"], fontSize=18, spaceAfter=20
        )

        elements.append(Paragraph("Chor-Teilnehmerliste", title_style))
        elements.append(Spacer(1, 0.5 * cm))

        data = [["Name", "Stimmgruppe", "E-Mail", "Telefon"]]
        for singer in singers:
            data.append(
                [
                    singer.full_name or "",
                    singer.voice_group or "",
                    singer.email or "",
                    singer.phone or "",
                ]
            )

        table = Table(data, colWidths=[5 * cm, 3 * cm, 4 * cm, 3 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                ]
            )
        )

        elements.append(table)

        doc.build(elements)

        self.statusBar().showMessage(f"Exportiert nach {filename}")

    def _export_libreoffice(self):
        """Export to LibreOffice format."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        import subprocess
        import tempfile
        import os

        singers = self.singer_repo.get_all()

        reply = QMessageBox.question(
            self,
            "LibreOffice Export",
            "Möchten Sie als Writer-Dokument (doc) oder Calc-Dokument (xls) exportieren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            output_format = "doc"
            ext = ".doc"
        else:
            output_format = "xls"
            ext = ".xls"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            import csv

            writer = csv.writer(f)
            writer.writerow(["Name", "Stimmgruppe", "E-Mail", "Telefon", "Adresse"])
            for singer in singers:
                writer.writerow(
                    [
                        singer.full_name or "",
                        singer.voice_group or "",
                        singer.email or "",
                        singer.phone or "",
                        singer.address or "",
                    ]
                )
            temp_csv = f.name

        filename, _ = QFileDialog.getSaveFileName(
            self, "Als LibreOffice exportieren", "", f"LibreOffice Dateien (*{ext})"
        )

        if not filename:
            return

        out_dir = os.path.dirname(filename)
        result = subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to",
                output_format,
                "--outdir",
                out_dir,
                temp_csv,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            base_name = os.path.splitext(os.path.basename(temp_csv))[0]
            expected_output = os.path.join(out_dir, base_name + ext)
            if expected_output != filename and os.path.exists(expected_output):
                os.rename(expected_output, filename)
            self.statusBar().showMessage(f"Exportiert nach {filename}")
        else:
            QMessageBox.warning(
                self, "Fehler", f"LibreOffice Fehler:\n{result.stderr}"
            )

        if os.path.exists(temp_csv):
            os.unlink(temp_csv)

    def _set_light_theme(self):
        """Set professional light theme."""
        light_style = """
        /* ===== LIGHT THEME ===== */

        /* Main application colors */
        QMainWindow, QWidget {
            background-color: #f8f9fa;
            color: #212529;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        /* Table styling */
        QTableWidget {
            background-color: #ffffff;
            alternate-background-color: #f8f9fa;
            gridline-color: #dee2e6;
            border: 1px solid #dee2e6;
            border-radius: 4px;
        }

        QTableWidget::item {
            padding: 12px 8px;
            border-bottom: 1px solid #e9ecef;
        }

        QTableWidget::item:selected {
            background-color: #e3f2fd;
            color: #1976d2;
        }

        QHeaderView::section {
            padding: 10px;
            background-color: #f1f3f4;
            border: none;
            border-bottom: 2px solid #1976d2;
            font-weight: bold;
        }

        QHeaderView::section {
            background-color: #f8f9fa;
            color: #495057;
            padding: 12px 8px;
            border: 1px solid #dee2e6;
            border-left: none;
            font-weight: 600;
            font-size: 13px;
        }

        /* Button styling */
        QPushButton {
            background-color: #ffffff;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 8px 16px;
            color: #495057;
            font-weight: 500;
        }

        QPushButton:hover {
            background-color: #e9ecef;
            border-color: #adb5bd;
        }

        QPushButton:pressed {
            background-color: #dee2e6;
        }

        /* Menu styling */
        QMenuBar {
            background-color: #ffffff;
            border-bottom: 1px solid #dee2e6;
            color: #495057;
        }

        QMenuBar::item {
            padding: 8px 12px;
            background-color: transparent;
        }

        QMenuBar::item:selected {
            background-color: #e9ecef;
        }

        QMenu {
            background-color: #ffffff;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            color: #495057;
        }

        QMenu::item {
            padding: 8px 20px;
            border-radius: 2px;
        }

        QMenu::item:selected {
            background-color: #e3f2fd;
            color: #1976d2;
        }

        /* Status bar */
        QStatusBar {
            background-color: #f8f9fa;
            border-top: 1px solid #dee2e6;
            color: #6c757d;
        }

        /* Tool bar */
        QToolBar {
            background-color: #f8f9fa;
            border: none;
            border-bottom: 1px solid #dee2e6;
        }

        /* Info labels - custom colors maintained */
        QLabel#projectInfoLabel {
            background-color: #4a90d9;
            color: #ffffff;
            padding: 10px 15px;
            font-weight: bold;
            font-size: 13px;
            border-radius: 4px;
        }

        QLabel#eventInfoLabel {
            background-color: #e67e22;
            color: #ffffff;
            padding: 10px 15px;
            font-weight: bold;
            font-size: 13px;
            border-radius: 4px;
        }

        /* Form controls */
        QLineEdit, QComboBox, QTextEdit {
            border: 1px solid #ced4da;
            border-radius: 4px;
            padding: 8px 12px;
            background-color: #ffffff;
            color: #495057;
        }

        QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
            border-color: #4a90d9;
            outline: none;
        }

        /* Scroll bars */
        QScrollBar:vertical {
            background-color: #f8f9fa;
            width: 12px;
            border-radius: 6px;
        }

        QScrollBar::handle:vertical {
            background-color: #adb5bd;
            border-radius: 6px;
            min-height: 20px;
        }

        QScrollBar::handle:vertical:hover {
            background-color: #6c757d;
        }

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
        }
        """
        self.setStyleSheet(light_style)
        set_theme("light")
        self.statusBar().showMessage("Helles Theme aktiviert")

    def _set_dark_theme(self):
        """Set professional dark theme."""
        dark_style = """
        /* ===== DARK THEME ===== */
        
        /* Info bar - augenfreundlich im Dark Mode */
        QWidget#infoBarWidget {
            background-color: #1e2832;
            border-bottom: 2px solid #4a90d9;
            padding: 8px;
        }
        QLabel {
            color: #e0e0e0;
            font-weight: bold;
            padding: 4px 12px;
            border-radius: 4px;
        }
        QLabel#projectInfoLabel {
            background-color: #1565c0;
            color: white;
        }
        QLabel#eventInfoLabel {
            background-color: #e65100;
            color: white;
        }
        QLabel#pageTitle {
            color: #ffffff;
        }

        /* Main application colors */
        QMainWindow, QWidget {
            background-color: #1a1a1a;
            color: #e0e0e0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        /* Table styling */
        QTableWidget {
            background-color: #2d2d2d;
            alternate-background-color: #262626;
            gridline-color: #404040;
            border: 1px solid #404040;
            border-radius: 4px;
        }

        QTableWidget::item {
            padding: 12px 8px;
            border-bottom: 1px solid #333333;
            color: #e0e0e0;
        }

        QTableWidget::item:selected {
            background-color: #1e3a5f;
            color: #64b5f6;
        }

        QHeaderView::section {
            background-color: #333333;
            color: #ffffff;
            padding: 12px 8px;
            border: 1px solid #404040;
            border-left: none;
            font-weight: 600;
            font-size: 13px;
        }

        /* Button styling */
        QPushButton {
            background-color: #333333;
            border: 1px solid #555555;
            border-radius: 6px;
            padding: 8px 16px;
            color: #e0e0e0;
            font-weight: 500;
        }

        QPushButton:hover {
            background-color: #404040;
            border-color: #666666;
        }

        QPushButton:pressed {
            background-color: #262626;
        }

        /* Checkbox styling for dark theme */
        QCheckBox {
            background-color: transparent;
            color: #e0e0e0;
            padding: 4px;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 1px solid #666666;
            border-radius: 3px;
            background-color: #2d2d2d;
        }
        QCheckBox::indicator:checked {
            background-color: #1565c0;
            border-color: #1976d2;
        }
        QCheckBox::indicator:indeterminate {
            background-color: #4a4a4a;
        }

        /* Menu styling */
        QMenuBar {
            background-color: #2d2d2d;
            border-bottom: 1px solid #404040;
            color: #e0e0e0;
        }

        QMenuBar::item {
            padding: 8px 12px;
            background-color: transparent;
        }

        QMenuBar::item:selected {
            background-color: #404040;
        }

        QMenu {
            background-color: #333333;
            border: 1px solid #555555;
            border-radius: 4px;
            color: #e0e0e0;
        }

        QMenu::item {
            padding: 8px 20px;
            border-radius: 2px;
        }

        QMenu::item:selected {
            background-color: #1e3a5f;
            color: #64b5f6;
        }

        /* Status bar */
        QStatusBar {
            background-color: #1a1a1a;
            border-top: 1px solid #404040;
            color: #b0b0b0;
        }

        /* Tool bar */
        QToolBar {
            background-color: #2d2d2d;
            border: none;
            border-bottom: 1px solid #404040;
            color: #e0e0e0;
        }

        /* Info labels - custom colors maintained */
        QLabel#projectInfoLabel {
            background-color: #4a90d9;
            color: #ffffff;
            padding: 10px 15px;
            font-weight: bold;
            font-size: 13px;
            border-radius: 4px;
        }

        QLabel#eventInfoLabel {
            background-color: #e67e22;
            color: #ffffff;
            padding: 10px 15px;
            font-weight: bold;
            font-size: 13px;
            border-radius: 4px;
        }

        /* Form controls */
        QLineEdit, QComboBox, QTextEdit {
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 8px 12px;
            background-color: #333333;
            color: #e0e0e0;
        }

        QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
            border-color: #4a90d9;
            outline: none;
        }

        /* Scroll bars */
        QScrollBar:vertical {
            background-color: #1a1a1a;
            width: 12px;
            border-radius: 6px;
        }

        QScrollBar::handle:vertical {
            background-color: #555555;
            border-radius: 6px;
            min-height: 20px;
        }

        QScrollBar::handle:vertical:hover {
            background-color: #666666;
        }

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
        }

        /* Additional dark theme refinements */
        QSplitter::handle {
            background-color: #404040;
        }

        QSplitter::handle:hover {
            background-color: #555555;
        }
        """
        self.setStyleSheet(dark_style)
        set_theme("dark")
        self.statusBar().showMessage("Dunkles Theme aktiviert")

    def _new_event(self):
        """Create a new event."""
        from .dialogs import EventDialog
        from ..domain.repository import EventRepository

        dialog = EventDialog(parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()

            if not data.get("name"):
                QMessageBox.warning(self, "Fehler", "Name ist erforderlich")
                return

            repo = EventRepository(self.db)
            repo.create(**data)

            self.statusBar().showMessage("Termin erstellt")

    def _manage_availability(self):
        """Manage availability for events."""
        from .dialogs import EventListDialog

        dialog = EventListDialog(self.db, parent=self)
        dialog.exec()

    def _list_events(self):
        """List all events."""
        from .dialogs import EventDialog
        from ..domain.repository import EventRepository
        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QMessageBox

        repo = EventRepository(self.db)
        events = repo.get_all()

        if not events:
            QMessageBox.information(self, "Termine", "Keine Termine vorhanden")
            return

        # Show events in a simple dialog
        event_text = "Vorhandene Termine:\n\n"
        for event in events:
            event_text += f"- {event.name} ({event.date}) [{event.event_type}]\n"

        QMessageBox.information(self, "Termine", event_text)

    def _export_singers_json(self):
        """Export singers as JSON for choraufstellung sync."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from ..export.sync import export_singers_json

        default_path = (
            self.db_path.replace(".db", "_singers.json")
            if self.db_path
            else "singers.json"
        )
        filename, _ = QFileDialog.getSaveFileName(
            self, "Sänger exportieren", default_path, "JSON Dateien (*.json)"
        )

        if filename:
            from pathlib import Path

            output_path = Path(filename)
            try:
                export_singers_json(self.db, output_path)
                self.statusBar().showMessage(f"Sänger exportiert nach {filename}")
                QMessageBox.information(self, "Export", f"Exportiert nach:\n{filename}")
            except Exception as e:
                QMessageBox.warning(self, "Fehler", f"Export fehlgeschlagen:\n{str(e)}")

    def _export_events_json(self):
        """Export events as JSON for choraufstellung sync."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from ..export.sync import export_events_json

        default_path = (
            self.db_path.replace(".db", "_termine.json")
            if self.db_path
            else "termine.json"
        )
        filename, _ = QFileDialog.getSaveFileName(
            self, "Termine exportieren", default_path, "JSON Dateien (*.json)"
        )

        if filename:
            from pathlib import Path

            output_path = Path(filename)
            try:
                export_events_json(self.db, output_path)
                self.statusBar().showMessage(f"Termine exportiert nach {filename}")
                QMessageBox.information(self, "Export", f"Exportiert nach:\n{filename}")
            except Exception as e:
                QMessageBox.warning(self, "Fehler", f"Export fehlgeschlagen:\n{str(e)}")

    def _export_availability_json(self):
        """Export availability matrix as JSON."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from ..export.sync import export_availability_json

        default_path = (
            self.db_path.replace(".db", "_verfuegbarkeit.json")
            if self.db_path
            else "verfuegbarkeit.json"
        )
        filename, _ = QFileDialog.getSaveFileName(
            self, "Verfügbarkeit exportieren", default_path, "JSON Dateien (*.json)"
        )

        if filename:
            from pathlib import Path

            output_path = Path(filename)
            try:
                export_availability_json(self.db, output_path)
                self.statusBar().showMessage(
                    f"Verfügbarkeit exportiert nach {filename}"
                )
                QMessageBox.information(self, "Export", f"Exportiert nach:\n{filename}")
            except Exception as e:
                QMessageBox.warning(self, "Fehler", f"Export fehlgeschlagen:\n{str(e)}")

    def _export_singers_csv(self):
        """Export singers as CSV fallback for choraufstellung."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from ..export.sync import export_singers_csv

        default_path = (
            self.db_path.replace(".db", "_singers.csv")
            if self.db_path
            else "singers.csv"
        )
        filename, _ = QFileDialog.getSaveFileName(
            self, "CSV exportieren", default_path, "CSV Dateien (*.csv)"
        )

        if filename:
            from pathlib import Path

            output_path = Path(filename)
            try:
                export_singers_csv(self.db, output_path)
                self.statusBar().showMessage(f"CSV exportiert nach {filename}")
                QMessageBox.information(self, "Export", f"Exportiert nach:\n{filename}")
            except Exception as e:
                QMessageBox.warning(self, "Fehler", f"Export fehlgeschlagen:\n{str(e)}")

    def _export_all_sync(self):
        """Export all sync files to default location."""
        from PyQt6.QtWidgets import QMessageBox
        from ..export.sync import export_all_sync

        try:
            result = export_all_sync(self.db)

            output_text = "Exportierte Dateien:\n\n"
            for export_type, path in result.items():
                output_text += f"{export_type}: {path}\n"

            self.statusBar().showMessage("Alle Sync-Dateien exportiert")
            QMessageBox.information(self, "Sync-Export", output_text)
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Export fehlgeschlagen:\n{str(e)}")

    def _new_projekt(self):
        """Create new project."""
        self.projects_tab._add_project()

    def _edit_project(self):
        """Edit selected project."""
        self.projects_tab._edit_project()

    def _delete_project(self):
        """Delete selected project."""
        self.projects_tab._delete_project()

    def _duplicate_project(self):
        """Duplicate selected project."""
        self.projects_tab._duplicate_project()

    def _save_projekt(self):
        """Save current project."""
        from PyQt6.QtWidgets import QMessageBox

        project = self.projects_tab.current_project
        if project:
            QMessageBox.information(
                self, "Speichern", f"Projekt '{project.name}' ist bereits gespeichert."
            )
        else:
            QMessageBox.warning(self, "Speichern", "Kein Projekt ausgewählt.")

    def _open_projekt(self):
        """Open existing project."""
        self.tabs.setCurrentIndex(0)
        QMessageBox.information(
            self, "Öffnen", "Bitte wählen Sie ein Projekt aus der Liste aus."
        )

    def _show_config(self):
        """Show configuration dialog."""
        from .dialogs import ConfigDialog

        dialog = ConfigDialog(self.db, self)
        dialog.exec()

    def _show_about(self):
        """Show about dialog."""
        from PyQt6.QtWidgets import QMessageBox
        import subprocess

        # Get git commit hash for version
        try:
            git_hash = subprocess.check_output(
                ["git", "describe", "--tags", "--abbrev=7", "--always", "--dirty"],
                cwd="/media/data/coding/chormanager",
                text=True,
            ).strip()
        except Exception:
            git_hash = "dev"

        QMessageBox.about(
            self,
            "Über ChorManager",
            f"<h3>ChorManager</h3>"
            f"<p>Desktop-Anwendung zur Verwaltung eines Chors</p>"
            f"<p>Version: {git_hash}</p>",
        )

    def _show_selbstdarstellung(self):
        """Show selbstdarstellung dialog."""
        from .dialogs import SelbstdarstellungDialog

        dialog = SelbstdarstellungDialog(self.db, self)
        dialog.exec()

    def _open_choraufstellung(self):
        """Open Choraufstellung app with current project/event data."""
        self._open_choraufstellung_file(None)

    def _open_choraufstellung_file(self, filepath: str = None):
        """Open ChorAufstellung app, optionally with a specific file."""
        import subprocess
        import os
        import sqlite3
        from PyQt6.QtWidgets import (
            QMessageBox,
            QInputDialog,
            QDialog,
            QVBoxLayout,
            QLabel,
            QPushButton,
        )

        choraufstellung_path = (
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            + "/choraufstellung"
        )

        if not os.path.exists(choraufstellung_path):
            QMessageBox.warning(
                self,
                "Fehler",
                f"Choraufstellung nicht gefunden unter:\n choraufstellung_path",
            )
            return

        project = (
            self.projects_tab.current_project if hasattr(self, "projects_tab") else None
        )

        event = None
        event_id = None
        current_row = (
            self.events_tab.table.currentRow() if hasattr(self, "events_tab") else -1
        )

        if current_row >= 0:
            item = self.events_tab.table.item(current_row, 0)
            event_id = item.data(Qt.ItemDataRole.UserRole) if item else None
            if event_id:
                event = self.events_tab.event_repo.get_by_id(event_id)

        vars_to_pass = []
        if project:
            vars_to_pass.append(f"CHOR_PROJECT={project.name}")
        if event:
            vars_to_pass.append(f"CHOR_EVENT_DATE={event.date[:10]}")
            vars_to_pass.append(f"CHOR_EVENT_NAME={event.name}")
            vars_to_pass.append(f"CHOR_EVENT_ID={event.id}")
        if filepath:
            vars_to_pass.append(f"CHOR_FILE={filepath}")

        env = os.environ.copy()
        for var in vars_to_pass:
            key, value = var.split("=", 1)
            env[key] = value

        db_path = self.db_path or os.path.expanduser(
            "~/.local/share/chormanager/chor.db"
        )
        env["CHOR_DB_PATH"] = db_path

        debug_info = f"Übergabe: {', '.join(vars_to_pass)}\n"
        debug_info += f"Project: {project.name if project else 'NIX'}\n"
        debug_info += f"Event: {event.name if event and event.date else 'NIX'}\n"
        debug_info += (
            f"current_row={current_row}, event_id={event_id if event_id else 'NIX'}\n\n"
        )

        if event and os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT s.id, s.full_name, s.short_name, s.voice_group, a.status
                    FROM singers s
                    JOIN availability a ON s.id = a.singer_id
                    WHERE a.event_id = ? AND a.status IN ('yes', 'conditional')
                """,
                    (event.id,),
                )
                rows = cursor.fetchall()

                debug_info += (
                    f"Sänger mit Zusage für {event.date[:10]} ({len(rows)}):\n"
                )
                for row in rows:
                    debug_info += f"  - {row['short_name'] or row['full_name']} ({row['voice_group']}) [{row['status']}]\n"

                cursor.execute(
                    "SELECT date, event_type FROM events ORDER BY date DESC LIMIT 5"
                )
                debug_info += f"\nLetzte Events: {cursor.fetchall()}"

                cursor.execute(
                    "SELECT e.id, e.date, e.name, COUNT(a.id) as cnt FROM events e LEFT JOIN availability a ON a.event_id = e.id GROUP BY e.id ORDER BY e.date DESC LIMIT 10"
                )
                debug_info += f"\nVerfügbarkeit: {cursor.fetchall()}"
                conn.close()
            except Exception as e:
                debug_info += f"Debug-Fehler: {e}"
        else:
            debug_info += "(Keine Verfügbarkeitsdaten)"

        d = QDialog(self)
        d.setWindowTitle("Debug: Choraufstellung starten")
        d.setMinimumSize(400, 300)
        lay = QVBoxLayout(d)
        lay.addWidget(QLabel(debug_info))
        close_btn = QPushButton("Schließen")
        close_btn.clicked.connect(d.accept)

        try:
            main_py = os.path.join(choraufstellung_path, "__main__.py")
            if os.path.exists(main_py):
                subprocess.run(
                    [sys.executable, main_py], cwd=choraufstellung_path, env=env
                )
                self.choraufstellung_tab._load_formations()
            lay.addWidget(close_btn)
            d.exec()
        except Exception as e:
            QMessageBox.warning(
                self,
                "Fehler",
                f"Choraufstellung konnte nicht gestartet werden:\n{str(e)}",
            )

    def _export_data(self):
        """Export all data to ZIP archive."""
        from PyQt6.QtWidgets import QFileDialog
        from datetime import datetime
        from ..export.portability import PortabilityService

        data_dir = self._get_data_dir()
        service = PortabilityService(str(data_dir))

        default_name = f"chormanager_daten_{datetime.now().strftime('%Y-%m-%d')}.zip"

        filename, _ = QFileDialog.getSaveFileName(
            self, "Daten exportieren", default_name, "ZIP Dateien (*.zip)"
        )

        if filename:
            service.export_data(filename)
            QMessageBox.information(
                self, "Export erfolgreich", f"Daten exportiert nach:\n{filename}"
            )
            self.statusBar().showMessage(f"Daten exportiert nach {filename}")

    def _import_data(self):
        """Import data from ZIP archive."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from ..export.portability import PortabilityService

        filename, _ = QFileDialog.getOpenFileName(
            self, "Daten importieren", "", "ZIP Dateien (*.zip)"
        )

        if not filename:
            return

        data_dir = self._get_data_dir()
        service = PortabilityService(str(data_dir))

        reply = QMessageBox.question(
            self,
            "Import bestätigen",
            "Achtung: Existierende Daten werden überschrieben!\n\nFortfahren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            service.import_data(filename, str(data_dir))
            QMessageBox.information(
                self,
                "Import erfolgreich",
                "Daten wurden importiert.\nBitte starten Sie die Anwendung neu.",
            )
            self.statusBar().showMessage("Daten importiert - Neustart erforderlich")

    def _get_data_dir(self):
        """Get current data directory."""
        from pathlib import Path
        from ..config import load_app_config

        config = load_app_config()
        return Path(
            config.get("app", {}).get("data_dir", "~/.local/share/chormanager")
        ).expanduser()

    def closeEvent(self, event):
        """Handle window close."""
        if self.db_path:
            self.backup_service.backup_before_save(self.db_path)

        self.db.close()
        event.accept()


def main():
    """Main entry point."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
