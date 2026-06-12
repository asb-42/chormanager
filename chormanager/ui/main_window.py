"""Main window for ChorManager."""

import sys
import json
from pathlib import Path
from PyQt6.QtCore import QSize

from PyQt6.QtWidgets import (
    QApplication,
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
    QStyle,
    QStackedWidget,
    QDialog,
    QDialogButtonBox,
    QDateEdit,
)
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
from ..config import (
    load_voice_groups,
    load_fields,
    get_theme,
    set_theme,
    get_last_active_project_id,
    set_last_active_project_id,
)
from ..core.export_service import ExportService
from ..core.response_matrix import build_response_matrix
from ..core.response_render_pdf import render_response_matrix_pdf
from ..core.response_render_odt import render_response_matrix_odt
from .export_format_dialog import ExportFormatDialog, SUPPORTED_FORMATS
from .export_dialog import ExportDialog
from PyQt6.QtWidgets import QFileDialog
from .theme_manager import ThemeMixin
from .tab_router import TabRouterMixin
from .choraufstellung_launcher import ChorAufstellungLauncherMixin


# --- M-1 step 5: ``get_icon`` was moved to its own module to avoid a
# circular import (tab_router -> main_window). Re-exported here for
# backward compatibility with any code that imports it from
# ``chormanager.ui.main_window``.
from .icons import get_icon  # noqa: E402, F401


# --- M-1 step 1: SingerDialog was moved to its own module.
# Re-exported here for backward compatibility with any code that
# imports ``chormanager.ui.main_window.SingerDialog``.
from .forms.singer_dialog import SingerDialog  # noqa: E402, F401


# --- M-1 step 3: ``refresh_tab_repositories`` was moved to its own
# module (``chormanager/ui/choraufstellung_launcher.py``). Re-exported
# here for backward compatibility with the test that imports it from
# ``chormanager.ui.main_window``.
from .choraufstellung_launcher import refresh_tab_repositories  # noqa: E402, F401


