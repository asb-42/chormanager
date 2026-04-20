# UI: Print Preview Dialog - shows exact preview of what will be printed/exported
try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QCheckBox, QComboBox, QWidget, QScrollArea, QFrame
    )
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont, QColor, QPainter, QPixmap
    from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
except ImportError:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QCheckBox, QComboBox, QWidget, QScrollArea, QFrame
    )
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont, QColor, QPainter, QPixmap
    from PyQt5.QtPrintSupport import QPrinter, QPrintDialog

from qt_compat import exec_qt


class PrintPreviewDialog(QDialog):
    """Preview dialog for printing/exporting choir formations."""
    
    def __init__(self, parent=None, grid=None, singers=None):
        super().__init__(parent)
        self.grid = grid
        self.singers = singers or []
        self.setWindowTitle("Druckvorschau")
        self.setMinimumSize(800, 600)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        title = QLabel("<b>Vorschau der Choraufstellung</b>")
        title.setStyleSheet("font-size: 12pt;")
        layout.addWidget(title)
        
        info_layout = QHBoxLayout()
        rows = self.grid.rows if self.grid else 0
        cols = self.grid.cols if self.grid else 0
        placed = len([s for s in self.grid.singers]) if self.grid and hasattr(self.grid, 'singers') else 0
        info_layout.addWidget(QLabel(f"Reihen: {rows}, Spalten: {cols}, Sänger: {placed}"))
        
        self.staggered_check = QCheckBox("Versetzt")
        self.staggered_check.setChecked(self.grid.staggered if self.grid else False)
        self.staggered_check.stateChanged.connect(self.update_preview)
        info_layout.addWidget(self.staggered_check)
        
        self.landscape_check = QCheckBox("Querformat")
        self.landscape_check.setChecked(True)
        self.landscape_check.stateChanged.connect(self.update_preview)
        info_layout.addWidget(self.landscape_check)
        
        layout.addLayout(info_layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        scroll.setWidget(self.preview_label)
        layout.addWidget(scroll)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        print_btn = QPushButton("Drucken...")
        print_btn.setDefault(True)
        print_btn.clicked.connect(self.do_print)
        button_layout.addWidget(print_btn)
        
        pdf_btn = QPushButton("Als PDF speichern...")
        pdf_btn.clicked.connect(self.do_pdf)
        button_layout.addWidget(pdf_btn)
        
        close_btn = QPushButton("Schließen")
        close_btn.clicked.connect(self.reject)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self.update_preview()
    
    def update_preview(self):
        if not self.grid:
            print("DEBUG: grid is None")
            return
        
        print(f"DEBUG: rows={self.grid.rows}, cols={self.grid.cols}, singers={len(self.grid.singers)}")
        
        rows = self.grid.rows
        cols = self.grid.cols
        staggered = self.staggered_check.isChecked()
        
        cell_width = 100
        cell_height = 70
        offset = 60 if staggered else 0
        margin_left = 80
        margin_top = 50
        
        total_width = margin_left * 2 + cols * cell_width + (offset if staggered else 0)
        total_height = margin_top + rows * cell_height + 50
        
        self.preview_label.setFixedSize(total_width, total_height)
        
        pixmap = QPixmap(total_width, total_height)
        pixmap.fill(QColor("white"))
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        for r in range(rows):
            for c in range(cols):
                x = margin_left + c * cell_width
                if staggered and r % 2 == 1:
                    x += offset
                y = margin_top + r * cell_height
                
                painter.setBrush(QColor("#f0f0f0"))
                painter.setPen(Qt.NoPen)
                painter.drawRect(x + 2, y + 2, cell_width - 4, cell_height - 4)
                
                singer = self.grid.get_singer_at(r, c)
                if singer:
                    vg = singer.voice_group.value if hasattr(singer.voice_group, 'value') else str(singer.voice_group)
                    color_map = {
                        'Sopran 1': '#ff9999', 'Sopran 2': '#ff6666',
                        'Alt 1': '#99ccff', 'Alt 2': '#6699ff',
                        'Tenor 1': '#99ff99', 'Tenor 2': '#66cc66',
                        'Bass 1': '#ffff99', 'Bass 2': '#ffff66'
                    }
                    vg_color = color_map.get(vg, '#cccccc')
                    painter.setBrush(QColor(vg_color))
                    painter.setPen(Qt.NoPen)
                    painter.drawRect(x + 2, y + 2, cell_width - 4, cell_height - 4)
                    
                    painter.setPen(QColor("black"))
                    font = QFont("Sans", 10, QFont.Weight.Bold)
                    painter.setFont(font)
                    painter.drawText(x + 5, y + 15, cell_width - 10, 30, Qt.AlignLeft | Qt.AlignTop, singer.name)
                    
                    font = QFont("Sans", 7)
                    painter.setFont(font)
                    painter.drawText(x + 5, y + 40, cell_width - 10, 20, Qt.AlignLeft | Qt.AlignTop, vg)
        
        painter.end()
        self.preview_label.setPixmap(pixmap)
    
    def do_print(self):
        from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
        printer = QPrinter(QPrinter.HighResolution)
        
        if self.landscape_check.isChecked():
            printer.setOrientation(QPrinter.Landscape)
        
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Drucken")
        
        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            self.print_to_printer(printer)
    
    def do_pdf(self):
        try:
            from PyQt6.QtWidgets import QFileDialog
        except ImportError:
            from PyQt5.QtWidgets import QFileDialog
        fp, _ = QFileDialog.getSaveFileName(self, "Als PDF speichern", "", "PDF (*.pdf)")
        if fp:
            if not fp.endswith('.pdf'):
                fp += '.pdf'
            if self.export_to_pdf(fp):
                try:
                    from PyQt6.QtWidgets import QMessageBox
                except ImportError:
                    from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(self, "OK", "PDF erstellt.")
            else:
                try:
                    from PyQt6.QtWidgets import QMessageBox
                except ImportError:
                    from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Fehler", "PDF konnte nicht erstellt werden.")
    
    def export_to_pdf(self, filepath):
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            
            rows = self.grid.rows
            cols = self.grid.cols
            staggered = self.staggered_check.isChecked()
            landscape_mode = self.landscape_check.isChecked()
            
            page_size = landscape(A4) if landscape_mode else A4
            
            doc = SimpleDocTemplate(filepath, pagesize=page_size,
                                  rightMargin=30, leftMargin=30,
                                  topMargin=30, bottomMargin=18)
            
            story = []
            styles = getSampleStyleSheet()
            
            story.append(Paragraph("Choraufstellung", styles['Title']))
            story.append(Spacer(1, 12))
            
            placed = len(self.grid.singers)
            info_text = f"Reihen: {rows}, Spalten: {cols}, Sänger: {placed}"
            if staggered:
                info_text += " (versetzt)"
            story.append(Paragraph(info_text, styles['Normal']))
            story.append(Spacer(1, 12))
            
            display_grid = [['' for _ in range(cols)] for _ in range(rows)]
            singer_grid = [[None for _ in range(cols)] for _ in range(rows)]
            
            for r in range(rows):
                for c in range(cols):
                    singer = self.grid.get_singer_at(r, c)
                    if singer:
                        display_grid[r][c] = singer.name
                        singer_grid[r][c] = singer
            
            col_width = page_size[0] / cols if cols > 0 else inch
            row_height = (page_size[1] - 200) / rows if rows > 0 else 0.6 * inch
            
            table = Table(display_grid, colWidths=[col_width] * cols, rowHeights=[row_height] * rows)
            
            table_style = TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
            ])
            
            color_map = {
                'Sopran': colors.lightpink,
                'Alt': colors.lightblue,
                'Tenor': colors.lightgreen,
                'Bass': colors.lightyellow
            }
            
            for r in range(rows):
                for c in range(cols):
                    cell = singer_grid[r][c]
                    if cell:
                        vg = cell.voice_group.value if hasattr(cell.voice_group, 'value') else str(cell.voice_group)
                        vg_name = vg.split()[0] if vg else 'Sopran'
                        bg_color = color_map.get(vg_name, colors.white)
                        table_style.add('BACKGROUND', (c, r), (c, r), bg_color)
            
            table.setStyle(table_style)
            story.append(table)
            
            doc.build(story)
            return True
        
        except Exception as e:
            print(f"PDF export error: {e}")
            return False
    
    def print_to_printer(self, printer):
        import subprocess
        import os
        
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            
            rows = self.grid.rows
            cols = self.grid.cols
            staggered = self.staggered_check.isChecked()
            landscape_mode = self.landscape_check.isChecked()
            
            page_size = landscape(A4) if landscape_mode else A4
            
            pdf_path = "/tmp/chor_print_output.pdf"
            
            doc = SimpleDocTemplate(pdf_path, pagesize=page_size,
                                rightMargin=30, leftMargin=30,
                                topMargin=30, bottomMargin=18)
            
            story = []
            styles = getSampleStyleSheet()
            
            story.append(Paragraph("Choraufstellung", styles['Title']))
            story.append(Spacer(1, 12))
            
            placed = len(self.grid.singers)
            info_text = f"Reihen: {rows}, Spalten: {cols}, Sänger: {placed}"
            if staggered:
                info_text += " (versetzt)"
            story.append(Paragraph(info_text, styles['Normal']))
            story.append(Spacer(1, 12))
            
            display_grid = [['' for _ in range(cols)] for _ in range(rows)]
            singer_grid = [[None for _ in range(cols)] for _ in range(rows)]
            
            for r in range(rows):
                for c in range(cols):
                    singer = self.grid.get_singer_at(r, c)
                    if singer:
                        display_grid[r][c] = singer.name
                        singer_grid[r][c] = singer
            
            col_width = page_size[0] / cols if cols > 0 else inch
            row_height = (page_size[1] - 200) / rows if rows > 0 else 0.6 * inch
            
            table = Table(display_grid, colWidths=[col_width] * cols, rowHeights=[row_height] * rows)
            
            table_style = TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
            ])
            
            color_map = {
                'Sopran': colors.lightpink,
                'Alt': colors.lightblue,
                'Tenor': colors.lightgreen,
                'Bass': colors.lightyellow
            }
            
            for r in range(rows):
                for c in range(cols):
                    cell = singer_grid[r][c]
                    if cell:
                        vg = cell.voice_group.value if hasattr(cell.voice_group, 'value') else str(cell.voice_group)
                        vg_name = vg.split()[0] if vg else 'Sopran'
                        bg_color = color_map.get(vg_name, colors.white)
                        table_style.add('BACKGROUND', (c, r), (c, r), bg_color)
            
            table.setStyle(table_style)
            story.append(table)
            
            doc.build(story)
            
            orientation = "landscape" if landscape_mode else "portrait"
            cmd = ["lp", "-d", printer.printerName(), "-o", f"orientation-requested={orientation}", pdf_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            
            return result.returncode == 0
        
        except Exception as e:
            print(f"Print error: {e}")
            return False