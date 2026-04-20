from typing import List
import os
import subprocess
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape, letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

try:
    from PyQt6.QtPrintSupport import QPrinter
except ImportError:
    try:
        from PyQt5.QtPrintSupport import QPrinter
    except ImportError:
        QPrinter = None


class PDFExporter:
    """Export choir formations to PDF format or directly to printer"""
    
    VOICE_COLORS = {
        'Sopran': colors.lightpink,
        'Alt': colors.lightblue,
        'Tenor': colors.lightgreen,
        'Bass': colors.lightyellow
    }
    
    def __init__(self, page_size=A4):
        self.page_size = page_size
        self.styles = getSampleStyleSheet()
    
    def export_formation(self, singers: List, rows: int, cols: int, 
                        filename: str, title: str = "Choraufstellung") -> bool:
        """Export formation to PDF file"""
        try:
            doc = SimpleDocTemplate(filename, pagesize=self.page_size,
                                  rightMargin=30, leftMargin=30,
                                  topMargin=30, bottomMargin=18)
            
            story = []
            
            story.append(Paragraph(title, self.styles['Title']))
            story.append(Spacer(1, 12))
            
            info_text = f"Reihen: {rows}, Spalten: {cols}, Sänger: {len(singers)}"
            story.append(Paragraph(info_text, self.styles['Normal']))
            story.append(Spacer(1, 12))
            
            display_grid, singer_grid = self._create_grid_data(singers, rows, cols)
            
            table = Table(display_grid, colWidths=[inch]*cols, rowHeights=[0.6*inch]*rows)
            
            table_style = TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
            ])
            
            for row_idx in range(rows):
                for col_idx in range(cols):
                    cell = singer_grid[row_idx][col_idx]
                    if cell and hasattr(cell, 'voice_group'):
                        vg = cell.voice_group.value if hasattr(cell.voice_group, 'value') else str(cell.voice_group)
                        vg_name = vg.split()[0] if vg else 'Sopran'
                        bg_color = self.VOICE_COLORS.get(vg_name, colors.white)
                        table_style.add('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), bg_color)
            
            table.setStyle(table_style)
            story.append(table)
            
            doc.build(story)
            return True
            
        except Exception as e:
            print(f"Error exporting PDF: {e}")
            return False
    
    def print_formation(self, singers: List, rows: int, cols: int, 
                        printer: QPrinter, title: str = "Choraufstellung") -> bool:
        """Print formation directly to printer with user-selected settings"""
        try:
            page_size = printer.pageSize()
            orientation = printer.orientation()
            
            rl_pagesize = A4
            if page_size == QPrinter.Letter:
                rl_pagesize = letter
            elif page_size == QPrinter.A5:
                from reportlab.lib.pagesizes import A5
                rl_pagesize = A5
            elif page_size == QPrinter.Legal:
                from reportlab.lib.pagesizes import legal
                rl_pagesize = legal
            
            if orientation == QPrinter.Landscape:
                rl_pagesize = landscape(rl_pagesize)
            
            pdf_path = "/tmp/chor_print_output.pdf"
            
            doc = SimpleDocTemplate(pdf_path, pagesize=rl_pagesize,
                                  rightMargin=30, leftMargin=30,
                                  topMargin=30, bottomMargin=18)
            
            story = []
            
            story.append(Paragraph(title, self.styles['Title']))
            story.append(Spacer(1, 12))
            
            info_text = f"Reihen: {rows}, Spalten: {cols}, Sänger: {len(singers)}"
            story.append(Paragraph(info_text, self.styles['Normal']))
            story.append(Spacer(1, 12))
            
            display_grid, singer_grid = self._create_grid_data(singers, rows, cols)
            
            col_width = rl_pagesize[0] / cols if cols > 0 else inch
            row_height = (rl_pagesize[1] - 200) / rows if rows > 0 else 0.6*inch
            
            table = Table(display_grid, colWidths=[col_width]*cols, rowHeights=[row_height]*rows)
            
            table_style = TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
            ])
            
            for row_idx in range(rows):
                for col_idx in range(cols):
                    cell = singer_grid[row_idx][col_idx]
                    if cell and hasattr(cell, 'voice_group'):
                        vg = cell.voice_group.value if hasattr(cell.voice_group, 'value') else str(cell.voice_group)
                        vg_name = vg.split()[0] if vg else 'Sopran'
                        bg_color = self.VOICE_COLORS.get(vg_name, colors.white)
                        table_style.add('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), bg_color)
            
            table.setStyle(table_style)
            story.append(table)
            
            doc.build(story)
            
            printer_name = printer.printerName()
            lp_orientation = "portrait" if orientation == QPrinter.Portrait else "landscape"
            
            cmd = ["lp", "-d", printer_name, "-o", f"orientation-requested={lp_orientation}", pdf_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"Error printing: {e}")
            return False
    
    def _create_grid_data(self, singers: List, rows: int, cols: int):
        display_grid = [['' for _ in range(cols)] for _ in range(rows)]
        singer_grid = [[None for _ in range(cols)] for _ in range(rows)]
        
        singer_index = 0
        for row in range(rows):
            for col in range(cols):
                if singer_index < len(singers):
                    singer = singers[singer_index]
                    display_grid[row][col] = singer.name
                    singer_grid[row][col] = singer
                    singer_index += 1
        
        return display_grid, singer_grid