class MainWindow(QMainWindow, ThemeMixin, TabRouterMixin, ChorAufstellungLauncherMixin):
    """Main window for ChorManager.

    M-1 step 4: ``_set_light_theme`` and ``_set_dark_theme`` are now
    inherited from ``ThemeMixin`` (see ``chormanager/ui/theme_manager.py``).
    M-1 step 5: tab-routing methods (``_emit_selection``,
    ``_update_context_toolbar``, ``_on_selection_changed``,
    ``_update_info_labels``, ``_on_project_changed``, ``_on_event_selected``,
    ``_on_besetzung_changed``, ``_on_tab_changed``) are inherited from
    ``TabRouterMixin`` (see ``chormanager/ui/tab_router.py``).
    M-1 step 6: the four ChorAufstellung-spawning methods
    (``_open_choraufstellung``, ``_open_choraufstellung_selected_or_new``,
    ``_open_choraufstellung_file``, ``_open_choraufstellung_for_event``)
    and the ``_edit_formation`` wrapper are inherited from
    ``ChorAufstellungLauncherMixin``
    (see ``chormanager/ui/choraufstellung_launcher.py``).
    """


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
        self.project_info_label.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum
        )
        info_layout.addWidget(self.project_info_label)

        # Besetzung-Status Label
        besetzung_status_label = QLabel("Aktive Besetzung:")
        besetzung_status_label.setStyleSheet("font-weight: normal; color: #666;")
        info_layout.addWidget(besetzung_status_label)

        self.besetzung_info_label = QLabel("Keine")
        self.besetzung_info_label.setObjectName("besetzungInfoLabel")
        self.besetzung_info_label.setVisible(True)
        self.besetzung_info_label.setWordWrap(False)
        self.besetzung_info_label.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum
        )
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
        self.event_info_label.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum
        )
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

        file_menu.addSeparator()

        backup_restore_action = QAction("Backup & Restore...", self)
        backup_restore_action.setIcon(
            get_icon("media-floppy", QStyle.StandardPixmap.SP_DriveFDIcon)
        )
        backup_restore_action.triggered.connect(self._open_backup_restore)
        file_menu.addAction(backup_restore_action)


        exit_action = QAction("Beenden", self)
        exit_action.setIcon(
            get_icon("application-exit", QStyle.StandardPixmap.SP_DialogCloseButton)
        )
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menubar.addMenu("&Bearbeiten")

        undo_action = QAction("Rückgängig", self)
        undo_action.setIcon(get_icon("edit-undo", QStyle.StandardPixmap.SP_ArrowBack))
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self._undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("Wiederholen", self)
        redo_action.setIcon(
            get_icon("edit-redo", QStyle.StandardPixmap.SP_ArrowForward)
        )
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self._redo)
        edit_menu.addAction(redo_action)

        projekt_menu = menubar.addMenu("&Projekt")

        new_projekt_action = QAction("Neu...", self)
        new_projekt_action.setIcon(
            get_icon("document-new", QStyle.StandardPixmap.SP_FileIcon)
        )
        new_projekt_action.triggered.connect(self._new_projekt)
        projekt_menu.addAction(new_projekt_action)

        save_projekt_action = QAction("Speichern", self)
        save_projekt_action.setIcon(
            get_icon("document-save", QStyle.StandardPixmap.SP_DialogSaveButton)
        )
        save_projekt_action.triggered.connect(self._save_projekt)
        projekt_menu.addAction(save_projekt_action)

        open_projekt_action = QAction("Öffnen...", self)
        open_projekt_action.setIcon(
            get_icon("document-open", QStyle.StandardPixmap.SP_DialogOpenButton)
        )
        open_projekt_action.triggered.connect(self._open_projekt)
        projekt_menu.addAction(open_projekt_action)
        
        edit_projekt_action = QAction("Bearbeiten...", self)
        edit_projekt_action.setIcon(get_icon("document-edit", QStyle.StandardPixmap.SP_FileDialogDetailedView))
        edit_projekt_action.triggered.connect(self._edit_project)
        projekt_menu.addAction(edit_projekt_action)
        
        delete_projekt_action = QAction("Löschen", self)
        delete_projekt_action.setIcon(get_icon("edit-delete", QStyle.StandardPixmap.SP_TrashIcon))
        delete_projekt_action.triggered.connect(self._delete_project)
        projekt_menu.addAction(delete_projekt_action)
        
        projekt_menu.addSeparator()

        export_menu = projekt_menu.addMenu("Export")
        
        export_libreoffice_action = QAction("LibreOffice exportieren...", self)
        export_libreoffice_action.setIcon(
            get_icon("x-office-document", QStyle.StandardPixmap.SP_FileIcon)
        )
        export_libreoffice_action.triggered.connect(self._export_project_libreoffice)
        export_menu.addAction(export_libreoffice_action)
        
        export_csv_action = QAction("CSV exportieren...", self)
        export_csv_action.setIcon(
            get_icon("x-office-spreadsheet", QStyle.StandardPixmap.SP_FileIcon)
        )
        export_csv_action.triggered.connect(self._export_project_csv)
        export_menu.addAction(export_csv_action)

        saenger_menu = menubar.addMenu("Sänger")
        
        add_singer_action = QAction("Hinzufügen...", self)
        add_singer_action.setIcon(get_icon("list-add", QStyle.StandardPixmap.SP_FileIcon))
        add_singer_action.triggered.connect(lambda: self.singers_tab._add_singer() if hasattr(self, "singers_tab") else None)
        saenger_menu.addAction(add_singer_action)
        
        edit_singer_action = QAction("Bearbeiten...", self)
        edit_singer_action.setIcon(get_icon("document-edit", QStyle.StandardPixmap.SP_FileDialogDetailedView))
        edit_singer_action.triggered.connect(lambda: self.singers_tab._edit_singer() if hasattr(self, "singers_tab") else None)
        saenger_menu.addAction(edit_singer_action)
        
        delete_singer_action = QAction("Löschen", self)
        delete_singer_action.setIcon(get_icon("edit-delete", QStyle.StandardPixmap.SP_TrashIcon))
        delete_singer_action.triggered.connect(lambda: self.singers_tab._delete_singer() if hasattr(self, "singers_tab") else None)
        saenger_menu.addAction(delete_singer_action)
        
        saenger_menu.addSeparator()
        
        saenger_export_menu = saenger_menu.addMenu("Export")
        export_lo_saenger = QAction("LibreOffice exportieren...", self)
        export_lo_saenger.triggered.connect(lambda: self._export_tab(1))
        saenger_export_menu.addAction(export_lo_saenger)
        export_csv_saenger = QAction("CSV exportieren...", self)
        export_csv_saenger.triggered.connect(lambda: self._export_tab_csv(1))
        saenger_export_menu.addAction(export_csv_saenger)

        besetzung_menu = menubar.addMenu("Besetzung")
        
        add_besetzung_action = QAction("Hinzufügen...", self)
        add_besetzung_action.setIcon(get_icon("list-add", QStyle.StandardPixmap.SP_FileIcon))
        add_besetzung_action.triggered.connect(lambda: self.besetzung_tab._new_besetzung() if hasattr(self, "besetzung_tab") else None)
        besetzung_menu.addAction(add_besetzung_action)
        
        edit_besetzung_action = QAction("Bearbeiten...", self)
        edit_besetzung_action.setIcon(get_icon("document-edit", QStyle.StandardPixmap.SP_FileDialogDetailedView))
        edit_besetzung_action.triggered.connect(lambda: self.besetzung_tab._edit_besetzung() if hasattr(self, "besetzung_tab") else None)
        besetzung_menu.addAction(edit_besetzung_action)
        
        delete_besetzung_action = QAction("Löschen", self)
        delete_besetzung_action.setIcon(get_icon("edit-delete", QStyle.StandardPixmap.SP_TrashIcon))
        delete_besetzung_action.triggered.connect(lambda: self.besetzung_tab._delete_besetzung() if hasattr(self, "besetzung_tab") else None)
        besetzung_menu.addAction(delete_besetzung_action)
        
        besetzung_menu.addSeparator()
        
        besetzung_export_menu = besetzung_menu.addMenu("Export")
        export_lo_besetzung = QAction("LibreOffice exportieren...", self)
        export_lo_besetzung.triggered.connect(self._export_besetzung)
        besetzung_export_menu.addAction(export_lo_besetzung)
        export_csv_besetzung = QAction("CSV exportieren...", self)
        export_csv_besetzung.triggered.connect(self._export_besetzung)
        besetzung_export_menu.addAction(export_csv_besetzung)

        termin_menu = menubar.addMenu("&Termine")

        new_event_action = QAction("Neuer Termin...", self)
        new_event_action.setIcon(
            get_icon("list-add", QStyle.StandardPixmap.SP_FileIcon)
        )
        new_event_action.triggered.connect(self._new_event)
        termin_menu.addAction(new_event_action)
        
        edit_event_action = QAction("Bearbeiten...", self)
        edit_event_action.setIcon(get_icon("document-edit", QStyle.StandardPixmap.SP_FileDialogDetailedView))
        edit_event_action.triggered.connect(self._edit_event)
        termin_menu.addAction(edit_event_action)
        
        delete_event_action = QAction("Löschen", self)
        delete_event_action.setIcon(get_icon("edit-delete", QStyle.StandardPixmap.SP_TrashIcon))
        delete_event_action.triggered.connect(self._delete_event)
        termin_menu.addAction(delete_event_action)
        
        termin_menu.addSeparator()

        manage_availability_action = QAction("Verfügbarkeit verwalten...", self)
        manage_availability_action.setIcon(
            get_icon("view-calendar", QStyle.StandardPixmap.SP_FileIcon)
        )
        manage_availability_action.triggered.connect(self._manage_availability)
        termin_menu.addAction(manage_availability_action)

        termin_menu.addSeparator()

        list_events_action = QAction("Terminliste anzeigen...", self)
        list_events_action.setIcon(
            get_icon("x-office-spreadsheet", QStyle.StandardPixmap.SP_FileIcon)
        )
        list_events_action.triggered.connect(self._list_events)
        termin_menu.addAction(list_events_action)

        termin_menu.addSeparator()
        termin_export_menu = termin_menu.addMenu("Export")
        export_lo_termin = QAction("LibreOffice exportieren...", self)
        export_lo_termin.triggered.connect(self._export_termine)
        termin_export_menu.addAction(export_lo_termin)
        export_csv_termin = QAction("CSV exportieren...", self)
        export_csv_termin.triggered.connect(self._export_termine)
        termin_export_menu.addAction(export_csv_termin)

        choraufstellung_menu = menubar.addMenu("Aufstellung")

        # Bug-fix 2026-06-12: 'In Aufstellung öffnen...' was wired to
        # ``self._open_choraufstellung`` which always spawned a fresh
        # editor (no CHOR_FILE) and therefore showed an empty grid
        # when the user wanted to reopen a saved formation. It is now
        # wired to ``self._edit_formation`` (same handler as
        # context-toolbar and right-click 'Bearbeiten'), which opens
        # the currently selected formation file. If no row is
        # selected, it falls back to opening a fresh editor.
        open_action = QAction("In Aufstellung öffnen...", self)
        open_action.setIcon(
            get_icon("media-playback-start", QStyle.StandardPixmap.SP_FileIcon)
        )
        open_action.triggered.connect(
            lambda: self._open_choraufstellung_selected_or_new()
        )
        choraufstellung_menu.addAction(open_action)

        choraufstellung_menu.addSeparator()
        aufstellung_export_menu = choraufstellung_menu.addMenu("Export")
        export_lo_aufstellung = QAction("LibreOffice exportieren...", self)
        export_lo_aufstellung.triggered.connect(self._export_aufstellung)
        aufstellung_export_menu.addAction(export_lo_aufstellung)
        export_csv_aufstellung = QAction("CSV exportieren...", self)
        export_csv_aufstellung.triggered.connect(self._export_aufstellung)
        aufstellung_export_menu.addAction(export_csv_aufstellung)

        repertoire_menu = menubar.addMenu("Repertoire")

        add_rep_action = QAction("Hinzufügen...", self)
        add_rep_action.setIcon(get_icon("list-add", QStyle.StandardPixmap.SP_FileIcon))
        add_rep_action.triggered.connect(lambda: self.repertoire_tab._add_repertoire() if hasattr(self, "repertoire_tab") else None)
        repertoire_menu.addAction(add_rep_action)

        edit_rep_action = QAction("Bearbeiten...", self)
        edit_rep_action.setIcon(
            get_icon("document-edit", QStyle.StandardPixmap.SP_FileDialogDetailedView)
        )
        edit_rep_action.triggered.connect(lambda: self.repertoire_tab._edit_repertoire() if hasattr(self, "repertoire_tab") else None)
        repertoire_menu.addAction(edit_rep_action)

        delete_rep_action = QAction("Löschen", self)
        delete_rep_action.setIcon(get_icon("edit-delete", QStyle.StandardPixmap.SP_TrashIcon))
        delete_rep_action.triggered.connect(lambda: self.repertoire_tab._delete_repertoire() if hasattr(self, "repertoire_tab") else None)
        repertoire_menu.addAction(delete_rep_action)

        view_menu = menubar.addMenu("&Ansicht")

        light_theme_action = QAction("Hell", self)
        light_theme_action.setIcon(
            get_icon("weather-clear", QStyle.StandardPixmap.SP_FileIcon)
        )
        light_theme_action.triggered.connect(self._set_light_theme)
        view_menu.addAction(light_theme_action)

        dark_theme_action = QAction("Dunkel", self)
        dark_theme_action.setIcon(
            get_icon("weather-night", QStyle.StandardPixmap.SP_FileIcon)
        )
        dark_theme_action.triggered.connect(self._set_dark_theme)
        view_menu.addAction(dark_theme_action)

        konfig_menu = menubar.addMenu("Konfiguration")

        konfig_action = QAction("Einstellungen...", self)
        konfig_action.setIcon(
            get_icon("preferences-system", QStyle.StandardPixmap.SP_FileIcon)
        )
        konfig_action.triggered.connect(self._show_config)
        konfig_menu.addAction(konfig_action)

        marketing_menu = menubar.addMenu("Marketing")

        selbstdarstellung_action = QAction("Selbstdarstellung...", self)
        selbstdarstellung_action.setIcon(
            get_icon("x-office-document", QStyle.StandardPixmap.SP_FileIcon)
        )
        selbstdarstellung_action.triggered.connect(self._show_selbstdarstellung)
        marketing_menu.addAction(selbstdarstellung_action)


        hilfe_menu = menubar.addMenu("&Hilfe")

        check_version_action = QAction("Version prüfen", self)
        check_version_action.setIcon(get_icon("system-software-update", QStyle.StandardPixmap.SP_FileIcon))
        check_version_action.triggered.connect(self._check_version)
        hilfe_menu.addAction(check_version_action)

        hilfe_menu.addSeparator()

        about_action = QAction("Über", self)
        about_action.setIcon(get_icon("help-about", QStyle.StandardPixmap.SP_FileIcon))
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
        self.nav_projects = QPushButton("Projekte")
        self.nav_projects.setIcon(
            get_icon("folder", QStyle.StandardPixmap.SP_DirClosedIcon)
        )
        self.nav_projects.setCheckable(True)
        self.nav_projects.setChecked(True)
        self.nav_projects.clicked.connect(lambda: self._switch_view(0))
        sidebar_layout.addWidget(self.nav_projects)

        self.nav_singers = QPushButton("Sänger")
        self.nav_singers.setIcon(
            get_icon("user-info", QStyle.StandardPixmap.SP_FileIcon)
        )
        self.nav_singers.setCheckable(True)
        self.nav_singers.clicked.connect(lambda: self._switch_view(1))
        sidebar_layout.addWidget(self.nav_singers)

        self.nav_besetzung = QPushButton("Besetzung")
        self.nav_besetzung.setIcon(
            get_icon("system-users", QStyle.StandardPixmap.SP_DirHomeIcon)
        )
        self.nav_besetzung.setCheckable(True)
        self.nav_besetzung.clicked.connect(lambda: self._switch_view(2))
        sidebar_layout.addWidget(self.nav_besetzung)

        self.nav_events = QPushButton("Termine")
        self.nav_events.setIcon(
            get_icon("x-office-calendar", QStyle.StandardPixmap.SP_FileIcon)
        )
        self.nav_events.setCheckable(True)
        self.nav_events.clicked.connect(lambda: self._switch_view(3))
        sidebar_layout.addWidget(self.nav_events)

        self.nav_formations = QPushButton("Aufstellung")
        self.nav_formations.setIcon(
            get_icon("audio-volume-high", QStyle.StandardPixmap.SP_MediaVolume)
        )
        self.nav_formations.setCheckable(True)
        self.nav_formations.clicked.connect(lambda: self._switch_view(4))
        sidebar_layout.addWidget(self.nav_formations)

        self.nav_repertoire = QPushButton("Repertoire")
        self.nav_repertoire.setIcon(
            get_icon("view-list", QStyle.StandardPixmap.SP_FileIcon)
        )
        self.nav_repertoire.setCheckable(True)
        self.nav_repertoire.clicked.connect(lambda: self._switch_view(5))
        sidebar_layout.addWidget(self.nav_repertoire)

        sidebar_layout.addStretch()

        splitter.addWidget(sidebar)

        # Content-Bereich (rechts) - mit horizontaler Context Toolbar oben
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

