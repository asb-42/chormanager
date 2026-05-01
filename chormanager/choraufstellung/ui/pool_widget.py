# UI: SingerPool widget and dialogs
try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QTableWidget, QTableWidgetItem, QHeaderView, QMenu,
        QDialog, QFormLayout, QLineEdit, QComboBox, QCompleter,
        QScrollArea, QCheckBox, QMessageBox
    )
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QColor, QFont, QPalette
except ImportError:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QTableWidget, QTableWidgetItem, QHeaderView, QMenu,
        QDialog, QFormLayout, QLineEdit, QComboBox, QCompleter,
        QScrollArea, QCheckBox, QMessageBox
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QColor, QFont, QPalette

from qt_compat import exec_qt
from singer_model import VoiceGroup, Singer, voice_group_color
from core.commands import UndoCommand


class AddSingerDialog(QDialog):
    """Dialog for adding or editing a singer."""
    
    def __init__(self, parent=None, singer=None):
        super().__init__(parent)
        self.singer = singer
        self.setWindowTitle("Sänger bearbeiten" if singer else "Sänger hinzufügen")
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QFormLayout(self)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nachname, Vorname")
        if self.singer:
            self.name_input.setText(self.singer.name)
        layout.addRow("Name:", self.name_input)
        
        self.voice_group_combo = QComboBox()
        for vg in VoiceGroup:
            self.voice_group_combo.addItem(vg.value if hasattr(vg, 'value') else str(vg), vg)
        if self.singer:
            vg_val = self.singer.voice_group.value if hasattr(self.singer.voice_group, 'value') else str(self.singer.voice_group)
            idx = self.voice_group_combo.findText(vg_val)
            if idx >= 0:
                self.voice_group_combo.setCurrentIndex(idx)
        layout.addRow("Stimmgruppe:", self.voice_group_combo)
        
        self.height_input = QLineEdit()
        if self.singer and self.singer.height > 0:
            self.height_input.setText(str(self.singer.height))
        layout.addRow("Größe (cm):", self.height_input)
        
        buttons = QHBoxLayout()
        buttons.addWidget(QPushButton("Speichern", clicked=self.accept))
        buttons.addWidget(QPushButton("Abbrechen", clicked=self.reject))
        layout.addRow(buttons)
    
    def get_singer(self):
        name = self.name_input.text().strip()
        if not name:
            return None
        
        height = 0
        try:
            height = int(self.height_input.text().strip()) if self.height_input.text().strip() else 0
        except ValueError:
            pass
        
        if self.singer:
            return Singer(name, self.voice_group_combo.currentData(), height, self.singer.singer_id)
        return Singer(name, self.voice_group_combo.currentData(), height)


class AffinityDialog(QDialog):
    """Dialog for setting proximity/affinity between singers."""
    
    def __init__(self, parent=None, singer=None, all_singers=None):
        super().__init__(parent)
        self.singer = singer
        self.all_singers = all_singers or []
        self.setWindowTitle(f"Nähe setzen für {singer.name}")
        self.setMinimumWidth(350)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Singpartner für <b>{self.singer.name}</b> auswählen:"))
        
        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.lineEdit().setPlaceholderText("Name eingeben oder auswählen...")
        
        other_singers = [s for s in self.all_singers if s.singer_id != self.singer.singer_id]
        for s in other_singers:
            self.combo.addItem(s.name, s.singer_id)
        
        if self.singer.affinity:
            idx = self.combo.findData(self.singer.affinity)
            if idx >= 0:
                self.combo.setCurrentIndex(idx)
        
        completer = QCompleter([s.name for s in other_singers], self)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.combo.setCompleter(completer)
        
        layout.addWidget(self.combo)
        
        clear_btn = QPushButton("Keine Nähe")
        clear_btn.clicked.connect(self.clear_affinity)
        layout.addWidget(clear_btn)
        
        buttons = QHBoxLayout()
        buttons.addWidget(QPushButton("Speichern", clicked=self.accept))
        buttons.addWidget(QPushButton("Abbrechen", clicked=self.reject))
        layout.addLayout(buttons)
    
    def clear_affinity(self):
        self.combo.setCurrentIndex(-1)
        self.combo.setCurrentText("")
    
    def get_affinity_singer_id(self):
        text = self.combo.currentText().strip()
        data = self.combo.currentData()
        if data:
            return data
        for s in self.all_singers:
            if s.name == text:
                return s.singer_id
        return ""


