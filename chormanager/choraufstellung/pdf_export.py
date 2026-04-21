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
    
    def _calc_page_size(self, rows: int, cols: int):
        """Calculate appropriate page size and orientation based on grid dimensions."""
        from reportlab.lib.pagesizes import landscape
        page_width, page_height = A4
        
        if cols > 4 or rows > 5:
            page_width, page_height = landscape(A4)
        
        return (page_width, page_height)
    
    def _calc_cell_size(self, page_size, rows: int, cols: int):
        """Calculate cell dimensions based on page size and grid."""
        page_width, page_height = page_size
        margin = 60
        usable_width = page_width - margin
        usable_height = page_height - 200
        
        col_width = usable_width / cols if cols > 0 else inch
        row_height = usable_height / rows if rows > 0 else 0.6*inch
        
        return col_width, row_height

    def export_formation(self, singers: List, rows: int, cols: int, 
                        filename: str, title: str = "Choraufstellung",
                        staggered: bool = False) -> bool:
        """Export formation to PDF file"""
        try:
            page_size = self._calc_page_size(rows, cols)
            col_width, row_height = self._calc_cell_size(page_size, rows, cols)
            
            if page_size[0] > page_size[1]:
                from reportlab.lib.pagesizes import landscape
                page_size = landscape(page_size)
            
            doc = SimpleDocTemplate(filename, pagesize=page_size,
                                  rightMargin=30, leftMargin=30,
                                  topMargin=30, bottomMargin=18)
            
            story = []
            
            story.append(Paragraph(title, self.styles['Title']))
            story.append(Spacer(1, 12))
            
            info_text = f"Reihen: {rows}, Spalten: {cols}, Sänger: {len(singers)}"
            story.append(Paragraph(info_text, self.styles['Normal']))
            story.append(Spacer(1, 12))
            
            display_grid, singer_grid = self._create_grid_data(singers, rows, cols, staggered)
            
            if staggered and rows > 1:
                col_width = (page_size[0] - 60) / (cols * 2)
            
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
            return True
            
        except Exception as e:
            print(f"Error exporting PDF: {e}")
            return False
    
    def print_formation(self, singers: List, rows: int, cols: int, 
                        printer: QPrinter, title: str = "Choraufstellung") -> bool:
        """Print formation directly to printer with user-selected settings"""
        try:
            rl_pagesize = A4
            is_landscape = False
            
            if hasattr(printer, 'pageSize'):
                page_size = printer.pageSize()
                if hasattr(page_size, 'name'):
                    page_name = page_size.name()
                else:
                    page_name = str(page_size)
                
                if page_name == "Letter":
                    rl_pagesize = letter
                elif page_name == "A5":
                    from reportlab.lib.pagesizes import A5
                    rl_pagesize = A5
                elif page_name == "Legal":
                    from reportlab.lib.pagesizes import legal
                    rl_pagesize = legal
            
            if hasattr(printer, 'orientation'):
                orientation = printer.orientation()
                if hasattr(orientation, 'value'):
                    is_landscape = orientation.value == 1
                elif orientation == 1:
                    is_landscape = True
            elif hasattr(printer, 'setPageSize'):
                pass
            
            if is_landscape:
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
            
            display_grid, singer_grid = self._create_grid_data(singers, rows, cols, is_landscape)
            
            col_width = rl_pagesize[0] / cols if cols > 0 else inch
            row_height = (rl_pagesize[1] - 200) / rows if rows > 0 else 0.6*inch
            
            if is_landscape and rows > 1:
                col_width = (rl_pagesize[0] - 60) / (cols * 2)
            
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
            
            if locals().get('printer'):
                printer_name = printer.printerName() if hasattr(printer, 'printerName') else "lp"
            else:
                printer_name = "lp"
            lp_orientation = "portrait"
            
            if hasattr(printer, 'orientation'):
                orient = printer.orientation()
                is_portrait = True
                if hasattr(orient, 'value'):
                    is_portrait = orient.value == 0
                elif orient == 0:
                    is_portrait = True
                elif orient == 1:
                    is_portrait = False
                lp_orientation = "portrait" if is_portrait else "landscape"
            
            cmd = ["lp", "-d", printer_name, "-o", f"orientation-requested={lp_orientation}", pdf_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"Error printing: {e}")
            return False
    
    def _create_grid_data(self, singers: List, rows: int, cols: int, staggered: bool = False):
        display_grid = [['' for _ in range(cols)] for _ in range(rows)]
        singer_grid = [[None for _ in range(cols)] for _ in range(rows)]
        
        for singer in singers:
            if singer.row >= 0 and singer.col >= 0:
                if singer.row < rows and singer.col < cols:
                    display_grid[singer.row][singer.col] = singer.name
                    singer_grid[singer.row][singer.col] = singer
        
        return display_grid, singer_grid