# Page title bar
        self.page_title_label = QLabel("Projektverwaltung")
        self.page_title_label.setObjectName("pageTitle")
        content_layout.addWidget(self.page_title_label)

        # Context toolbar (horizontal oberhalb des Content)
        self.context_toolbar = QToolBar("Aktionen")
        self.context_toolbar.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.context_toolbar.setMovable(False)
        self.context_toolbar.setIconSize(QSize(16, 16))
        content_layout.addWidget(self.context_toolbar)

        # Runtime selection state. Initialised to None so that code
        # paths that read self.current_project / self.current_event
        # (e.g. line 1042: 'self.current_project.id if
        # self.current_project else None') never trip an AttributeError
        # when no project has been selected yet (e.g. fresh DB or a
        # stale last_active_project_id that no longer exists).
        # _on_project_changed / _on_event_selected (in tab_router.py)
        # overwrite these when a real selection happens.
        self.current_project = None
        self.current_event = None

        from .views.projects_tab import ProjectsTab

        self.projects_tab = ProjectsTab(self.db)
        self.projects_tab.current_project_changed.connect(self._on_project_changed)
        self.projects_tab._load_active_project()
        self._update_context_toolbar(0, self.projects_tab.current_project)

        from .views.singers_tab import SingersTab

        self.singers_tab = SingersTab(self.db)

        from .views.events_tab import EventsTab

        self.events_tab = EventsTab(self.db)
        self.events_tab.event_selected.connect(self._on_event_selected)
        self.events_tab._restore_active_event()

        from .views.besetzung_tab import BesetzungTab
        self.besetzung_tab = BesetzungTab(self.db)
        self.besetzung_tab.active_besetzung_changed.connect(self._on_besetzung_changed)
        self.besetzung_tab._restore_active_besetzung()

        from .views.choraufstellung_tab import ChorAufstellungTab
        self.choraufstellung_tab = ChorAufstellungTab(self.db)

        from .views.repertoire_tab import RepertoireTab
        self.repertoire_tab = RepertoireTab(self.db)

        # Stacked widget für Content
        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(self.projects_tab)
        self.content_stack.addWidget(self.singers_tab)
        self.content_stack.addWidget(self.besetzung_tab)
        self.content_stack.addWidget(self.events_tab)
        self.content_stack.addWidget(self.choraufstellung_tab)
        self.content_stack.addWidget(self.repertoire_tab)

        content_layout.addWidget(self.content_stack)

        splitter.addWidget(content_area)
        splitter.setStretchFactor(1, 1)

        # Initialize context toolbar for current view (projects)
        self._update_context_toolbar(0, self.projects_tab.current_project)

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
        titles = [
            "Projektverwaltung",
            "Sängerverwaltung",
            "Besetzungen",
            "Terminverwaltung",
            "Choraufstellung",
            "Repertoire",
        ]
        self.page_title_label.setText(titles[index])
        self.content_stack.setCurrentIndex(index)
        self.nav_projects.setChecked(index == 0)
        self.nav_singers.setChecked(index == 1)
        self.nav_besetzung.setChecked(index == 2)
        self.nav_events.setChecked(index == 3)
        self.nav_formations.setChecked(index == 4)
        self.nav_repertoire.setChecked(index == 5)
        self._emit_selection(index)



    def _create_status_bar(self):
        """Create status bar."""
        self.statusBar().showMessage("Bereit")

    def _refresh_tabs(self):
        """Refresh all tabs."""
        if hasattr(self, "singers_tab"):
            self.singers_tab._load_singers()
        if hasattr(self, "events_tab"):
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

    # NOTE: ``_open_choraufstellung_for_event`` and ``_edit_formation``
    # moved to ``ChorAufstellungLauncherMixin`` in M-1 step 6
    # (see ``chormanager/ui/choraufstellung_launcher.py``). The wrapper
    # methods below remain here because they are still called from
    # many places in MainWindow.

    def _duplicate_formation(self):
        self.choraufstellung_tab._duplicate_formation()

    def _delete_formation(self):
        self.choraufstellung_tab._delete_formation()

    def _new_formation(self):
        self.choraufstellung_tab._new_formation()

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
                writer = csv.DictWriter(
                    f, fieldnames=[field["name"] for field in fields]
                )
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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
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
            QMessageBox.warning(self, "Fehler", f"LibreOffice Fehler:\n{result.stderr}")

        if os.path.exists(temp_csv):
            os.unlink(temp_csv)


    def _new_event(self):
        """Create a new event."""
        from .dialogs import EventDialog
        from ..domain.repository import EventRepository

        prefilled_project_id = self.current_project.id if self.current_project else None
        dialog = EventDialog(db=self.db, parent=self, prefilled_project_id=prefilled_project_id)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()

            if not data.get("name"):
                QMessageBox.warning(self, "Fehler", "Name ist erforderlich")
                return

            repo = EventRepository(self.db)
            repo.create(**data)
            if hasattr(self, 'projects_tab'):
                self.projects_tab._load_projects()
            if hasattr(self, 'events_tab'):
                self.events_tab._load_events()

            self.statusBar().showMessage("Termin erstellt")

    def _manage_availability(self):
        """Manage availability for events."""
        self.events_tab._manage_availability()

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
        from datetime import datetime

        try:
            git_hash = subprocess.check_output(
                ["git", "describe", "--tags", "--abbrev=7", "--always", "--dirty"],
                cwd="/media/data/coding/chormanager",
                text=True,
            ).strip()
            commit_date = subprocess.check_output(
                ["git", "log", "-1", "--format=%cd", "--date=short"],
                cwd="/media/data/coding/chormanager",
                text=True,
            ).strip()
        except Exception:
            git_hash = "dev"
            commit_date = "unbekannt"

        QMessageBox.about(
            self,
            "Über ChorManager",
            f"<h3>ChorManager</h3>"
            f"<p>Desktop-Anwendung zur Verwaltung eines Chors</p>"
            f"<p>Version: {git_hash} ({commit_date})</p>",
        )

    def _show_selbstdarstellung(self):
        """Show selbstdarstellung dialog."""
        from .dialogs import SelbstdarstellungDialog

        dialog = SelbstdarstellungDialog(self.db, self)
        dialog.exec()

    # NOTE: ``_open_choraufstellung``, ``_open_choraufstellung_selected_or_new`` and
    # ``_open_choraufstellung_file`` moved to ``ChorAufstellungLauncherMixin``
    # in M-1 step 6 (see ``chormanager/ui/choraufstellung_launcher.py``).

    def _open_backup_restore(self):
        """Open Backup & Restore dialog."""
        from ..export.backup_service import BackupService
        from ..ui.dialogs import BackupRestoreDialog
        from pathlib import Path

        app_root = Path(__file__).parent.parent.parent
        service = BackupService(app_root)

        dialog = BackupRestoreDialog(self)
        dialog.service = service
        if dialog.exec():
            if dialog.restored:
                self._reload_after_restore()

    def _reload_after_restore(self):
        """Reload database and all tabs after backup restore."""
        try:
            self.db.close()
            self.db = Database(self.db_path)
            self.db.connect()

            self.singer_repo = SingerRepository(self.db)

            for tab_attr in ['projects_tab', 'singers_tab', 'besetzung_tab', 'events_tab', 'repertoire_tab', 'choraufstellung_tab']:
                if hasattr(self, tab_attr):
                    tab = getattr(self, tab_attr)
                    refresh_tab_repositories(tab, self.db)
            
            if hasattr(self, 'projects_tab'):
                self.projects_tab._load_projects()
            if hasattr(self, 'singers_tab'):
                self.singers_tab._load_singers()
            if hasattr(self, 'events_tab'):
                self.events_tab._load_events()
            if hasattr(self, 'besetzung_tab'):
                self.besetzung_tab._load_besetzungen()
            
            self.statusBar().showMessage("Datenbank nach Backup-Restore neu geladen.", 3000)
        except Exception as e:
            QMessageBox.critical(
                self, "Fehler", f"Fehler beim Neuladen der Datenbank:\n{str(e)}"
            )


    def _export_response_matrix(self):
        """Export a project-wide response matrix (PDF or ODT).

        The matrix covers:
          * All events belonging to the currently active project.
          * All singers in the active Besetzung (Choraufstellung filter).
            If there is no active Besetzung, all singers are included.

        The user is first asked for the output format (PDF / ODT), then
        for a destination file. A status-bar message confirms success
        or reports errors.
        """
        try:
            from ..domain.repository import (
                SingerRepository,
                EventRepository,
                ProjectRepository,
                BesetzungRepository,
                AvailabilityRepository,
            )
            from ..config import get_last_active_besetzung_id

            # 1) Resolve the active project
            project = (
                self.projects_tab.current_project
                if hasattr(self, "projects_tab")
                else None
            )
            if project is None:
                QMessageBox.information(
                    self,
                    "Information",
                    "Bitte wählen Sie zuerst ein aktives Projekt aus.",
                )
                return

            # 2) Load singers (filtered by active Besetzung)
            singer_repo = SingerRepository(self.db)
            singers = singer_repo.get_active()
            singer_filter_ids = None
            saved_besetzung_id = get_last_active_besetzung_id()
            if saved_besetzung_id:
                besetzung_repo = BesetzungRepository(self.db)
                besetzung = besetzung_repo.get_by_id(saved_besetzung_id)
                if besetzung and besetzung.project_id == project.id:
                    singer_filter_ids = besetzung.get_singer_ids()

            # 3) Load events for this project
            event_repo = EventRepository(self.db)
            all_events = event_repo.get_all()
            project_events = [e for e in all_events if e.project_id == project.id]

            # 4) Load availabilities for these events
            avail_repo = AvailabilityRepository(self.db)
            event_ids = {e.id for e in project_events}
            availabilities = [
                a
                for a in (
                    avail_repo.get_by_event(eid) for eid in event_ids
                )
                for a in a
            ] if event_ids else []

            # 5) Build the matrix
            matrix = build_response_matrix(
                singers=singers,
                events=project_events,
                availabilities=availabilities,
                title=project.name,
                singer_filter_ids=singer_filter_ids,
            )

            if not matrix.columns:
                QMessageBox.information(
                    self,
                    "Information",
                    f"Das Projekt '{project.name}' enthält keine Termine. "
                    "Es gibt nichts zu exportieren.",
                )
                return

            # 6) Ask the user for the output format
            dlg = ExportFormatDialog(self, default_format="pdf")
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            fmt_key = dlg.selected_format
            ext = SUPPORTED_FORMATS[fmt_key]["ext"]

            # 7) Ask for the destination file
            default_name = f"{project.name}-Zusagen{ext}"
            out_path = ExportFormatDialog.get_save_path(
                self, fmt_key, default_name,
            )
            if out_path is None:
                return

            # 8) Render
            if fmt_key == "pdf":
                render_response_matrix_pdf(matrix, out_path)
            else:
                render_response_matrix_odt(matrix, out_path)

            self.statusBar().showMessage(
                f"Zusagen/Absagen-Liste exportiert nach {out_path}", 5000,
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Fehler",
                f"Export fehlgeschlagen:\n{type(e).__name__}: {e}",
            )

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




    def _check_version(self):
        """Open version check dialog."""
        dialog = VersionCheckDialog(self)
        dialog.exec()
    

    _TAB_EXPORT_CONFIG = {
        'projekte': ('projects', 'projects_tab', 'project_repo', 'Projekte'),
        'saenger': ('singers', 'singers_tab', 'singer_repo', 'Sänger'),
        'besetzung': ('besetzung', 'besetzung_tab', 'besetzung_repo', 'Besetzungen'),
        'termine': ('events', 'events_tab', 'event_repo', 'Termine'),
    }

    def _get_export_config_for_current_tab(self):
        tab_index = self.content_stack.currentIndex()
        tab_map = {0: 'projekte', 1: 'saenger', 2: 'besetzung', 3: 'termine'}
        tab_key = tab_map.get(tab_index)
        if tab_key and tab_key in self._TAB_EXPORT_CONFIG:
            return self._TAB_EXPORT_CONFIG[tab_key]
        return None

    def _export_tab_generic(self):
        config = self._get_export_config_for_current_tab()
        if not config:
            QMessageBox.warning(self, 'Export', 'Export für diesen Tab nicht verfügbar.')
            return

        table_name, tab_attr, repo_attr, display_name = config
        repo = getattr(getattr(self, tab_attr), repo_attr)
        service = ExportService()

        fields = service.get_table_fields(self.db.get_connection(), table_name)
        if not fields:
            QMessageBox.warning(self, 'Warnung', f'Keine Felder für Tabelle {table_name} gefunden.')
            return

        dialog = ExportDialog(fields, self)
        if not dialog.exec():
            return

        selected_fields = dialog.get_selected_fields()
        fmt = dialog.get_export_format()

        if not selected_fields:
            QMessageBox.warning(self, 'Warnung', 'Keine Felder ausgewählt.')
            return

        items = repo.get_all()
        data = service.get_export_data(items, selected_fields)

        if fmt == 'writer':
            content = service.export_to_libreoffice_writer(data, selected_fields)
            ext_filter = 'LibreOffice Writer (*.odt)'
        elif fmt == 'calc':
            content = service.export_to_libreoffice_calc(data, selected_fields)
            ext_filter = 'LibreOffice Calc (*.ods)'
        else:
            content = service.export_to_csv(data, selected_fields)
            ext_filter = 'CSV (*.csv)'

        tab_name_map = {'Projekte': 'projekte', 'Sänger': 'saenger', 'Besetzungen': 'besetzungen', 'Termine': 'termine'}
        ext_map = {'writer': 'odt', 'calc': 'ods', 'csv': 'csv'}
        tab_file = tab_name_map.get(display_name, display_name.lower())
        ext = ext_map.get(fmt, 'csv')
        default_name = f'2026-04-26-{tab_file}.{ext}'
        workdir = Path(__file__).parent.parent.parent / 'workdir'
        workdir.mkdir(exist_ok=True)
        default_path = str(workdir / default_name)

        filename, _ = QFileDialog.getSaveFileName(
            self, f'{display_name} exportieren',
            default_path, ext_filter
        )
        if not filename:
            return

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        self.statusBar().showMessage(f'{display_name} exportiert ({fmt.upper()})')

    def _export_project_libreoffice(self):
        self.content_stack.setCurrentIndex(0)
        self._export_tab_generic()

    def _export_project_csv(self):
        self.content_stack.setCurrentIndex(0)
        self._export_tab_generic()

    def _export_tab(self, tab_index):
        self.content_stack.setCurrentIndex(tab_index)
        self._export_tab_generic()

    def _export_tab_csv(self, tab_index):
        self.content_stack.setCurrentIndex(tab_index)
        self._export_tab_generic()

    def _export_besetzung(self):
        besetzung_fields = [
            {'name': 'name', 'label': 'Name'},
            {'name': 'project', 'label': 'Projekt'},
            {'name': 'singer_count', 'label': 'Anzahl Sänger'},
            {'name': 'updated_at', 'label': 'Zuletzt gespeichert'},
        ]

        dialog = ExportDialog(besetzung_fields, self)
        if not dialog.exec():
            return

        selected = dialog.get_selected_fields()
        fmt = dialog.get_export_format()

        if not selected:
            QMessageBox.warning(self, 'Warnung', 'Keine Felder ausgewählt.')
            return

        service = ExportService()
        besetzungen = self.besetzung_tab.besetzung_repo.get_all()

        data = []
        for b in besetzungen:
            row = {}
            if 'name' in selected:
                row['name'] = b.name
            if 'project' in selected:
                proj = self.besetzung_tab.project_repo.get_by_id(b.project_id)
                row['project'] = proj.name if proj else '-'
            if 'singer_count' in selected:
                singer_ids = b.get_singer_ids()
                row['singer_count'] = len(singer_ids) if singer_ids else 0
            if 'updated_at' in selected:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(b.updated_at)
                    row['updated_at'] = dt.strftime('%d.%m.%Y %H:%M')
                except (ValueError, OSError):
                    row['updated_at'] = '-'
            data.append(row)

        if fmt == 'writer':
            content = service.export_to_libreoffice_writer(data, selected)
            ext_filter = 'LibreOffice Writer (*.odt)'
        elif fmt == 'calc':
            content = service.export_to_libreoffice_calc(data, selected)
            ext_filter = 'LibreOffice Calc (*.ods)'
        else:
            content = service.export_to_csv(data, selected)
            ext_filter = 'CSV (*.csv)'

        from pathlib import Path
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        workdir = Path(__file__).parent.parent / 'workdir'
        workdir.mkdir(exist_ok=True)
        ext_map = {'writer': 'odt', 'calc': 'ods', 'csv': 'csv'}
        ext = ext_map.get(fmt, 'csv')
        default_path = str(workdir / f'{today}-besetzungen.{ext}')

        filename, _ = QFileDialog.getSaveFileName(
            self, 'Besetzungen exportieren',
            default_path, ext_filter
        )
        if not filename:
            return

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        self.statusBar().showMessage(f'Besetzungen exportiert ({fmt.upper()})')

    def _export_termine(self):
        termin_fields = [
            {'name': 'date', 'label': 'Datum'},
            {'name': 'name', 'label': 'Name'},
            {'name': 'type', 'label': 'Typ'},
            {'name': 'project', 'label': 'Projekt'},
            {'name': 'yes_count', 'label': 'Verbindl. Zusagen'},
            {'name': 'conditional_count', 'label': 'Vorbehalt'},
        ]

        dialog = ExportDialog(termin_fields, self)
        if not dialog.exec():
            return

        selected = dialog.get_selected_fields()
        fmt = dialog.get_export_format()

        if not selected:
            QMessageBox.warning(self, 'Warnung', 'Keine Felder ausgewählt.')
            return

        service = ExportService()
        events = self.events_tab.event_repo.get_all()

        event_type_labels = {
            'gp': 'GP', 'op': 'OP', 'sofa': 'SOFA',
            'probe': 'Probe', 'konzert': 'Konzert',
            'auftritt': 'Auftritt', 'sonstiges': 'Sonstiges',
        }

        data = []
        for e in events:
            row = {}
            if 'date' in selected:
                try:
                    from datetime import datetime
                    if e.date and len(e.date) >= 10:
                        dt = datetime.strptime(e.date[:10], '%Y-%m-%d')
                        row['date'] = dt.strftime('%d.%m.%Y')
                    else:
                        row['date'] = e.date or '-'
                except:
                    row['date'] = e.date[:10] if e.date else '-'
            if 'name' in selected:
                row['name'] = e.name or ''
            if 'type' in selected:
                row['type'] = event_type_labels.get(e.event_type, e.event_type or '')
            if 'project' in selected:
                proj = self.events_tab.project_repo.get_by_id(e.project_id)
                row['project'] = proj.name if proj else ''
            if 'yes_count' in selected:
                avails = self.events_tab.avail_repo.get_by_event(e.id)
                row['yes_count'] = sum(1 for a in avails if a.status == 'yes')
            if 'conditional_count' in selected:
                avails = self.events_tab.avail_repo.get_by_event(e.id)
                row['conditional_count'] = sum(1 for a in avails if a.status == 'conditional')
            data.append(row)

        if fmt == 'writer':
            content = service.export_to_libreoffice_writer(data, selected)
            ext_filter = 'LibreOffice Writer (*.odt)'
        elif fmt == 'calc':
            content = service.export_to_libreoffice_calc(data, selected)
            ext_filter = 'LibreOffice Calc (*.ods)'
        else:
            content = service.export_to_csv(data, selected)
            ext_filter = 'CSV (*.csv)'

        from pathlib import Path
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        workdir = Path(__file__).parent.parent / 'workdir'
        workdir.mkdir(exist_ok=True)
        ext_map = {'writer': 'odt', 'calc': 'ods', 'csv': 'csv'}
        ext = ext_map.get(fmt, 'csv')
        default_path = str(workdir / f'{today}-termine.{ext}')

        filename, _ = QFileDialog.getSaveFileName(
            self, 'Termine exportieren',
            default_path, ext_filter
        )
        if not filename:
            return

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        self.statusBar().showMessage(f'Termine exportiert ({fmt.upper()})')

    def _export_aufstellung(self):
        aufstellung_fields = [
            {'name': 'filename', 'label': 'Dateiname'},
            {'name': 'size', 'label': 'Dateigröße'},
            {'name': 'project', 'label': 'Projekt'},
            {'name': 'event_date', 'label': 'Termin'},
            {'name': 'event', 'label': 'Typ'},
            {'name': 'saved_at', 'label': 'Gespeichert'},
        ]

        dialog = ExportDialog(aufstellung_fields, self)
        if not dialog.exec():
            return

        selected = dialog.get_selected_fields()
        fmt = dialog.get_export_format()

        if not selected:
            QMessageBox.warning(self, 'Warnung', 'Keine Felder ausgewählt.')
            return

        import os
        service = ExportService()
        data_dir = self.choraufstellung_tab._data_dir

        files = []
        if os.path.exists(data_dir):
            for f in os.listdir(data_dir):
                if f.endswith('.json'):
                    fp = os.path.join(data_dir, f)
                    stats = os.stat(fp)
                    entry = {'filename': f, 'size': stats.st_size}
                    try:
                        with open(fp, 'r', encoding='utf-8') as jf:
                            content_json = json.load(jf)
                            entry['metadata'] = content_json.get('metadata', {})
                            entry['saved_at'] = content_json.get('saved_at', '')
                    except:
                        entry['metadata'] = {}
                        entry['saved_at'] = ''
                    files.append(entry)

        data = []
        for f in files:
            meta = f.get('metadata', {})
            row = {}
            if 'filename' in selected:
                row['filename'] = f['filename']
            if 'size' in selected:
                sz = f.get('size', 0)
                row['size'] = f'{sz // 1024} KB' if sz >= 1024 else f'{sz} B'
            if 'project' in selected:
                row['project'] = meta.get('project', '')
            if 'event_date' in selected:
                ed = meta.get('event_date', '')
                row['event_date'] = ed[:10] if ed else ''
            if 'event' in selected:
                row['event'] = meta.get('event', '')
            if 'saved_at' in selected:
                saved = f.get('saved_at', '')
                if saved:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(saved)
                        row['saved_at'] = dt.strftime('%d.%m.%Y %H:%M')
                    except:
                        row['saved_at'] = saved
                else:
                    row['saved_at'] = ''
            data.append(row)

        if fmt == 'writer':
            content = service.export_to_libreoffice_writer(data, selected)
            ext_filter = 'LibreOffice Writer (*.odt)'
        elif fmt == 'calc':
            content = service.export_to_libreoffice_calc(data, selected)
            ext_filter = 'LibreOffice Calc (*.ods)'
        else:
            content = service.export_to_csv(data, selected)
            ext_filter = 'CSV (*.csv)'

        from pathlib import Path
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        workdir = Path(__file__).parent.parent / 'workdir'
        workdir.mkdir(exist_ok=True)
        ext_map = {'writer': 'odt', 'calc': 'ods', 'csv': 'csv'}
        ext = ext_map.get(fmt, 'csv')
        default_path = str(workdir / f'{today}-aufstellungen.{ext}')

        filename, _ = QFileDialog.getSaveFileName(
            self, 'Aufstellungen exportieren',
            default_path, ext_filter
        )
        if not filename:
            return

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        self.statusBar().showMessage(f'Aufstellungen exportiert ({fmt.upper()})')


# --- M-1 step 2: VersionCheckDialog was moved to its own module.
# Re-exported here for backward compatibility with any code that
# imports ``chormanager.ui.main_window.VersionCheckDialog``.
from .update_controller import VersionCheckDialog  # noqa: E402, F401


# --- M-1 step 3: refresh_tab_repositories was moved to its own module.
# Re-exported here for backward compatibility with the unit test
# (tests/unit/test_reload_after_restore.py) that imports it from
# the original location.
from .choraufstellung_launcher import refresh_tab_repositories  # noqa: E402, F401