class VoicingConfigDialog(QDialog):
    """Dialog for configuring active voice groups."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QDialog { background: #f9f6f0; }")
        self.setWindowTitle("Besatzung konfigurieren")
        self.resize(300, 350)
        self._setup_ui()
    
    def _setup_ui(self):
        from config import load_voice_groups_config
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Aktive Stimmgruppen:"))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        container = QWidget()
        self.checkboxes = {}
        v_layout = QVBoxLayout(container)
        
        for vg in load_voice_groups_config():
            cb = QCheckBox(vg["id"])
            color = vg["color"]
            cb.setStyleSheet(f"""
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
            """)
            self.checkboxes[vg["id"]] = cb
            v_layout.addWidget(cb)
        
        scroll.setWidget(container)
        
        buttons = QHBoxLayout()
        buttons.addWidget(QPushButton("OK", clicked=self.accept))
        buttons.addWidget(QPushButton("Abbrechen", clicked=self.reject))
        layout.addLayout(buttons)
    
    def set_active(self, active_groups):
        for g, c in self.checkboxes.items():
            c.setChecked(g in active_groups)
    
    def get_active(self):
        return [g for g, c in self.checkboxes.items() if c.isChecked()]


class SingerPool(QWidget):
    """Widget for managing the pool of singers."""
    singer_selected = pyqtSignal(object)
    singer_added = pyqtSignal(object)
    singer_edit_requested = pyqtSignal(object)
    place_all_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.singers = []
        self.placed_singer_ids = set()
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header with count
        self.pool_header = QLabel("<b>Sängerpool</b>")
        layout.addWidget(self.pool_header)
        self.pool_count_label = QLabel("0 Sänger")
        self.pool_count_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(self.pool_count_label)
        layout.addWidget(QLabel("Doppelklick: automatisch\nDrag & Drop: manuell\nRechtsklick: Bearbeiten / Nähe"))
        
        self.table = DraggableTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Stimmgruppe", "Größe", "Nähe"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setDragDropMode(QTableWidget.DragDropMode.DragOnly)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemDoubleClicked.connect(self.on_double_click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.cellClicked.connect(self.on_cell_clicked)
        layout.addWidget(self.table)
        
        buttons = QVBoxLayout()
        buttons.addWidget(QPushButton("Alle Sänger platzieren", clicked=self.place_all_requested.emit))
        buttons.addWidget(QPushButton("Einzelner Sänger", clicked=self.add_dialog))
        buttons.addWidget(QPushButton("Import (CSV/TXT)", clicked=self.do_import))
        buttons.addWidget(QPushButton("Ausgewählten entfernen", clicked=self.remove_selected))
        layout.addLayout(buttons)
    
    def on_cell_clicked(self, row, col):
        item = self.table.item(row, 0)
        if item:
            singer = item.data(Qt.ItemDataRole.UserRole)
            if singer:
                self.singer_selected.emit(singer)
    
    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if item:
            row = item.row()
            singer = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if singer:
                menu = QMenu(self)
                edit_action = menu.addAction("Bearbeiten")
                affinity_action = menu.addAction("Nähe setzen")
                remove_action = menu.addAction("Entfernen")
                action = menu.exec(self.table.viewport().mapToGlobal(pos))
                
                if action == edit_action:
                    self.singer_edit_requested.emit(singer)
                elif action == affinity_action:
                    self.set_affinity(singer)
                elif action == remove_action:
                    self.table.selectRow(row)
                    self.remove_selected()
    
    def set_affinity(self, singer):
        """Set proximity/affinity for a singer."""
        d = AffinityDialog(self, singer=singer, all_singers=self.singers)
        if d.exec() == QDialog.DialogCode.Accepted:
            new_affinity_id = d.get_affinity_singer_id()
            old_affinity_id = singer.affinity
            
            # Clear old bidirectional affinity
            if old_affinity_id:
                old_partner = next((s for s in self.singers if s.singer_id == old_affinity_id), None)
                if old_partner and old_partner.affinity == singer.singer_id:
                    old_partner.affinity = ""
            
            # Set new affinity
            singer.affinity = new_affinity_id
            
            # Set bidirectional affinity
            if new_affinity_id:
                partner = next((s for s in self.singers if s.singer_id == new_affinity_id), None)
                if partner:
                    partner.affinity = singer.singer_id
            
            self.update_singers(self.singers, self.placed_singer_ids)
            if hasattr(self.parent(), '_mark_modified'):
                self.parent()._mark_modified()
    
    def update_singers(self, singers, placed_ids=None):
        self.singers = singers
        if placed_ids is not None:
            self.placed_singer_ids = placed_ids
        
        self.table.setRowCount(0)
        
        for s in self.singers:
            if str(s.singer_id) in self.placed_singer_ids:
                continue
            
            row_pos = self.table.rowCount()
            self.table.insertRow(row_pos)
            
            vg_color = voice_group_color(s.voice_group)
            
            # Name
            name_item = QTableWidgetItem(s.name)
            name_item.setData(Qt.ItemDataRole.UserRole, s)
            name_item.setFont(QFont("SansSerif", 9, QFont.Weight.Bold))
            name_item.setBackground(QColor(vg_color))
            self.table.setItem(row_pos, 0, name_item)
            
            # Voice group
            vg_val = s.voice_group.value if hasattr(s.voice_group, 'value') else str(s.voice_group)
            vg_item = QTableWidgetItem(vg_val)
            vg_item.setBackground(QColor(vg_color))
            self.table.setItem(row_pos, 1, vg_item)
            
            # Height
            height_text = f"{s.height} cm" if s.height > 0 else ""
            height_item = QTableWidgetItem(height_text)
            height_item.setBackground(QColor(vg_color))
            self.table.setItem(row_pos, 2, height_item)
            
            # Affinity
            affinity_name = ""
            if s.affinity:
                partner = next((p for p in self.singers if p.singer_id == s.affinity), None)
                if partner:
                    affinity_name = partner.name
            affinity_item = QTableWidgetItem(affinity_name)
            affinity_item.setBackground(QColor(vg_color))
            self.table.setItem(row_pos, 3, affinity_item)
        
        # Update count label
        pool_count = self.table.rowCount()
        self.pool_count_label.setText(f"{pool_count} Sänger")
    
    def update_placed_singers(self, placed_ids):
        self.placed_singer_ids = placed_ids
        self.update_singers(self.singers, placed_ids)
    
    def add_singer(self, s):
        self.singers.append(s)
        self.update_singers(self.singers, self.placed_singer_ids)
    
    def add_dialog(self, singer=None):
        d = AddSingerDialog(self, singer=singer)
        if d.exec() == QDialog.DialogCode.Accepted:
            s = d.get_singer()
            if s:
                if singer:
                    idx = next((i for i, x in enumerate(self.singers) if x.singer_id == singer.singer_id), -1)
                    if idx >= 0:
                        self.singers[idx] = s
                else:
                    self.singers.append(s)
                self.update_singers(self.singers, self.placed_singer_ids)
                if singer:
                    return s
                self.singer_added.emit(s)
                return s
        return None
    
    def on_double_click(self, item):
        if item:
            row = item.row()
            singer = item.data(Qt.ItemDataRole.UserRole)
            if singer:
                self.singer_selected.emit(singer)
    
    def remove_selected(self):
        row = self.table.currentRow()
        if row >= 0:
            singer = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if singer:
                idx = next((i for i, x in enumerate(self.singers) if x.singer_id == singer.singer_id), -1)
                if idx >= 0:
                    if singer.affinity:
                        partner = next((p for p in self.singers if p.singer_id == singer.affinity), None)
                        if partner:
                            partner.affinity = ""
                    self.singers.pop(idx)
            self.update_singers(self.singers, self.placed_singer_ids)
    
    def do_import(self):
        from PyQt6.QtWidgets import QFileDialog
        fp, _ = QFileDialog.getOpenFileName(self, "Import", "", "Text (*.txt *.csv);;Alle (*)")
        if not fp:
            return
        
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            QMessageBox.warning(self, "Fehler", str(e))
            return
        
        imported = errors = 0
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split(';') if ';' in line else line.split(',')
            if len(parts) < 2:
                continue
            
            name = parts[0].strip()
            vg_str = parts[1].strip()
            height = int(parts[2].strip()) if len(parts) > 2 and parts[2].strip().isdigit() else 0
            
            from dependencies import get_valid_voice_groups
            valid_vgs = get_valid_voice_groups()
            
            if not name or vg_str not in valid_vgs:
                errors += 1
                continue
            
            vg = next((v for v in VoiceGroup if hasattr(v, 'value') and v.value == vg_str), None)
            if vg:
                self.singers.append(Singer(name, vg, height))
                imported += 1
            else:
                errors += 1
        
        self.update_singers(self.singers)
        if hasattr(self.parent(), '_mark_modified'):
            self.parent()._mark_modified()
        
        QMessageBox.information(self, "Fertig", f"{imported} importiert, {errors} übersprungen.")


class DraggableTableWidget(QTableWidget):
    """Table widget with drag support for singers."""
    
    def startDrag(self, supportedActions):
        row = self.currentRow()
        if row >= 0:
            from PyQt6.QtCore import QMimeData
            from PyQt6.QtCore import Qt
            
            item = self.item(row, 0)
            singer = item.data(Qt.ItemDataRole.UserRole)
            if singer:
                drag = QDrag(self)
                mime = QMimeData()
                mime.setText(f"singer:{singer.singer_id}")
                drag.setMimeData(mime)
                drag.exec(Qt.DragAction.Copy)
        else:
            super().startDrag(supportedActions)
